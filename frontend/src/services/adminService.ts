import { apiClient } from '../lib/apiClient';
import { DOCTORS, EVENTS, RESOURCES, SYSTEM } from '../lib/api';
import type { Event, Resource } from '../types/db';

export interface AdminOverview {
  health: {
    status: 'operational' | 'degraded';
    database: string;
    redis: string;
    uptime_seconds: number;
    live_connections: number;
    live_via_redis: boolean;
  };
  queues: {
    open_reports: number;
    critical_reports: number;
    pending_licences: number;
    pending_resources: number;
    pending_events: number;
  };
  users: {
    total: number;
    by_type: Record<string, number>;
    new_last_7_days: number;
    suspended: number;
  };
  activity: {
    posts_last_7_days: number;
    moderation_actions_last_7_days: number;
  };
}

export type AuditCategory = 'moderation' | 'verification' | 'resource' | 'event';

export interface AuditLogEntry {
  log_id: string;
  user_id?: string | null;
  actor_name?: string | null;
  action: string;
  target_type?: string | null;
  target_id?: string | null;
  metadata?: Record<string, unknown> | null;
  created_at: string;
}

export interface Page<T> {
  data: T[];
  meta: { total: number; page: number; limit: number; total_pages?: number; pages?: number };
}

export interface PendingLicence {
  verification_id: string;
  user_id: string;
  display_name?: string | null;
  email?: string | null;
  license_number: string;
  institution: string;
  country: string;
  specialization: string;
  issuing_region?: string | null;
  expiration_date?: string | null;
  status: string;
  created_at: string;
  has_document: boolean;
}

export type PendingResource = Resource & {
  submitter_name?: string | null;
  submitter_email?: string | null;
  submitter_type?: string | null;
};

export type PendingEvent = Event & {
  suggester_name?: string | null;
  suggester_email?: string | null;
  suggester_type?: string | null;
};

export type ApprovalDecision = { decision: 'approve' } | { decision: 'reject'; reason: string };

export const adminService = {
  getOverview: async (): Promise<AdminOverview> => {
    const response = await apiClient.get(SYSTEM.ADMIN_OVERVIEW);
    return response.data;
  },

  getAuditLogs: async (params: { category?: AuditCategory; page?: number; limit?: number }): Promise<Page<AuditLogEntry>> => {
    const response = await apiClient.get(SYSTEM.AUDIT_LOGS, { params });
    return response.data;
  },

  // Doctor licences
  getPendingLicences: async (): Promise<PendingLicence[]> => {
    const response = await apiClient.get(DOCTORS.PENDING);
    return response.data;
  },

  decideLicence: async (id: string, body: { status: 'approved' } | { status: 'rejected'; rejection_reason: string }) => {
    const response = await apiClient.patch(DOCTORS.REVIEW(id), body);
    return response.data;
  },

  /** The uploaded licence, for viewing in a new tab. */
  getLicenceDocument: async (id: string): Promise<Blob> => {
    const response = await apiClient.get(DOCTORS.DOCUMENT(id), { responseType: 'blob', timeout: 60000 });
    return response.data;
  },

  // Resources and events waiting for approval
  getPendingResources: async (page = 1): Promise<Page<PendingResource>> => {
    const response = await apiClient.get(RESOURCES.PENDING, { params: { page, limit: 50 } });
    return response.data;
  },

  decideResource: async (id: string, body: ApprovalDecision) => {
    const response = await apiClient.patch(RESOURCES.APPROVAL(id), body);
    return response.data;
  },

  getPendingEvents: async (page = 1): Promise<Page<PendingEvent>> => {
    const response = await apiClient.get(EVENTS.PENDING, { params: { page, limit: 50 } });
    return response.data;
  },

  decideEvent: async (id: string, body: ApprovalDecision) => {
    const response = await apiClient.patch(EVENTS.APPROVAL(id), body);
    return response.data;
  },
};

export default adminService;
