import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, BarChart3, Loader2, Lock, Plus, Rocket, Trash2, UserPlus, X } from 'lucide-react';
import { Card } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Switch } from '../../components/ui/switch';
import { Skeleton } from '../../components/ui/skeleton';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { PageHeader } from '../../components/ui/PageHeader';
import { SurveyAnalyticsModal } from '../../components/surveys/SurveyAnalyticsModal';
import { AssignSurveyModal } from '../../components/surveys/AssignSurveyModal';
import { useAuthContext } from '../../contexts/AuthContext';
import { useChangeSurveyStatus, useCreateSurvey, useManagedSurveys } from '../../hooks/useSurvey';
import type { ManagedSurvey, NewSurvey, QuestionType, SurveyStatus } from '../../services/surveyService';
import { canManageSurveys } from './Surveys';
import Forbidden from '../Error/Forbidden';

const TYPE_LABELS: Record<QuestionType, string> = {
  single_choice: 'Single choice',
  multiple_choice: 'Multiple choice',
  yes_no: 'Yes / No',
  scale: 'Scale (1–5)',
  open_text: 'Open text',
  number: 'Number',
  date: 'Date',
};

const STATUS_STYLES: Record<SurveyStatus, string> = {
  draft: 'bg-gray-100 text-gray-700',
  active: 'bg-green-100 text-green-700',
  closed: 'bg-red-100 text-red-700',
};

interface DraftQuestion {
  text: string;
  type: QuestionType;
  required: boolean;
  options: string;                  // one per line
  branching: Record<string, number>; // answer value -> index of the question to jump to
}

const NEXT = 'next';
const blankQuestion = (): DraftQuestion => ({ text: '', type: 'single_choice', required: true, options: '', branching: {} });
const optionList = (q: DraftQuestion) => q.options.split('\n').map(o => o.trim()).filter(Boolean);
const branchValues = (q: DraftQuestion) =>
  q.type === 'yes_no' ? ['yes', 'no'] : q.type === 'single_choice' || q.type === 'multiple_choice' ? optionList(q) : [];
const hasOptions = (t: QuestionType) => t === 'single_choice' || t === 'multiple_choice';

