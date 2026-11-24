import { BarChart3 } from 'lucide-react';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '../ui/dialog';
import { Skeleton } from '../ui/skeleton';
import { useTheme } from '../../contexts/ThemeContext';
import { useSurveyAnalytics } from '../../hooks/useSurvey';
import type { QuestionAnalytics } from '../../services/surveyService';

function Bars({ question }: { question: QuestionAnalytics }) {
  const entries = Object.entries(question.distribution ?? {}).sort((a, b) => b[1] - a[1]);
  const top = Math.max(1, ...entries.map(([, n]) => n));
  if (entries.length === 0) return null;
  return (
    <div className="space-y-1.5">
      {entries.map(([label, n]) => (
        <div key={label} className="flex items-center gap-3 text-sm">
          <span className="w-28 truncate text-muted-foreground" title={label}>{label}</span>
          <div className="flex-1 h-2.5 rounded-full bg-[hsl(var(--border))] overflow-hidden">
            <div className="h-full bg-primary-color rounded-full" style={{ width: `${(n / top) * 100}%` }} />
          </div>
          <span className="w-8 text-right tabular-nums">{n}</span>
        </div>
      ))}
    </div>
  );
}

export function SurveyAnalyticsModal({ surveyId, onClose }: { surveyId: string | null; onClose: () => void }) {
  const { theme } = useTheme();
  const isDark = theme === 'dark';
  const { data, isLoading, isError } = useSurveyAnalytics(surveyId ?? undefined);

  return (
    <Dialog open={!!surveyId} onOpenChange={o => !o && onClose()}>
      <DialogContent className={`sm:max-w-[600px] max-h-[85vh] overflow-y-auto border shadow-xl ${
        !isDark ? 'bg-white text-zinc-950 border-zinc-200' : 'bg-zinc-900 text-white border-zinc-800'}`}>
        <DialogHeader>
          <div className="mx-auto bg-[hsl(var(--primary)/0.1)] p-3 rounded-full mb-2 text-primary-color"><BarChart3 size={24} /></div>
          <DialogTitle className={`text-center text-xl font-bold ${!isDark ? 'text-zinc-950' : 'text-white'}`}>
            {data?.title ?? 'Survey Results'}
          </DialogTitle>
          <DialogDescription className={`text-center px-4 ${!isDark ? 'text-zinc-600' : 'text-zinc-400'}`}>
            {data ? `${data.total_responses} ${data.total_responses === 1 ? 'response' : 'responses'} · ${data.completed_assignments} of ${data.assigned} assigned completed` : 'Response summary'}
          </DialogDescription>
        </DialogHeader>

        {data && (
          <div className="grid grid-cols-2 gap-3 pt-2">
            <div className="rounded-xl border border-[hsl(var(--border))] p-3 text-center">
              <p className="text-2xl font-bold">{data.completion_rate != null ? `${data.completion_rate}%` : '—'}</p>
              <p className="text-xs text-muted-foreground">Completion rate</p>
            </div>
            <div className="rounded-xl border border-[hsl(var(--border))] p-3 text-center">
              <p className="text-2xl font-bold">{data.avg_completion_hours != null ? `${data.avg_completion_hours} h` : '—'}</p>
              <p className="text-xs text-muted-foreground">Average time to complete</p>
            </div>
          </div>
        )}

        {isLoading ? (
          <div className="space-y-3 py-4">{[...Array(3)].map((_, i) => <Skeleton key={i} className="h-20 w-full" />)}</div>
        ) : isError || !data ? (
          <p className="text-sm text-destructive py-4 text-center">Could not load the results.</p>
        ) : (
          <div className="space-y-5 py-4">
            {data.questions.map((q, i) => (
              <div key={q.question_id} className="space-y-2">
                <p className="font-semibold text-sm">{i + 1}. {q.question_text}</p>
                <p className="text-xs text-muted-foreground">
                  {q.answered} answered
                  {q.average != null && ` · average ${q.average.toFixed(1)} (min ${q.min}, max ${q.max})`}
                </p>
                <Bars question={q} />
              </div>
            ))}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
