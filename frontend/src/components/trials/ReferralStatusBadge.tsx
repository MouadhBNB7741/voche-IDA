import { Badge } from '../ui/badge';
import type { ReferralStatus } from '../../types/db';

const STATUS: Record<ReferralStatus, { label: string; className: string }> = {
    sent: { label: 'Sent', className: 'border-border text-muted-foreground' },
    viewed: { label: 'Viewed', className: 'border-primary/30 text-primary-color' },
    consent_pending: { label: 'Consent pending', className: 'border-amber-400/50 text-amber-600 dark:text-amber-400' },
    enrolled: { label: 'Enrolled', className: 'border-success-color/40 text-success-color' },
    declined: { label: 'Declined', className: 'border-red-400/40 text-red-500' },
    ineligible: { label: 'Not eligible', className: 'border-red-400/40 text-red-500' },
};

export function ReferralStatusBadge({ status }: { status: ReferralStatus }) {
    const { label, className } = STATUS[status];
    return <Badge variant="outline" className={className}>{label}</Badge>;
}
