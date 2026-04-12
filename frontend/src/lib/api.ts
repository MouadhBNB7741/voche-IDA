/**
 * Voche API Constants
 * Aligned with backend/app/api/v1/ routes and routers.
 */

export const API_BASE = '/api/v1';

export const AUTH = {
  LOGIN: `${API_BASE}/auth/login`,
  REGISTER: `${API_BASE}/auth/register`,
  ME: `${API_BASE}/auth/me`,
  FORGOT_PASSWORD: `${API_BASE}/auth/forgot-password`,
  RESET_PASSWORD: `${API_BASE}/auth/reset-password`,
  VERIFY_EMAIL: `${API_BASE}/auth/verify-email`,
};

export const USERS = {
  PROFILE: `${API_BASE}/users/profile`,
  ME_SAVED_TRIALS: `${API_BASE}/users/me/saved-trials`,
  NOTIFICATIONS: `${API_BASE}/notifications`,
};

export const CLINICAL = {
  TRIALS: `${API_BASE}/clinical/trials`,
  TRIAL_BY_ID: (id: string) => `${API_BASE}/clinical/trials/${id}`,
  SAVE_TRIAL: (id: string) => `${API_BASE}/clinical/trials/${id}/save`,
  INTEREST: (id: string) => `${API_BASE}/clinical/trials/${id}/interest`,
  ALERTS: `${API_BASE}/clinical/alerts/trials`,
  ALERT_BY_ID: (id: string) => `${API_BASE}/clinical/alerts/trials/${id}`,
};

export const COMMUNITY = {
  LIST: `${API_BASE}/community`,
  FEED: `${API_BASE}/community/feed`,
  GET: (id: string) => `${API_BASE}/community/${id}`,
  POSTS: (communityId: string) => `${API_BASE}/community/${communityId}/posts`,
  POST_DETAILS: (communityId: string, postId: string) => `${API_BASE}/community/${communityId}/posts/${postId}`,
  LIKE_POST: (communityId: string, postId: string) => `${API_BASE}/community/${communityId}/posts/${postId}/like`,
  REPLIES: (communityId: string, postId: string) => `${API_BASE}/community/${communityId}/posts/${postId}/replies`,
  LIKE_REPLY: (communityId: string, replyId: string) => `${API_BASE}/community/${communityId}/replies/${replyId}/like`,
  REPORT: (communityId: string) => `${API_BASE}/community/${communityId}/report`,
  ADMIN_REPORTS: `${API_BASE}/community/admin/reports`,
};

export const ORGANIZATIONS = {
  LIST: `${API_BASE}/organizations`,
  DETAILS: (id: string) => `${API_BASE}/organizations/${id}`,
  JOIN: (id: string) => `${API_BASE}/organizations/${id}/join`,
  REQUESTS: (id: string) => `${API_BASE}/organizations/${id}/requests`,
  DECIDE: (orgId: string, userId: string) => `${API_BASE}/organizations/${orgId}/members/${userId}/decide`,
  WORKING_GROUPS: `${API_BASE}/organizations/working-groups`,
  WG_DETAILS: (id: string) => `${API_BASE}/organizations/working-groups/${id}`,
  WG_JOIN: (id: string) => `${API_BASE}/organizations/working-groups/${id}/join`,
  WG_REQUESTS: (id: string) => `${API_BASE}/organizations/working-groups/${id}/requests`,
  WG_DECIDE: (groupId: string, userId: string) => `${API_BASE}/organizations/working-groups/${groupId}/members/${userId}/decide`,
};

export const EVENTS = {
  LIST: `${API_BASE}/events`,
  DETAILS: (id: string) => `${API_BASE}/events/${id}`,
  REGISTER: (id: string) => `${API_BASE}/events/${id}/register`,
};

export const RESOURCES = {
  LIST: `${API_BASE}/resources`,
  DETAILS: (id: string) => `${API_BASE}/resources/${id}`,
};

export const SYSTEM = {
  HEALTH: `${API_BASE}/system/health`,
  STATS: `${API_BASE}/system/stats`,
};
