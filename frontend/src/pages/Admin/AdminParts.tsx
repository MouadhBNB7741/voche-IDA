import { useEffect, useState, type ReactNode } from 'react';
import { ChevronLeft, ChevronRight, Loader2 } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Card } from '../../components/ui/card';
import { Checkbox } from '../../components/ui/checkbox';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../../components/ui/dialog';
import { Label } from '../../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Textarea } from '../../components/ui/textarea';
import { useDialogClasses, useToneClass, type Tone } from './adminUtils';

export function ToneBadge({ tone, children }: { tone: Tone; children: ReactNode }) {
  const toneClass = useToneClass();
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-semibold ${toneClass(tone)}`}>
      {children}
    </span>
  );
}

export function EmptyState({ icon, title, text }: { icon: ReactNode; title: string; text: string }) {
  return (
    <Card className="p-10 text-center border-dashed">
      <div className="mx-auto mb-3 w-12 h-12 rounded-full bg-primary-color/10 text-primary-color flex items-center justify-center">
        {icon}
      </div>
      <p className="font-semibold">{title}</p>
      <p className="text-sm text-muted-foreground mt-1">{text}</p>
    </Card>
  );
}

export function LoadingCards() {
  return (
    <div className="space-y-4" aria-busy="true">
      {[0, 1].map(i => <Card key={i} className="h-40 animate-pulse bg-muted/30" />)}
    </div>
  );
}

export function Pager({ page, pages, onChange }: { page: number; pages: number; onChange: (page: number) => void }) {
  if (pages <= 1) return null;
  return (
    <div className="flex items-center justify-end gap-2 pt-2">
      <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => onChange(page - 1)} aria-label="Previous page">
        <ChevronLeft size={16} />
      </Button>
      <span className="text-sm text-muted-foreground">Page {page} of {pages}</span>
      <Button variant="outline" size="sm" disabled={page >= pages} onClick={() => onChange(page + 1)} aria-label="Next page">
        <ChevronRight size={16} />
      </Button>
    </div>
  );
}

export interface DecisionValues {
  reason: string;
  durationHours?: number;
  removeContent: boolean;
}

export interface DecisionConfig {
  title: string;
  description: string;
  confirmLabel: string;
  destructive?: boolean;
  /** 'required' needs a reason; 'optional' shows the box; 'none' hides it. */
  reason: 'required' | 'optional' | 'none';
  reasonHint?: string;
  askDuration?: boolean;
  offerRemoveContent?: boolean;
}

const DURATIONS = [
  { hours: 24, label: '24 hours' },
  { hours: 72, label: '3 days' },
  { hours: 168, label: '7 days' },
  { hours: 720, label: '30 days' },
];

/** Confirmation for an admin decision, with the reason sent to the member when one is needed. */
export function DecisionDialog({
  config,
  pending,
  onCancel,
  onConfirm,
}: {
  config: DecisionConfig | null;
  pending: boolean;
  onCancel: () => void;
  onConfirm: (values: DecisionValues) => void;
}) {
  const classes = useDialogClasses();
  const [reason, setReason] = useState('');
  const [duration, setDuration] = useState('72');
  const [removeContent, setRemoveContent] = useState(false);

  useEffect(() => {
    if (config) {
      setReason('');
      setDuration('72');
      setRemoveContent(false);
    }
  }, [config]);

  const reasonMissing = config?.reason === 'required' && reason.trim().length < 3;

  return (
    <Dialog open={!!config} onOpenChange={(open) => { if (!open && !pending) onCancel(); }}>
      <DialogContent className={`sm:max-w-[480px] border shadow-xl ${classes.content}`}>
        {config && (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (reasonMissing || pending) return;
              onConfirm({
                reason: reason.trim(),
                durationHours: config.askDuration ? Number(duration) : undefined,
                removeContent,
              });
            }}
            className="space-y-4"
          >
            <DialogHeader>
              <DialogTitle>{config.title}</DialogTitle>
              <DialogDescription className={classes.muted}>{config.description}</DialogDescription>
            </DialogHeader>

            {config.askDuration && (
              <div className="space-y-2">
                <Label htmlFor="decision-duration">Suspend for</Label>
                <Select value={duration} onValueChange={setDuration}>
                  <SelectTrigger id="decision-duration" className="w-full"><SelectValue /></SelectTrigger>
                  <SelectContent className={classes.menu}>
                    {DURATIONS.map(d => (
                      <SelectItem key={d.hours} value={String(d.hours)} className={`cursor-pointer ${classes.option}`}>
                        {d.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            {config.reason !== 'none' && (
              <div className="space-y-2">
                <Label htmlFor="decision-reason">
                  Reason {config.reason === 'optional' && <span className={classes.muted}>(optional)</span>}
                </Label>
                <Textarea
                  id="decision-reason"
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  maxLength={1000}
                  rows={3}
                  placeholder={config.reasonHint ?? 'Shown to the member'}
                  className="resize-none"
                  autoFocus
                />
              </div>
            )}

            {config.offerRemoveContent && (
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <Checkbox checked={removeContent} onCheckedChange={(v) => setRemoveContent(v === true)} />
                Also remove the reported content
              </label>
            )}

            <DialogFooter className="gap-2">
              <Button type="button" variant="ghost" onClick={onCancel} disabled={pending}>Cancel</Button>
              <Button
                type="submit"
                variant={config.destructive ? 'destructive' : 'default'}
                disabled={reasonMissing || pending}
                className="gap-2"
              >
                {pending && <Loader2 size={16} className="animate-spin" />}
                {config.confirmLabel}
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
