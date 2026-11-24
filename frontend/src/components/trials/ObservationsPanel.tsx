import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ClipboardPlus, Flag, Loader2, NotebookPen } from 'lucide-react';
import { toast } from 'sonner';
import { Card } from '../ui/card';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { trialService } from '../../services/trialService';
import { useTrials } from '../../hooks/useTrials';
import { useErrorHandler } from '../../hooks/useErrorHandler';
import { formatMessageDate } from '../../utils/date';
import type { SeverityLevel } from '../../types/db';

const SEVERITY_STYLES: Record<SeverityLevel, string> = {
  low: 'bg-gray-100 text-gray-700',
  medium: 'bg-amber-100 text-amber-700',
  high: 'bg-orange-100 text-orange-700',
  critical: 'bg-red-100 text-red-700',
};

export function ObservationsPanel() {
  const queryClient = useQueryClient();
  const { handleError } = useErrorHandler();
  const [trialId, setTrialId] = useState('');
  const [severity, setSeverity] = useState<SeverityLevel>('low');
  const [summary, setSummary] = useState('');

  // shortcut: first 100 trials only; switch to a search box when trial counts grow
  const { data: trials = [] } = useTrials({ limit: 100 });
  const { data: observations = [], isLoading } = useQuery({
    queryKey: ['observations', 'recent'],
    queryFn: trialService.getRecentObservations,
  });

  const create = useMutation({
    mutationFn: () => trialService.createObservation(trialId, summary.trim(), severity),
    onSuccess: () => {
      toast.success('Observation Logged');
      setSummary('');
      setSeverity('low');
      queryClient.invalidateQueries({ queryKey: ['observations'] });
    },
    onError: (err) => handleError(err, 'Could not log the observation.'),
  });

  const valid = !!trialId && summary.trim().length >= 10;

  return (
    <div className="space-y-4">
      <Card className="p-5">
        <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); if (valid) create.mutate(); }}>
          <h3 className="font-bold flex items-center gap-2"><ClipboardPlus size={18} className="text-primary-color" /> Log an observation</h3>
          <div className="grid sm:grid-cols-[1fr_180px] gap-4">
            <div className="space-y-2">
              <Label htmlFor="obs-trial">Trial</Label>
              <Select value={trialId} onValueChange={setTrialId}>
                <SelectTrigger id="obs-trial" className="h-11"><SelectValue placeholder="Choose a trial" /></SelectTrigger>
                <SelectContent>
                  {trials.map((t) => <SelectItem key={t.trial_id} value={t.trial_id}>{t.title}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="obs-severity">Severity</Label>
              <Select value={severity} onValueChange={(v) => setSeverity(v as SeverityLevel)}>
                <SelectTrigger id="obs-severity" className="h-11"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {(Object.keys(SEVERITY_STYLES) as SeverityLevel[]).map((s) => (
                    <SelectItem key={s} value={s} className="capitalize">{s}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="obs-summary">Observation</Label>
            <Textarea id="obs-summary" value={summary} onChange={(e) => setSummary(e.target.value)}
              placeholder="What did you observe? At least 10 characters."
              className="border border-[hsl(var(--border))] resize-none min-h-[90px]" />
            {severity === 'critical' && <p className="text-xs text-destructive">Critical observations are flagged for review.</p>}
          </div>
          <div className="flex justify-end">
            <Button type="submit" className="gap-2 cursor-pointer" disabled={!valid || create.isPending}>
              {create.isPending && <Loader2 size={16} className="animate-spin" />} Log Observation
            </Button>
          </div>
        </form>
      </Card>

      {isLoading ? (
        <div className="py-10 flex justify-center"><Loader2 className="h-8 w-8 animate-spin text-primary-color" /></div>
      ) : observations.length === 0 ? (
        <Card className="p-12 text-center border-dashed bg-muted/20">
          <NotebookPen className="mx-auto mb-4 text-muted-foreground/30" size={40} />
          <p className="text-muted-foreground">No observations yet on your trials.</p>
        </Card>
      ) : (
        <div className="grid gap-3">
          {observations.map((o) => (
            <Card key={o.observation_id} className="p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="font-semibold text-sm">{o.trial_title}</p>
                  <p className="text-sm mt-1 break-words">{o.summary}</p>
                  <p className="text-xs text-muted-foreground mt-2">{o.doctor_name ?? 'Unknown doctor'} · {formatMessageDate(o.created_at)}</p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  {o.flagged && <Flag size={14} className="text-destructive" aria-label="Flagged" />}
                  <Badge className={`${SEVERITY_STYLES[o.severity_level]} border-0 capitalize`}>{o.severity_level}</Badge>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
