import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, ArrowRight, CheckCircle2, ClipboardList, Clock, Loader2, ShieldCheck } from 'lucide-react';
import { Card } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Textarea } from '../../components/ui/textarea';
import { Checkbox } from '../../components/ui/checkbox';
import { Label } from '../../components/ui/label';
import { Skeleton } from '../../components/ui/skeleton';
import { useAuthContext } from '../../contexts/AuthContext';
import { useSaveSurveyDraft, useSubmitSurvey, useSurveyById } from '../../hooks/useSurvey';
import { answerPath, isEmptyAnswer } from '../../services/surveyService';
import type { Answer, SurveyQuestion } from '../../services/surveyService';

const SIGN_IN_MESSAGE = 'Sign in to your Voche account to take surveys.';
const SCALE = [1, 2, 3, 4, 5];

function ChoiceButton({ selected, onClick, children }: { selected: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`w-full text-left px-4 py-3 rounded-xl border transition-colors cursor-pointer ${selected ? 'border-[hsl(var(--primary))] bg-[hsl(var(--primary)/0.1)] font-semibold' : 'border-[hsl(var(--border))] hover:bg-[hsl(var(--muted))]'}`}
    >
      {children}
    </button>
  );
}

function QuestionInput({ question, value, onChange }: { question: SurveyQuestion; value: Answer | undefined; onChange: (v: Answer) => void }) {
  switch (question.type) {
    case 'yes_no':
      return (
        <div className="grid grid-cols-2 gap-3">
          {['yes', 'no'].map(v => (
            <ChoiceButton key={v} selected={value === v} onClick={() => onChange(v)}>{v === 'yes' ? 'Yes' : 'No'}</ChoiceButton>
          ))}
        </div>
      );
    case 'single_choice':
      return (
        <div className="space-y-2">
          {(question.options ?? []).map(o => (
            <ChoiceButton key={o} selected={value === o} onClick={() => onChange(o)}>{o}</ChoiceButton>
          ))}
        </div>
      );
    case 'multiple_choice': {
      const selected = Array.isArray(value) ? value : [];
      return (
        <div className="space-y-2">
          {(question.options ?? []).map(o => (
            <ChoiceButton key={o} selected={selected.includes(o)}
              onClick={() => onChange(selected.includes(o) ? selected.filter(s => s !== o) : [...selected, o])}>
              {o}
            </ChoiceButton>
          ))}
          <p className="text-xs text-muted-foreground">Select all that apply.</p>
        </div>
      );
    }
    case 'scale':
      return (
        <div className="space-y-2">
          <div className="grid grid-cols-5 gap-2">
            {SCALE.map(n => (
              <ChoiceButton key={n} selected={Number(value) === n} onClick={() => onChange(n)}>
                <span className="block text-center">{n}</span>
              </ChoiceButton>
            ))}
          </div>
          <div className="flex justify-between text-xs text-muted-foreground"><span>Poor</span><span>Excellent</span></div>
        </div>
      );
    case 'number':
      return <Input type="number" value={value === undefined ? '' : String(value)}
        onChange={e => onChange(e.target.value === '' ? '' : Number(e.target.value))} className="h-11" />;
    case 'date':
      return <Input type="date" value={(value as string) ?? ''} onChange={e => onChange(e.target.value)} className="h-11" />;
    default:
      return <Textarea rows={5} value={(value as string) ?? ''} onChange={e => onChange(e.target.value)} placeholder="Type your answer..." />;
  }
}

