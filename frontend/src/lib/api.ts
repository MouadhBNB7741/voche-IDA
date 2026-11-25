/**
 * Voche API Constants
 * Aligned with backend/app/api/v1/ routes and routers.
 */

export const API_BASE = '/api/v1';

export const AUTH = {
  LOGIN: `${API_BASE}/auth/login`,
  GOOGLE: `${API_BASE}/auth/google`,
  LOGOUT: `${API_BASE}/auth/logout`,
  REGISTER: `${API_BASE}/auth/register`,
  ME: `${API_BASE}/auth/me`,
  FORGOT_PASSWORD: `${API_BASE}/auth/request-reset`,        
  RESET_PASSWORD: `${API_BASE}/auth/reset-password`,
  VERIFY_EMAIL: `${API_BASE}/auth/verify-email`,
};

export const USERS = {
  ME: `${API_BASE}/users/me`,
  ME_AVATAR: `${API_BASE}/users/me/avatar`,
  PROFILE: `${API_BASE}/users/profile`,
  ME_SAVED_TRIALS: `${API_BASE}/users/me/saved-trials`,
  NOTIFICATIONS: `${API_BASE}/notifications`,
  NOTIFICATION_PREFERENCES: `${API_BASE}/users/me/preferences/notifications`,
  ME_CANCEL_DELETION: `${API_BASE}/users/me/cancel-deletion`,
  ONBOARDING_COMPLETE: `${API_BASE}/users/onboarding/complete`,
};

export const DOCTORS = {
  VERIFICATION: `${API_BASE}/doctors/verification`,
  VERIFICATION_UPLOAD: `${API_BASE}/doctors/verification/upload`,
  DOCUMENT: (id: string) => `${API_BASE}/doctors/verification/${id}/document`,
  // Admin review of licences
  PENDING: `${API_BASE}/doctors/verifications/pending`,
  REVIEW: (id: string) => `${API_BASE}/doctors/verifications/${id}`,
};

export const MODERATION = {
  QUEUE: `${API_BASE}/moderation/queue`,
  DECIDE: (reportId: string) => `${API_BASE}/moderation/reports/${reportId}/decide`,
};

export const CLINICAL = {
  TRIALS: `${API_BASE}/trials`,
  TRIAL_BY_ID: (id: string) => `${API_BASE}/trials/${id}`,
  SAVE_TRIAL: (id: string) => `${API_BASE}/trials/${id}/save`,
  INTEREST: (id: string) => `${API_BASE}/trials/${id}/interest`,
  SCREEN: (id: string) => `${API_BASE}/trials/${id}/screen`,
  REFER: (id: string) => `${API_BASE}/trials/${id}/refer`,
  REFERRALS_SENT: `${API_BASE}/referrals/sent`,
  REFERRALS_RECEIVED: `${API_BASE}/referrals/received`,
  REFERRAL_RESPOND: (id: string) => `${API_BASE}/referrals/${id}/respond`,
  REFERRAL_CONSENT: (id: string) => `${API_BASE}/referrals/${id}/consent`,
  ENROLL: (id: string) => `${API_BASE}/trials/${id}/enroll`,
  MANAGED_TRIALS: `${API_BASE}/trials/managed`,
  TRIAL_STATUS: (id: string) => `${API_BASE}/trials/${id}/status`,
  OBSERVATIONS: `${API_BASE}/clinical-observations/`,
  RECENT_OBSERVATIONS: `${API_BASE}/clinical-observations/recent`,
  ALERTS: `${API_BASE}/alerts/trials`,
  ALERT_BY_ID: (id: string) => `${API_BASE}/alerts/trials/${id}`,
};

export const AI = {
  CONVERSATIONS: `${API_BASE}/ai/conversations`,
  CONVERSATION: (id: string) => `${API_BASE}/ai/conversations/${id}`,
  MESSAGES: (id: string) => `${API_BASE}/ai/conversations/${id}/messages`,
  FEEDBACK: (messageId: string) => `${API_BASE}/ai/messages/${messageId}/feedback`,
};

