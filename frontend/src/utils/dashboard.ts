/**
 * The dashboard that holds a user's profile and settings.
 */
export function dashboardPathFor(userType?: string | null): string {
  return userType === 'hcp' ? '/hcpdashboard' : '/patientdashboard';
}

const ROLE_LABELS: Record<string, string> = {
  patient: 'Patient Advocate',
  caregiver: 'Caregiver',
  hcp: 'Healthcare Professional',
  org_member: 'Organization Member',
  admin: 'Administrator',
};

/**
 * The role shown on the dashboard header.
 */
export function roleLabelFor(userType?: string | null): string {
  return (userType && ROLE_LABELS[userType]) || 'Patient Advocate';
}
