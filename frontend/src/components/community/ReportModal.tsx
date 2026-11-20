import { useEffect, useState } from 'react';
import { LifeBuoy } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select';
import { Button } from '../ui/button';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { useTheme } from '../../contexts/ThemeContext';
import { useReportContent } from '../../hooks/useCommunity';
import type { ReportReason } from '../../types/db';

const REPORT_REASONS: { value: ReportReason; label: string }[] = [
  { value: 'misinformation', label: 'Medical misinformation' },
  { value: 'harassment', label: 'Harassment or abuse' },
  { value: 'self_harm', label: 'Self-harm or suicide' },
  { value: 'spam', label: 'Spam or advertising' },
  { value: 'inappropriate_content', label: 'Inappropriate content' },
  { value: 'medical_advice', label: 'Unsafe medical advice' },
  { value: 'other', label: 'Something else' },
];

const MAX_DETAILS = 500;

export interface ReportTarget {
  type: 'post' | 'comment';
  id: string;
}

interface ReportModalProps {
  communityId: string;
  target: ReportTarget | null;
  onClose: () => void;
  onReported?: (target: ReportTarget) => void;
}

/**
 * Report a post or reply to the moderators.
 */
export function ReportModal({ communityId, target, onClose, onReported }: ReportModalProps) {
  const { theme } = useTheme();
  const isDark = theme === 'dark';
  const reportContent = useReportContent(communityId);
  const [reason, setReason] = useState<ReportReason | ''>('');
  const [details, setDetails] = useState('');

  useEffect(() => {
    if (target) {
      setReason('');
      setDetails('');
    }
  }, [target?.id]);

  const handleSubmit = async () => {
    if (!target || !reason) return;
    try {
      await reportContent.mutateAsync({
        target_type: target.type,
        target_id: target.id,
        reason,
        description: details.trim() || undefined,
      });
      onReported?.(target);
      onClose();
    } catch {
      // The mutation shows the error; keep the dialog open so the user can try again
    }
  };

  const thing = target?.type === 'comment' ? 'reply' : 'post';

  return (
    <Dialog open={target !== null} onOpenChange={(open) => { if (!open) onClose(); }}>
      <DialogContent className={`sm:max-w-[440px] border shadow-xl ${
        !isDark ? 'bg-white text-zinc-950 border-zinc-200' : 'bg-zinc-900 text-white border-zinc-800'
      }`}>
        <DialogHeader>
          <DialogTitle className={!isDark ? 'text-zinc-950' : 'text-white'}>
            Report this {thing}
          </DialogTitle>
          <DialogDescription className={!isDark ? 'text-zinc-500' : 'text-zinc-400'}>
            Moderators will review it. The author won't know who reported it.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="space-y-2">
            <Label htmlFor="report-reason" className={!isDark ? 'text-zinc-700' : 'text-zinc-300'}>
              Why are you reporting it?
            </Label>
            <Select value={reason} onValueChange={(value) => setReason(value as ReportReason)}>
              <SelectTrigger id="report-reason" className={`w-full border ${
                !isDark ? 'bg-white border-zinc-200 text-zinc-900' : 'bg-zinc-950 border-zinc-800 text-white'
              }`}>
                <SelectValue placeholder="Choose a reason" />
              </SelectTrigger>
              <SelectContent className={`border opacity-100 ${
                !isDark ? 'bg-white border-zinc-200 text-zinc-950' : 'bg-zinc-900 border-zinc-800 text-white'
              }`}>
                {REPORT_REASONS.map((item) => (
                  <SelectItem
                    key={item.value}
                    value={item.value}
                    className={`cursor-pointer ${
                      !isDark
                        ? 'text-zinc-900 hover:bg-zinc-100 focus:bg-zinc-100 focus:text-zinc-900'
                        : 'text-white hover:bg-zinc-800 focus:bg-zinc-800 focus:text-white'
                    }`}
                  >
                    {item.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {reason === 'self_harm' && (
            <div className="flex gap-3 rounded-lg border border-amber-500/40 bg-amber-500/10 p-3 text-sm">
              <LifeBuoy size={18} className="shrink-0 text-amber-600 mt-0.5" />
              <p className={!isDark ? 'text-zinc-700' : 'text-zinc-200'}>
                Our moderators will see this first. If someone is in immediate danger,
                contact your local emergency services.
              </p>
            </div>
          )}

          <div className="space-y-2">
            <Label htmlFor="report-details" className={!isDark ? 'text-zinc-700' : 'text-zinc-300'}>
              Details <span className="font-normal text-muted-foreground">(optional)</span>
            </Label>
            <Textarea
              id="report-details"
              value={details}
              onChange={(e) => setDetails(e.target.value.slice(0, MAX_DETAILS))}
              rows={3}
              placeholder="Anything that helps the moderators understand the problem"
              className={`resize-none ${!isDark ? 'bg-white border-zinc-200' : 'bg-zinc-950 border-zinc-800'}`}
            />
            <p className="text-xs text-muted-foreground text-right">{details.length}/{MAX_DETAILS}</p>
          </div>
        </div>

        <DialogFooter className="gap-2">
          <Button
            variant="outline"
            onClick={onClose}
            className={`cursor-pointer ${
              !isDark ? 'border-zinc-200 hover:bg-zinc-50 text-zinc-900' : 'border-zinc-800 hover:bg-zinc-800 text-white'
            }`}
          >
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={!reason || reportContent.isPending}
            variant="destructive"
            className="cursor-pointer bg-red-600 text-white hover:bg-red-700"
          >
            {reportContent.isPending ? 'Sending...' : 'Send report'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default ReportModal;
