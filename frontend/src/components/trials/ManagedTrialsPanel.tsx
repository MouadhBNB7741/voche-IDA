import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { FlaskConical, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { Card } from '../ui/card';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { trialService } from '../../services/trialService';
import { useErrorHandler } from '../../hooks/useErrorHandler';
import type { ManagedTrial, TrialStatus } from '../../types/db';

const FINAL: TrialStatus[] = ['Completed', 'Terminated'];

function TrialRow({ trial }: { trial: ManagedTrial }) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { handleError } = useErrorHandler();
  const [next, setNext] = useState<TrialStatus | ''>('');

  const change = useMutation({
    mutationFn: (status: TrialStatus) => trialService.changeTrialStatus(trial.trial_id, status),
    onSuccess: (_, status) => {
      toast.success('Trial Status Updated', { description: `${trial.title} is now ${status}.` });
      setNext('');
      queryClient.invalidateQueries({ queryKey: ['trials'] });
    },
    onError: (err) => handleError(err, 'Could not change the trial status.'),
  });

  return (
    <Card className="p-5 hover:shadow-md transition-all">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div className="min-w-0 space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <h4 className="font-bold hover:text-primary-color transition-colors cursor-pointer" onClick={() => navigate(`/trials/${trial.trial_id}`)}>
              {trial.title}
            </h4>
            <Badge variant="secondary" className="text-white">{trial.status}</Badge>
          </div>
          <p className="text-xs text-muted-foreground">
            {[trial.phase, trial.disease_area].filter(Boolean).join(' · ')}
            {trial.max_enrollment ? ` · ${trial.enrollment ?? 0}/${trial.max_enrollment} enrolled on site` : ''}
            {` · ${trial.referrals} referrals, ${trial.enrolled} enrolled through Voche`}
          </p>
        </div>
        {trial.next_statuses.length > 0 ? (
          <div className="flex items-center gap-2 shrink-0">
            <Select value={next} onValueChange={(v) => setNext(v as TrialStatus)}>
              <SelectTrigger className="h-9 w-48" aria-label={`New status for ${trial.title}`}><SelectValue placeholder="Change status" /></SelectTrigger>
              <SelectContent>
                {trial.next_statuses.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}
              </SelectContent>
            </Select>
            <Button size="sm" className="cursor-pointer" disabled={!next || change.isPending} onClick={() => next && change.mutate(next)}>
              {change.isPending ? <Loader2 size={14} className="animate-spin" /> : 'Update'}
            </Button>
          </div>
        ) : (
          <span className="text-xs text-muted-foreground shrink-0">Final status</span>
        )}
      </div>
      {next && FINAL.includes(next) && (
        <p className="text-xs text-destructive mt-3">{next} is final: the trial cannot be reopened afterwards.</p>
      )}
    </Card>
  );
}

export function ManagedTrialsPanel() {
  const { data: trials = [], isLoading, isError } = useQuery({
    queryKey: ['trials', 'managed'],
    queryFn: trialService.getManagedTrials,
  });

  if (isLoading) return <div className="py-16 flex justify-center"><Loader2 className="h-8 w-8 animate-spin text-primary-color" /></div>;
  if (isError) return <p className="text-sm text-destructive">Could not load your trials.</p>;
  if (trials.length === 0) {
    return (
      <Card className="p-16 text-center border-dashed bg-muted/20">
        <FlaskConical className="mx-auto mb-4 text-muted-foreground/30" size={48} />
        <h4 className="font-bold text-lg mb-2">No Trials Assigned</h4>
        <p className="text-muted-foreground max-w-sm mx-auto">An administrator assigns the trials you manage. They will appear here.</p>
      </Card>
    );
  }
  return <div className="grid gap-4">{trials.map((t) => <TrialRow key={t.trial_id} trial={t} />)}</div>;
}
