import { apiClient } from '../lib/apiClient';
import { MODERATION } from '../lib/api';

export type ModerationAction =
  | 'approve_content'
  | 'hide_content'
  | 'delete_content'
  | 'warn_user'
  | 'suspend_user'
  | 'ban_user';

export type ReportPriority = 'normal' | 'high' | 'critical';

export interface AuthorHistory {
  warnings: number;
  suspensions: number;
  bans: number;
  content_removed: number;
  reports_received: number;
  reports_upheld: number;
  last_action_at?: string | null;
}

/** One report in the moderation queue, with the reported content and its author. */
export interface QueueItem {
  report_id: string;
  target_type: 'post' | 'comment' | 'user' | 'resource';
  target_id: string;
  reason: string;
  description?: string | null;
  source: 'user' | 'auto_filter';
  priority: ReportPriority;
  status: string;
  created_at?: string | null;
  resolved_at?: string | null;
  action_taken?: string | null;
  resolution_notes?: string | null;
  reporter_name?: string | null;
  moderator_name?: string | null;
  reported_content?: string | null;
  current_content?: string | null;
  post_id?: string | null;
  community_id?: string | null;
  post_title?: string | null;
  content_status?: string | null;
  moderation_score?: number | null;
  flagged_reason?: string | null;
  content_deleted?: boolean | null;
  open_reports_on_target: number;
  author_id?: string | null;
  author_name?: string | null;
  author_type?: string | null;
  author_status?: string | null;
  author_suspended_until?: string | null;
  author_history?: AuthorHistory | null;
}

export interface QueuePage {
  data: QueueItem[];
  meta: { total: number; page: number; limit: number; pages: number };
}

export interface QueueFilters {
  status?: 'open' | 'closed';
  priority?: ReportPriority;
  target_type?: 'post' | 'comment';
  page?: number;
  limit?: number;
}

export interface DecideRequest {
  action: ModerationAction;
  reason?: string;
  duration_hours?: number;
  remove_content?: boolean;
}

export const moderationService = {
  /** Reports to review, most urgent first (admins only). */
  getQueue: async (filters: QueueFilters = {}): Promise<QueuePage> => {
    const response = await apiClient.get(MODERATION.QUEUE, { params: filters });
    return response.data;
  },

  /** Act on a report. Every open report on the same content is closed with it. */
  decide: async (reportId: string, body: DecideRequest) => {
    const response = await apiClient.post(MODERATION.DECIDE(reportId), body);
    return response.data;
  },
};

export default moderationService;