export const SURVEYS = {
  LIST: `${API_BASE}/surveys/`,
  BY_ID: (id: string) => `${API_BASE}/surveys/${id}`,
  SUBMIT: (id: string) => `${API_BASE}/surveys/${id}/responses`,
  COMPLETED: `${API_BASE}/surveys/completed`,
  COMPLETED_BY_ID: (id: string) => `${API_BASE}/surveys/completed/${id}`,
  ASSIGNED: `${API_BASE}/surveys/assigned`,
  MANAGE: `${API_BASE}/surveys/manage`,
  CREATE: `${API_BASE}/surveys/`,
  STATUS: (id: string) => `${API_BASE}/surveys/${id}/status`,
  DRAFT: (id: string) => `${API_BASE}/surveys/${id}/draft`,
  ASSIGN: (id: string) => `${API_BASE}/surveys/${id}/assign`,
  ANALYTICS: (id: string) => `${API_BASE}/surveys/${id}/analytics`,
};

export const COMMUNITY = {
  LIST: `${API_BASE}/community/`,
  FEED: `${API_BASE}/community/feed`,
  GET: (id: string) => `${API_BASE}/community/${id}`,
  POSTS: (communityId: string) => `${API_BASE}/community/${communityId}/posts`,
  POST_DETAILS: (communityId: string, postId: string) => `${API_BASE}/community/${communityId}/posts/${postId}`,
  LIKE_POST: (communityId: string, postId: string) => `${API_BASE}/community/${communityId}/posts/${postId}/like`,
  UNLIKE_POST: (communityId: string, postId: string) => `${API_BASE}/community/${communityId}/posts/${postId}/unlike`,
  REPLIES: (communityId: string, postId: string) => `${API_BASE}/community/${communityId}/posts/${postId}/replies`,
  LIKE_REPLY: (communityId: string, replyId: string) => `${API_BASE}/community/${communityId}/replies/${replyId}/like`,
  UNLIKE_REPLY: (communityId: string, replyId: string) => `${API_BASE}/community/${communityId}/replies/${replyId}/unlike`,
  DELETE_POST: (communityId: string, postId: string) => `${API_BASE}/community/${communityId}/posts/${postId}`,
  DELETE_REPLY: (communityId: string, replyId: string) => `${API_BASE}/community/${communityId}/replies/${replyId}`,
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
  LIST: `${API_BASE}/events/`,
  DETAILS: (id: string) => `${API_BASE}/events/${id}`,
  REGISTER: (id: string) => `${API_BASE}/events/${id}/register`,
  MY_EVENTS: `${API_BASE}/users/me/events`,
  // Suggestions (POST to LIST) and their approval
  MY_SUGGESTIONS: `${API_BASE}/events/my-suggestions`,
  PENDING: `${API_BASE}/events/pending`,
  APPROVAL: (id: string) => `${API_BASE}/events/${id}/approval`,
};

export const RESOURCES = {
  LIST: `${API_BASE}/resources/`,
  DETAILS: (id: string) => `${API_BASE}/resources/${id}`,
  RATE: (id: string) => `${API_BASE}/resources/${id}/rating`,
  PROGRESS: (id: string) => `${API_BASE}/resources/${id}/progress`,
  DOWNLOAD: (id: string) => `${API_BASE}/resources/${id}/download`,
  FILE: (id: string) => `${API_BASE}/resources/${id}/file`,
  // Submissions and their approval
  CAN_SUBMIT: `${API_BASE}/resources/can-submit`,
  SUBMIT: `${API_BASE}/resources/submit`,
  MINE: `${API_BASE}/resources/mine`,
  PENDING: `${API_BASE}/resources/pending`,
  APPROVAL: (id: string) => `${API_BASE}/resources/${id}/approval`,
};

export const SYSTEM = {
  HEALTH: `${API_BASE}/system/health`,
  STATS: `${API_BASE}/system/stats`,
  FEEDBACK: `${API_BASE}/system/feedback`,
  FEEDBACK_LOCK: `${API_BASE}/system/feedback/lock`,
  ADMIN_OVERVIEW: `${API_BASE}/system/admin/overview`,
  AUDIT_LOGS: `${API_BASE}/system/audit-logs`,
};
