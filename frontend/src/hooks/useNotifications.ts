import { useEffect, useRef, useSyncExternalStore } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import Cookies from 'universal-cookie';
import { toast } from 'sonner';
import { useAuthContext } from '../contexts/AuthContext';
import { notificationService, type NotificationPage } from '../services/notificationService';
import type { Notification } from '../types/db';

export const NOTIFICATIONS_KEY = ['notifications'];
const FEED_LIMIT = 20;
// Refresh used whenever the live connection is down or unavailable
const POLL_INTERVAL_MS = 10_000;
const PING_INTERVAL_MS = 25_000;
const MAX_RETRY_DELAY_MS = 30_000;
// Close codes sent by the server (see backend/app/api/v1/notifications.py)
const LOGIN_REFUSED = new Set([4401, 4403]);

const cookies = new Cookies();

// Whether the live connection is open, shared by every component that shows notifications
let liveConnected = false;
const listeners = new Set<() => void>();

function setLiveConnected(value: boolean) {
  if (liveConnected === value) return;
  liveConnected = value;
  listeners.forEach(listener => listener());
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => { listeners.delete(listener); };
}

export function useLiveConnected(): boolean {
  return useSyncExternalStore(subscribe, () => liveConnected);
}

/**
 * Where the live connection goes. VITE_NOTIFICATIONS_WS_URL can point it at another
 * server; otherwise it is the API server's /api/v1/notifications/ws.
 */
export function notificationsSocketUrl(): string {
  const explicit = import.meta.env.VITE_NOTIFICATIONS_WS_URL;
  if (explicit) return explicit;
  const api = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000')
    .replace(/\/+$/, '')
    .replace(/\/api\/v1$/, '');
  return `${api.replace(/^http/, 'ws')}/api/v1/notifications/ws`;
}

/**
 * The latest notifications and the unread count, for the bell and the Notifications page.
 * While the live connection is open, new ones arrive instantly; otherwise this refreshes every 10 seconds.
 */
export function useNotificationFeed() {
  const { isAuthenticated } = useAuthContext();
  const live = useLiveConnected();
  return useQuery<NotificationPage>({
    queryKey: NOTIFICATIONS_KEY,
    queryFn: () => notificationService.getNotifications({ limit: FEED_LIMIT }),
    enabled: isAuthenticated,
    refetchInterval: live ? false : POLL_INTERVAL_MS,
  });
}

/**
 * Keeps one live connection open for the logged-in user, reconnecting when it drops.
 * Mount it once, in the app layout.
 */
export function useLiveNotifications() {
  const { user } = useAuthContext();
  const userId = user?.id;
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const navigateRef = useRef(navigate);
  navigateRef.current = navigate;

  useEffect(() => {
    if (!userId || typeof WebSocket === 'undefined') return;

    let socket: WebSocket | null = null;
    let stopped = false;
    let retries = 0;
    let retryTimer: number | undefined;
    let pingTimer: number | undefined;

    const receive = (notification: Notification) => {
      queryClient.setQueryData<NotificationPage>(NOTIFICATIONS_KEY, page => {
        if (!page || page.data.some(n => n.notification_id === notification.notification_id)) return page;
        return {
          ...page,
          data: [notification, ...page.data].slice(0, FEED_LIMIT),
          unread_count: page.unread_count + (notification.read ? 0 : 1),
        };
      });
      queryClient.invalidateQueries({ queryKey: NOTIFICATIONS_KEY });

      // Pages that show what the notification is about
      if (notification.type === 'verification_update') queryClient.invalidateQueries({ queryKey: ['auth', 'me'] });
      if (notification.type === 'resource_update') queryClient.invalidateQueries({ queryKey: ['resources'] });
      if (notification.type === 'event_update') queryClient.invalidateQueries({ queryKey: ['events'] });
      if (notification.type === 'moderation_action') queryClient.invalidateQueries({ queryKey: ['community'] });
      // Admins: new submissions and urgent reports refresh the admin portal
      if (['resource_update', 'event_update', 'verification_update', 'moderation_action'].includes(notification.type)) {
        queryClient.invalidateQueries({ queryKey: ['admin'] });
      }

      const link = notification.link;
      toast(notification.title, {
        description: notification.message,
        duration: 6000,
        action: link ? { label: 'View', onClick: () => navigateRef.current(link) } : undefined,
      });
    };

    const scheduleReconnect = () => {
      if (stopped) return;
      const delay = Math.min(MAX_RETRY_DELAY_MS, 1000 * 2 ** retries) * (0.75 + Math.random() * 0.5);
      retries += 1;
      window.clearTimeout(retryTimer);
      retryTimer = window.setTimeout(connect, delay);
    };

    function connect() {
      if (stopped || socket) return;
      const token = cookies.get('voche_token');
      if (!token) {
        // Logged out in another tab, or the session ended: check again later
        retries = Math.max(retries, 5);
        scheduleReconnect();
        return;
      }

      const ws = new WebSocket(notificationsSocketUrl());
      socket = ws;
      // The token goes in the first message, not the URL, so it never lands in server logs
      ws.onopen = () => ws.send(JSON.stringify({ type: 'auth', token }));
      ws.onmessage = event => {
        let message: { type?: string; notification?: Notification };
        try {
          message = JSON.parse(event.data);
        } catch {
          return;
        }
        if (message.type === 'ready') {
          retries = 0;
          setLiveConnected(true);
          // Catch up on anything sent while the connection was down
          queryClient.invalidateQueries({ queryKey: NOTIFICATIONS_KEY });
          window.clearInterval(pingTimer);
          pingTimer = window.setInterval(() => {
            if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: 'ping' }));
          }, PING_INTERVAL_MS);
        } else if (message.type === 'notification' && message.notification) {
          receive(message.notification);
        }
      };
      ws.onclose = event => {
        window.clearInterval(pingTimer);
        if (socket === ws) socket = null;
        setLiveConnected(false);
        // Login refused or expired: retry slowly, the 10-second refresh runs meanwhile
        if (LOGIN_REFUSED.has(event.code)) retries = Math.max(retries, 5);
        scheduleReconnect();
      };
    }

    const reconnectNow = () => {
      if (stopped || socket) return;
      retries = 0;
      window.clearTimeout(retryTimer);
      connect();
    };

    window.addEventListener('online', reconnectNow);
    // Wait a tick, so a mount that is undone straight away (React strict mode) opens nothing
    retryTimer = window.setTimeout(connect, 0);

    return () => {
      stopped = true;
      window.clearTimeout(retryTimer);
      window.clearInterval(pingTimer);
      window.removeEventListener('online', reconnectNow);
      if (socket) {
        socket.onclose = null;
        socket.close(1000, 'Logged out');
        socket = null;
      }
      setLiveConnected(false);
    };
  }, [userId, queryClient]);
}
