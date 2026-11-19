/**
 * The dashboard that holds a user's profile and settings.
 */
export function dashboardPathFor(userType?: string | null): string {
  return userType === 'hcp' ? '/hcpdashboard' : '/patientdashboard';
}
