import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTheme } from '../../contexts/ThemeContext';

const CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined;
const SCRIPT_URL = 'https://accounts.google.com/gsi/client';

/** False when no Google Client ID is configured: the button is then hidden. */
export const isGoogleSignInEnabled = Boolean(CLIENT_ID);

// The parts of Google Identity Services used here
interface GoogleCredentialResponse {
  credential: string;
}
interface GoogleAccountsId {
  initialize(config: {
    client_id: string;
    callback: (response: GoogleCredentialResponse) => void;
    ux_mode?: 'popup' | 'redirect';
    cancel_on_tap_outside?: boolean;
  }): void;
  renderButton(parent: HTMLElement, options: Record<string, unknown>): void;
}
declare global {
  interface Window {
    google?: { accounts: { id: GoogleAccountsId } };
  }
}

let scriptPromise: Promise<void> | null = null;

function loadGoogleScript(): Promise<void> {
  if (window.google?.accounts?.id) return Promise.resolve();
  if (!scriptPromise) {
    scriptPromise = new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = SCRIPT_URL;
      script.async = true;
      script.onload = () => resolve();
      script.onerror = () => {
        scriptPromise = null;
        script.remove();
        reject(new Error('Could not load Google sign-in'));
      };
      document.head.appendChild(script);
    });
  }
  return scriptPromise;
}

// Google allows one callback per page: initialize once and pass the credential
// to whichever button is on screen.
let activeHandler: ((credential: string) => void) | null = null;
let initialized = false;

function initializeGoogle(google: NonNullable<Window['google']>) {
  if (initialized || !CLIENT_ID) return;
  google.accounts.id.initialize({
    client_id: CLIENT_ID,
    callback: (response) => activeHandler?.(response.credential),
    ux_mode: 'popup',
    cancel_on_tap_outside: true,
  });
  initialized = true;
}

interface GoogleSignInButtonProps {
  text?: 'signin_with' | 'signup_with' | 'continue_with';
  onCredential: (credential: string) => void;
  disabled?: boolean;
}

/**
 * The official "Sign in with Google" button. Google gives the browser an ID token,
 * which onCredential sends to the backend.
 */
export function GoogleSignInButton({ text = 'continue_with', onCredential, disabled = false }: GoogleSignInButtonProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLDivElement>(null);
  const handlerRef = useRef(onCredential);
  const { theme } = useTheme();
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    handlerRef.current = onCredential;
  }, [onCredential]);

  useEffect(() => {
    if (!CLIENT_ID) return;
    let cancelled = false;
    const handler = (credential: string) => handlerRef.current(credential);

    loadGoogleScript()
      .then(() => {
        const google = window.google;
        if (cancelled || !google || !buttonRef.current || !containerRef.current) return;
        initializeGoogle(google);
        activeHandler = handler;
        buttonRef.current.innerHTML = '';
        google.accounts.id.renderButton(buttonRef.current, {
          type: 'standard',
          theme: theme === 'dark' ? 'filled_black' : 'outline',
          size: 'large',
          text,
          shape: 'rectangular',
          logo_alignment: 'center',
          // Google accepts 200 to 400 pixels
          width: Math.max(200, Math.min(400, Math.round(containerRef.current.offsetWidth))),
        });
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });

    return () => {
      cancelled = true;
      if (activeHandler === handler) activeHandler = null;
    };
  }, [text, theme]);

  if (!CLIENT_ID) return null;

  if (failed) {
    return (
      <p className="text-sm text-center text-muted-foreground">
        Google sign-in could not load. Check your connection, or use your email and password.
      </p>
    );
  }

  return (
    <div ref={containerRef} className="w-full space-y-3">
      <div
        ref={buttonRef}
        className={`flex justify-center min-h-[44px] ${disabled ? 'pointer-events-none opacity-60' : ''}`}
        aria-busy={disabled}
      />
      <p className="text-xs text-center text-muted-foreground leading-snug">
        By continuing with Google, you agree to the{' '}
        <Link to="#" className="text-primary-color hover:underline">Terms of Service</Link> and{' '}
        <Link to="#" className="text-primary-color hover:underline">Privacy Policy</Link>, and consent to data processing.
      </p>
    </div>
  );
}
