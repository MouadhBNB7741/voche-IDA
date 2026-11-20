import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { AlertTriangle, BadgeCheck, CheckCircle2, FileText, Mail, XCircle } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Card } from '../../components/ui/card';
import { useErrorHandler } from '../../hooks/useErrorHandler';
import { adminService, type PendingLicence } from '../../services/adminService';
import { DecisionDialog, EmptyState, LoadingCards, ToneBadge, type DecisionConfig } from './AdminParts';
import { formatDate, openProtectedFile, timeAgo } from './adminUtils';

type Decision = 'approve' | 'reject';

const DECISIONS: Record<Decision, DecisionConfig> = {
  approve: {
    title: 'Approve this licence?',
    description: 'The doctor gets the Verified HCP badge and can share resources. They are told by notification and email.',
    confirmLabel: 'Approve licence',
    reason: 'none',
  },
  reject: {
    title: 'Reject this licence?',
    description: 'The doctor is told why by notification and email, and can send a new document.',
    confirmLabel: 'Reject licence',
    destructive: true,
    reason: 'required',
    reasonHint: 'For example: the document is blurry, or the licence number does not match',
  },
};

export default function LicenceQueue() {
  const queryClient = useQueryClient();
  const { handleError } = useErrorHandler();
  const [pending, setPending] = useState<{ licence: PendingLicence; decision: Decision } | null>(null);

  const licences = useQuery({
    queryKey: ['admin', 'licences'],
    queryFn: adminService.getPendingLicences,
  });

  const decide = useMutation({
    mutationFn: ({ licence, decision, reason }: { licence: PendingLicence; decision: Decision; reason: string }) =>
      adminService.decideLicence(
        licence.verification_id,
        decision === 'approve' ? { status: 'approved' } : { status: 'rejected', rejection_reason: reason },
      ),
    onSuccess: (_, { decision }) => {
      toast.success(decision === 'approve' ? 'Licence approved. The doctor has been notified.' : 'Licence rejected. The doctor has been notified.');
      setPending(null);
      queryClient.invalidateQueries({ queryKey: ['admin'] });
    },
    onError: (err) => handleError(err, 'Could not save the decision.'),
  });

  const viewDocument = async (licence: PendingLicence) => {
    try {
      await openProtectedFile(
        () => adminService.getLicenceDocument(licence.verification_id),
        `licence-${licence.license_number}`,
      );
    } catch (err) {
      handleError(err, 'Could not open the document.');
    }
  };

  if (licences.isLoading) return <LoadingCards />;
  if (licences.isError) {
    return <EmptyState icon={<AlertTriangle size={22} />} title="Could not load the licences" text="Check your connection and try again." />;
  }
  const items = licences.data ?? [];
  if (items.length === 0) {
    return <EmptyState icon={<BadgeCheck size={22} />} title="No licences waiting" text="Licences that doctors send for verification will appear here." />;
  }

  return (
    <div className="space-y-4">
      {items.map(licence => {
        const expired = !!licence.expiration_date && new Date(licence.expiration_date) < new Date();
        return (
          <Card key={licence.verification_id} className="p-5 space-y-4">
            <div className="flex flex-wrap items-start gap-3">
              <div className="space-y-1">
                <p className="font-semibold text-lg">{licence.display_name || 'Unnamed doctor'}</p>
                {licence.email && (
                  <p className="text-sm text-muted-foreground flex items-center gap-1.5"><Mail size={14} /> {licence.email}</p>
                )}
              </div>
              <span className="text-xs text-muted-foreground ml-auto" title={formatDate(licence.created_at)}>
                Sent {timeAgo(licence.created_at)}
              </span>
            </div>

            <dl className="grid sm:grid-cols-2 gap-x-6 gap-y-2 text-sm">
              <Detail label="Licence number" value={licence.license_number} />
              <Detail label="Specialization" value={licence.specialization} />
              <Detail label="Institution" value={licence.institution} />
              <Detail label="Country" value={[licence.country, licence.issuing_region].filter(Boolean).join(', ')} />
              {licence.expiration_date && (
                <div>
                  <dt className="text-muted-foreground">Expires</dt>
                  <dd className="font-medium flex items-center gap-2">
                    {formatDate(licence.expiration_date, false)}
                    {expired && <ToneBadge tone="red">Expired</ToneBadge>}
                  </dd>
                </div>
              )}
            </dl>

            <div className="flex flex-wrap gap-2">
              {licence.has_document ? (
                <Button size="sm" variant="outline" className="gap-1.5" onClick={() => viewDocument(licence)}>
                  <FileText size={14} /> View document
                </Button>
              ) : (
                <ToneBadge tone="amber">No document uploaded</ToneBadge>
              )}
              <Button size="sm" className="gap-1.5 ml-auto" onClick={() => setPending({ licence, decision: 'approve' })}>
                <CheckCircle2 size={14} /> Approve
              </Button>
              <Button size="sm" variant="outline" className="gap-1.5 text-destructive" onClick={() => setPending({ licence, decision: 'reject' })}>
                <XCircle size={14} /> Reject
              </Button>
            </div>
          </Card>
        );
      })}

      <DecisionDialog
        config={pending ? DECISIONS[pending.decision] : null}
        pending={decide.isPending}
        onCancel={() => setPending(null)}
        onConfirm={({ reason }) => pending && decide.mutate({ ...pending, reason })}
      />
    </div>
  );
}

function Detail({ label, value }: { label: string; value?: string | null }) {
  return (
    <div>
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="font-medium break-words">{value || 'Not given'}</dd>
    </div>
  );
}