function NewSurveyForm({ onDone }: { onDone: () => void }) {
  const create = useCreateSurvey();
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [estimatedTime, setEstimatedTime] = useState('');
  const [consentText, setConsentText] = useState('');
  const [publish, setPublish] = useState(false);
  const [questions, setQuestions] = useState<DraftQuestion[]>([blankQuestion()]);

  const update = (i: number, patch: Partial<DraftQuestion>) =>
    setQuestions(qs => qs.map((q, j) => (j === i ? { ...q, ...patch } : q)));

  const remove = (i: number) =>
    setQuestions(qs => qs.filter((_, j) => j !== i).map(q => ({
      ...q,
      branching: Object.fromEntries(Object.entries(q.branching)
        .filter(([, n]) => n !== i)
        .map(([v, n]) => [v, n > i ? n - 1 : n])),
    })));

  const valid = title.trim().length >= 3 && description.trim().length >= 3 && questions.every(q =>
    q.text.trim().length >= 3 && (!hasOptions(q.type) || optionList(q).length >= 2));

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const payload: NewSurvey = {
      title: title.trim(),
      description: description.trim(),
      estimated_time: estimatedTime.trim() || undefined,
      consent_text: consentText.trim() || undefined,
      status: publish ? 'active' : 'draft',
      questions: questions.map(q => {
        const values = branchValues(q);
        return {
          text: q.text.trim(),
          type: q.type,
          required: q.required,
          options: hasOptions(q.type) ? optionList(q) : undefined,
          branching: Object.entries(q.branching)
            .filter(([v]) => values.includes(v))
            .map(([value, next]) => ({ value, next })),
        };
      }),
    };
    create.mutate(payload, { onSuccess: onDone });
  };

  return (
    <Card className="p-6 border-[hsl(var(--border))] shadow-sm">
      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold">New survey</h2>
          <Button type="button" variant="ghost" size="icon" className="cursor-pointer" onClick={onDone} aria-label="Close"><X size={18} /></Button>
        </div>

        <div className="grid md:grid-cols-2 gap-4">
          <div className="space-y-2 md:col-span-2">
            <Label htmlFor="survey-title">Title</Label>
            <Input id="survey-title" value={title} onChange={e => setTitle(e.target.value)} placeholder="e.g. Side effects check-in" className="h-11" />
          </div>
          <div className="space-y-2 md:col-span-2">
            <Label htmlFor="survey-description">Description</Label>
            <Textarea id="survey-description" value={description} onChange={e => setDescription(e.target.value)} className="border border-[hsl(var(--border))] resize-none min-h-[80px]" placeholder="What the survey is about and who it is for" />
          </div>
          <div className="space-y-2">
            <Label htmlFor="survey-time">Estimated time</Label>
            <Input id="survey-time" value={estimatedTime} onChange={e => setEstimatedTime(e.target.value)} placeholder="e.g. 5 minutes" className="h-11" />
          </div>
          <div className="flex items-center gap-3 pt-7">
            <Switch id="survey-publish" checked={publish} onCheckedChange={setPublish} />
            <Label htmlFor="survey-publish" className="cursor-pointer">Publish immediately</Label>
          </div>
          <div className="space-y-2 md:col-span-2">
            <Label htmlFor="survey-consent">Consent text (optional)</Label>
            <Textarea id="survey-consent" value={consentText} onChange={e => setConsentText(e.target.value)} className="border border-[hsl(var(--border))] resize-none min-h-[70px]" placeholder="Shown before the first question. A default is used when empty." />
          </div>
        </div>

        <div className="space-y-4">
          {questions.map((q, i) => {
            const values = branchValues(q);
            const later = questions.map((other, k) => ({ k, other })).filter(({ k }) => k > i);
            return (
              <div key={i} className="rounded-xl border border-[hsl(var(--border))] p-4 space-y-4">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-sm">Question {i + 1}</span>
                  <Button type="button" variant="ghost" size="icon" className="cursor-pointer text-destructive"
                    disabled={questions.length === 1} onClick={() => remove(i)} aria-label={`Remove question ${i + 1}`}>
                    <Trash2 size={16} />
                  </Button>
                </div>
                <Input value={q.text} onChange={e => update(i, { text: e.target.value })} placeholder="Question text" className="h-11" aria-label={`Question ${i + 1} text`} />
                <div className="flex flex-col sm:flex-row gap-4 sm:items-center">
                  <div className="sm:w-56">
                    <Select value={q.type} onValueChange={v => update(i, { type: v as QuestionType, branching: {} })}>
                      <SelectTrigger className="h-11" aria-label={`Question ${i + 1} type`}><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {Object.entries(TYPE_LABELS).map(([value, label]) => <SelectItem key={value} value={value}>{label}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="flex items-center gap-3">
                    <Switch id={`q-required-${i}`} checked={q.required} onCheckedChange={v => update(i, { required: v })} />
                    <Label htmlFor={`q-required-${i}`} className="cursor-pointer">Required</Label>
                  </div>
                </div>
                {hasOptions(q.type) && (
                  <Textarea value={q.options} onChange={e => update(i, { options: e.target.value })}
                    placeholder={'One option per line\nOption A\nOption B'} className="border border-[hsl(var(--border))] resize-none min-h-[90px]" aria-label={`Question ${i + 1} options`} />
                )}
                {values.length > 0 && later.length > 0 && (
                  <div className="space-y-2">
                    <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Branching</p>
                    {values.map(v => (
                      <div key={v} className="flex items-center gap-3 text-sm">
                        <span className="w-32 truncate">If “{v}”</span>
                        <Select value={q.branching[v] !== undefined ? String(q.branching[v]) : NEXT}
                          onValueChange={sel => {
                            const branching = { ...q.branching };
                            if (sel === NEXT) delete branching[v]; else branching[v] = Number(sel);
                            update(i, { branching });
                          }}>
                          <SelectTrigger className="h-9 flex-1" aria-label={`Question ${i + 1}, if ${v}`}><SelectValue /></SelectTrigger>
                          <SelectContent>
                            <SelectItem value={NEXT}>Go to the next question</SelectItem>
                            {later.map(({ k, other }) => (
                              <SelectItem key={k} value={String(k)}>Jump to question {k + 1}{other.text ? `: ${other.text.slice(0, 40)}` : ''}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
          <Button type="button" variant="outline" className="gap-2 cursor-pointer" onClick={() => setQuestions(qs => [...qs, blankQuestion()])}>
            <Plus size={16} /> Add question
          </Button>
        </div>

        <div className="flex justify-end gap-3">
          <Button type="button" variant="ghost" className="cursor-pointer" onClick={onDone}>Cancel</Button>
          <Button type="submit" className="gap-2 cursor-pointer" disabled={!valid || create.isPending}>
            {create.isPending && <Loader2 size={16} className="animate-spin" />}
            {publish ? 'Create and publish' : 'Save as draft'}
          </Button>
        </div>
      </form>
    </Card>
  );
}

export default function SurveyBuilder() {
  const navigate = useNavigate();
  const { user, isAuthenticated, openAuthModal } = useAuthContext();
  const allowed = canManageSurveys(user);
  const { data: surveys = [], isLoading, isError } = useManagedSurveys(allowed);
  const changeStatus = useChangeSurveyStatus();

  const [creating, setCreating] = useState(false);
  const [analyticsFor, setAnalyticsFor] = useState<string | null>(null);
  const [assignFor, setAssignFor] = useState<ManagedSurvey | null>(null);

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Card className="p-12 text-center max-w-md">
          <h3 className="text-xl font-bold mb-2">Sign in to manage surveys</h3>
          <Button className="cursor-pointer" onClick={() => openAuthModal('Sign in to your Voche account to manage surveys.')}>Sign In</Button>
        </Card>
      </div>
    );
  }
  if (!allowed) return <Forbidden />;

  return (
    <div className="container mx-auto p-4 md:p-8 space-y-8 animate-in fade-in duration-500">
      <button type="button" onClick={() => navigate('/surveys')}
        className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors cursor-pointer">
        <ArrowLeft size={16} /> All surveys
      </button>

      <PageHeader
        title="Manage Surveys"
        description="Create surveys with branching questions, publish them, assign them to patients and follow the results."
        badgeText={`${surveys.length} ${surveys.length === 1 ? "Survey" : "Surveys"}`}
        variant="green"
        action={!creating ? (
          <Button variant="hero" className="gap-2 font-semibold transition-transform hover:scale-105 cursor-pointer" onClick={() => setCreating(true)}>
            <Plus size={20} className="stroke-[3px]" /> New Survey
          </Button>
        ) : undefined}
      />

      {creating && <NewSurveyForm onDone={() => setCreating(false)} />}

      <Card className="p-6 border-[hsl(var(--border))] shadow-sm space-y-4">
        <h2 className="text-xl font-bold">All surveys</h2>
        {isLoading ? (
          <div className="space-y-3">{[...Array(3)].map((_, i) => <Skeleton key={i} className="h-16 w-full rounded-xl" />)}</div>
        ) : isError ? (
          <p className="text-sm text-destructive">Could not load surveys.</p>
        ) : surveys.length === 0 ? (
          <p className="text-sm text-muted-foreground">No surveys yet. Create the first one.</p>
        ) : (
          <div className="space-y-3">
            {surveys.map(s => {
              const pending = changeStatus.isPending && changeStatus.variables?.surveyId === s.survey_id;
              return (
                <div key={s.survey_id} className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 p-4 rounded-xl border border-[hsl(var(--border))]">
                  <div className="space-y-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="font-semibold truncate">{s.title}</p>
                      <Badge className={`${STATUS_STYLES[s.status]} border-0 capitalize`}>{s.status}</Badge>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {s.question_count} questions · {s.responses} responses · {s.assigned} assigned · created {new Date(s.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2 shrink-0">
                    {s.status === 'draft' && (
                      <Button size="sm" className="gap-1.5 cursor-pointer" disabled={pending}
                        onClick={() => changeStatus.mutate({ surveyId: s.survey_id, status: 'active' })}>
                        {pending ? <Loader2 size={14} className="animate-spin" /> : <Rocket size={14} />} Publish
                      </Button>
                    )}
                    {s.status === 'active' && (
                      <>
                        <Button size="sm" variant="outline" className="gap-1.5 cursor-pointer" onClick={() => setAssignFor(s)}>
                          <UserPlus size={14} /> Assign
                        </Button>
                        <Button size="sm" variant="outline" className="gap-1.5 cursor-pointer" disabled={pending}
                          onClick={() => changeStatus.mutate({ surveyId: s.survey_id, status: 'closed' })}>
                          {pending ? <Loader2 size={14} className="animate-spin" /> : <Lock size={14} />} Close
                        </Button>
                      </>
                    )}
                    <Button size="sm" variant="outline" className="gap-1.5 cursor-pointer" onClick={() => setAnalyticsFor(s.survey_id)}>
                      <BarChart3 size={14} /> Results
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </Card>

      <SurveyAnalyticsModal surveyId={analyticsFor} onClose={() => setAnalyticsFor(null)} />
      <AssignSurveyModal survey={assignFor} onClose={() => setAssignFor(null)} />
    </div>
  );
}
