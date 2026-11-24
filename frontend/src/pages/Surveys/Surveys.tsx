import { useNavigate } from 'react-router-dom';
import { ClipboardList, Clock, CheckCircle2, ArrowRight, CalendarClock, Settings2, Gift } from 'lucide-react';
import { Card } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Skeleton } from '../../components/ui/skeleton';
import { PageHeader } from '../../components/ui/PageHeader';
import { useAuthContext } from '../../contexts/AuthContext';
import { useAssignedSurveys, useCompletedSurveys, useSurveys } from '../../hooks/useSurvey';
import type { AssignedSurvey } from '../../services/surveyService';

const SIGN_IN_MESSAGE = 'Sign in to your Voche account to take surveys.';

export const canManageSurveys = (user: { user_type: string; is_verified?: boolean } | null | undefined) =>
  !!user && (user.user_type === 'admin' || user.user_type === 'org_member' || (user.user_type === 'hcp' && !!user.is_verified));

const formatDate = (value?: string | null) => (value ? new Date(value).toLocaleDateString() : null);

function SurveyRow({ title, meta, action }: { title: string; meta: React.ReactNode; action: React.ReactNode }) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 rounded-xl border border-[hsl(var(--border))] hover:bg-[hsl(var(--muted))] transition-colors">
      <div className="space-y-1 min-w-0">
        <p className="font-semibold truncate">{title}</p>
        <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">{meta}</div>
      </div>
      {action}
    </div>
  );
}

function SectionSkeleton() {
  return (
    <div className="space-y-3">
      {[...Array(2)].map((_, i) => <Skeleton key={i} className="h-16 w-full rounded-xl" />)}
    </div>
  );
}

export default function Surveys() {
  const navigate = useNavigate();
  const { user, isAuthenticated, openAuthModal } = useAuthContext();

  const assigned = useAssignedSurveys(isAuthenticated);
  const completed = useCompletedSurveys(isAuthenticated);
  const open = useSurveys(isAuthenticated);

  const assignedList = assigned.data ?? [];
  const toDo = assignedList.filter(a => a.status === 'pending' || a.status === 'in_progress');
  const assignedIds = new Set(assignedList.map(a => a.survey_id));
  const openSurveys = (open.data ?? []).filter(s => !s.already_completed && !assignedIds.has(s.survey_id));

  const takeButton = (a: Pick<AssignedSurvey, 'survey_id' | 'has_draft'>) => (
    <Button className="gap-2 cursor-pointer shrink-0" onClick={() => navigate(`/surveys/${a.survey_id}/take`)}>
      {a.has_draft ? 'Continue' : 'Start'} <ArrowRight size={16} />
    </Button>
  );

  return (
    <div className="container mx-auto p-4 md:p-8 space-y-8 animate-in fade-in duration-500">
      <PageHeader
        title="Surveys"
        description="Share your experience to help improve care and research. Your progress is saved as you go."
        badgeText={isAuthenticated ? `${toDo.length} To Complete` : undefined}
        variant="green"
        action={canManageSurveys(user) ? (
          <Button variant="hero" className="gap-2 font-semibold transition-transform hover:scale-105 cursor-pointer" onClick={() => navigate('/surveys/manage')}>
            <Settings2 size={20} /> Manage Surveys
          </Button>
        ) : undefined}
      />

      {!isAuthenticated ? (
        <Card className="p-12 text-center max-w-md mx-auto">
          <ClipboardList className="mx-auto mb-4 text-muted-foreground/30" size={48} />
          <h3 className="text-xl font-bold mb-2">Sign in to see your surveys</h3>
          <Button className="cursor-pointer" onClick={() => openAuthModal(SIGN_IN_MESSAGE)}>Sign In</Button>
        </Card>
      ) : (
        <>
          <Card className="p-6 border-[hsl(var(--border))] shadow-sm space-y-4">
            <h2 className="text-xl font-bold flex items-center gap-2"><CalendarClock className="text-accent" /> Assigned to you</h2>
            {assigned.isLoading ? <SectionSkeleton /> : assigned.isError ? (
              <p className="text-sm text-destructive">Could not load your assigned surveys.</p>
            ) : toDo.length === 0 ? (
              <p className="text-sm text-muted-foreground">Nothing waiting for you right now.</p>
            ) : (
              <div className="space-y-3">
                {toDo.map(a => (
                  <SurveyRow
                    key={a.survey_id}
                    title={a.title}
                    meta={<>
                      {a.status === 'in_progress' && <Badge className="bg-amber-100 text-amber-700 border-0">In progress</Badge>}
                      {a.trial_title && <span>{a.trial_title}</span>}
                      {a.estimated_time && <span className="flex items-center gap-1"><Clock size={12} /> {a.estimated_time}</span>}
                      {a.due_date && <span>Due {formatDate(a.due_date)}</span>}
                    </>}
                    action={takeButton(a)}
                  />
                ))}
              </div>
            )}
          </Card>

          <Card className="p-6 border-[hsl(var(--border))] shadow-sm space-y-4">
            <h2 className="text-xl font-bold flex items-center gap-2"><ClipboardList className="text-accent" /> Open surveys</h2>
            {open.isLoading ? <SectionSkeleton /> : open.isError ? (
              <p className="text-sm text-destructive">Could not load open surveys.</p>
            ) : openSurveys.length === 0 ? (
              <p className="text-sm text-muted-foreground">No other surveys are open right now.</p>
            ) : (
              <div className="space-y-3">
                {openSurveys.map(s => (
                  <SurveyRow
                    key={s.survey_id}
                    title={s.title}
                    meta={<>
                      {s.estimated_time && <span className="flex items-center gap-1"><Clock size={12} /> {s.estimated_time}</span>}
                      {s.incentive && <span className="flex items-center gap-1"><Gift size={12} /> {s.incentive}</span>}
                    </>}
                    action={takeButton({ survey_id: s.survey_id, has_draft: false })}
                  />
                ))}
              </div>
            )}
          </Card>

          <Card className="p-6 border-[hsl(var(--border))] shadow-sm space-y-4">
            <h2 className="text-xl font-bold flex items-center gap-2"><CheckCircle2 className="text-accent" /> Completed</h2>
            {completed.isLoading ? <SectionSkeleton /> : completed.isError ? (
              <p className="text-sm text-destructive">Could not load your completed surveys.</p>
            ) : (completed.data ?? []).length === 0 ? (
              <p className="text-sm text-muted-foreground">You have not completed any surveys yet.</p>
            ) : (
              <div className="space-y-3">
                {completed.data!.map(c => (
                  <SurveyRow
                    key={c.completion_id}
                    title={c.title}
                    meta={<span>Submitted {formatDate(c.submitted_at)}</span>}
                    action={<Badge className="bg-green-100 text-green-700 border-0 shrink-0">Completed</Badge>}
                  />
                ))}
              </div>
            )}
          </Card>
        </>
      )}
    </div>
  );
}