export default function SurveyRunner() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { isAuthenticated, openAuthModal } = useAuthContext();

  const { data: survey, isLoading, isError, error } = useSurveyById(id);
  const saveDraft = useSaveSurveyDraft();
  const submit = useSubmitSurvey();

  const [answers, setAnswers] = useState<Record<string, Answer>>({});
  const [step, setStep] = useState(-1); // -1 = introduction and consent
  const [consent, setConsent] = useState(false);
  const [savedAt, setSavedAt] = useState<Date | null>(null);
  const [done, setDone] = useState(false);
  const loadedDraft = useRef(false);
  const dirty = useRef(false);

  useEffect(() => {
    if (survey && !loadedDraft.current) {
      loadedDraft.current = true;
      if (survey.draft_answers && Object.keys(survey.draft_answers).length > 0) {
        setAnswers(survey.draft_answers);
        setConsent(true);
      }
    }
  }, [survey]);

  const path = useMemo(() => (survey ? answerPath(survey.questions, answers) : []), [survey, answers]);
  const current = step >= 0 ? path[step] : undefined;
  const isLast = step === path.length - 1;

  // Auto-save a draft one second after the last change
  useEffect(() => {
    if (!dirty.current || !id || !isAuthenticated || done) return;
    const timer = setTimeout(() => {
      const onPath = Object.fromEntries(path.map(q => [q.question_id, answers[q.question_id]]).filter(([, a]) => !isEmptyAnswer(a as Answer)));
      saveDraft.mutate({ surveyId: id, answers: onPath }, { onSuccess: () => setSavedAt(new Date()) });
    }, 1000);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [answers]);

  const setAnswer = (questionId: string, value: Answer) => {
    dirty.current = true;
    setAnswers(prev => ({ ...prev, [questionId]: value }));
  };

  const canContinue = step === -1 ? consent : !!current && (!current.required || !isEmptyAnswer(answers[current.question_id]));

  const handleNext = () => {
    if (!isAuthenticated) {
      openAuthModal(SIGN_IN_MESSAGE);
      return;
    }
    if (!isLast) {
      setStep(s => s + 1);
      return;
    }
    const responses = path
      .filter(q => !isEmptyAnswer(answers[q.question_id]))
      .map(q => ({ question_id: q.question_id, answer: answers[q.question_id] }));
    submit.mutate(
      { surveyId: id!, payload: { consent_given: consent, anonymous: false, responses } },
      { onSuccess: () => setDone(true) },
    );
  };

  if (isLoading) {
    return (
      <div className="container mx-auto p-4 md:p-8 max-w-2xl space-y-4">
        <Skeleton className="h-8 w-2/3" />
        <Skeleton className="h-64 w-full rounded-xl" />
      </div>
    );
  }

  if (isError || !survey) {
    const status = (error as { status?: number } | null)?.status;
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Card className="p-12 text-center max-w-md">
          <ClipboardList className="mx-auto mb-4 text-muted-foreground/30" size={48} />
          <h3 className="text-xl font-bold mb-2">{status === 404 ? 'Survey not found' : 'Failed to load survey'}</h3>
          <Button className="cursor-pointer" onClick={() => navigate('/surveys')}>Back to Surveys</Button>
        </Card>
      </div>
    );
  }

  if (done) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Card className="p-12 text-center max-w-md">
          <CheckCircle2 className="mx-auto mb-4 text-green-600" size={48} />
          <h3 className="text-xl font-bold mb-2">Thank you!</h3>
          <p className="text-muted-foreground mb-6">Your responses to "{survey.title}" have been recorded.</p>
          <Button className="cursor-pointer" onClick={() => navigate('/surveys')}>Back to Surveys</Button>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-4 md:p-8 max-w-2xl space-y-6 animate-in fade-in duration-500">
      <button type="button" onClick={() => navigate('/surveys')}
        className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors cursor-pointer">
        <ArrowLeft size={16} /> All surveys
      </button>

      <div className="space-y-2">
        <h1 className="text-2xl md:text-3xl font-bold">{survey.title}</h1>
        {step >= 0 && (
          <div className="flex items-center gap-3">
            <div className="flex-1 h-2 rounded-full bg-[hsl(var(--border))] overflow-hidden">
              <div className="h-full bg-primary-color transition-all" style={{ width: `${((step + 1) / path.length) * 100}%` }} />
            </div>
            <span className="text-xs text-muted-foreground whitespace-nowrap">Question {step + 1} of {path.length}</span>
          </div>
        )}
      </div>

      <Card className="p-6 border-[hsl(var(--border))] shadow-sm space-y-6">
        {step === -1 ? (
          <>
            <p className="text-muted-foreground">{survey.description}</p>
            {survey.estimated_time && (
              <p className="flex items-center gap-2 text-sm text-muted-foreground"><Clock size={14} /> {survey.estimated_time}</p>
            )}
            <div className="rounded-xl bg-[hsl(var(--muted))] p-4 space-y-3">
              <p className="flex items-center gap-2 font-semibold"><ShieldCheck size={18} className="text-primary-color" /> Consent</p>
              <p className="text-sm text-muted-foreground whitespace-pre-line">
                {survey.consent_text || 'Your answers will be used to improve care and research. You can stop at any time; your progress is saved.'}
              </p>
              <div className="flex items-start gap-3">
                <Checkbox id="survey-consent" checked={consent} onCheckedChange={v => setConsent(v === true)} className="mt-0.5" />
                <Label htmlFor="survey-consent" className="text-sm leading-snug cursor-pointer">I have read the above and agree to take part.</Label>
              </div>
            </div>
          </>
        ) : current && (
          <div className="space-y-4">
            <h2 className="text-lg font-semibold">
              {current.text}
              {current.required && <span className="text-destructive ml-1">*</span>}
            </h2>
            <QuestionInput question={current} value={answers[current.question_id]} onChange={v => setAnswer(current.question_id, v)} />
          </div>
        )}

        <div className="flex items-center justify-between gap-3 pt-2">
          <Button variant="ghost" className="gap-2 cursor-pointer" disabled={step === -1 || submit.isPending} onClick={() => setStep(s => s - 1)}>
            <ArrowLeft size={16} /> Back
          </Button>
          <span className="text-xs text-muted-foreground">
            {saveDraft.isPending ? 'Saving…' : savedAt ? `Progress saved ${savedAt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}` : ''}
          </span>
          <Button className="gap-2 cursor-pointer" disabled={!canContinue || submit.isPending} onClick={handleNext}>
            {submit.isPending ? <><Loader2 className="animate-spin" size={16} /> Submitting...</>
              : step === -1 ? <>Start <ArrowRight size={16} /></>
              : isLast ? 'Submit'
              : <>Next <ArrowRight size={16} /></>}
          </Button>
        </div>
      </Card>
    </div>
  );
}
