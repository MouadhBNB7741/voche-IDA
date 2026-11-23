import { Badge } from '../ui/badge';
import type { ReferralStatus } from '../../types/db';

const STATUS: Record<ReferralStatus, { label: string; className: string }> = {
    sent: { label: 'Sent', className: 'border-[hsl(var(--border))] text-muted-foreground' },
    viewed: { label: 'Viewed', className: 'border-[hsl(var(--primary)/0.3)] text-primary-color' },
    consent_pending: { label: 'Consent pending', className: 'border-amber-400/50 text-amber-600 dark:text-amber-400' },
    enrolled: { label: 'Enrolled', className: 'border-[hsl(var(--success)/0.4)] text-success-color' },
    declined: { label: 'Declined', className: 'border-red-400/40 text-red-500' },
    ineligible: { label: 'Not eligible', className: 'border-red-400/40 text-red-500' },
};

export function ReferralStatusBadge({ status }: { status: ReferralStatus }) {
    const { label, className } = STATUS[status];
    return <Badge variant="outline" className={className}>{label}</Badge>;
}

const STEPS = ['Referred', 'Accepted', 'Consent signed & enrolled'];
const REACHED: Partial<Record<ReferralStatus, number>> = { sent: 1, viewed: 1, consent_pending: 2, enrolled: 3 };

/** Enrolment milestones for a referral; nothing for declined or ineligible ones. */
export function ReferralProgress({ status, selfEnrolled }: { status: ReferralStatus; selfEnrolled?: boolean }) {
    const reached = REACHED[status];
    if (!reached) return null;
    const steps = selfEnrolled ? ['Started', 'Eligible', STEPS[2]] : STEPS;
    return (
        <ol className="flex items-center gap-2 text-xs mt-3" aria-label="Enrolment progress">
            {steps.map((label, i) => {
                const done = i < reached;
                return (
                    <li key={label} className="flex items-center gap-2" aria-current={i === reached ? 'step' : undefined}>
                        <span className={`h-2.5 w-2.5 rounded-full ${done ? 'bg-primary-color' : 'bg-[hsl(var(--border))]'}`} />
                        <span className={done ? 'font-semibold' : 'text-muted-foreground'}>{label}</span>
                        {i < steps.length - 1 && <span className={`h-px w-6 ${i + 1 < reached ? 'bg-primary-color' : 'bg-[hsl(var(--border))]'}`} />}
                    </li>
                );
            })}
        </ol>
    );
}
