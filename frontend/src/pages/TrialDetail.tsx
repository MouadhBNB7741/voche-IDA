import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useData } from '../contexts/DataContext';
import { Card } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import {
  ArrowLeft,
  Heart,
  MapPin,
  Calendar,
  Building,
  Clock,
  CheckCircle2,
  XCircle,
  HelpCircle,
  ChevronRight,
  ShieldCheck,
  Activity,
  FlaskConical
} from 'lucide-react';
import { trialService } from '../services/TrialService';
import type { Trial } from '../data/mockData';
import { toast } from 'sonner';
import { PageHeader } from '../components/ui/PageHeader';

// Eligibility Quiz Questions
const eligibilityQuestions = [
  {
    id: 1,
    question: 'Are you within the required age range for this trial?',
    type: 'yesno' as const,
  },
  {
    id: 2,
    question: 'Have you been diagnosed with the condition this trial is studying?',
    type: 'yesno' as const,
  },
  {
    id: 3,
    question: 'Are you currently taking any medications for this condition?',
    type: 'choice' as const,
    options: ['No medications', 'Some medications', 'Multiple medications'],
  },
  {
    id: 4,
    question: 'Have you participated in a clinical trial before?',
    type: 'yesno' as const,
  },
  {
    id: 5,
    question: 'Are you able to travel to the trial location for regular visits?',
    type: 'yesno' as const,
  },
];

export default function TrialDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [trial, setTrial] = useState<Trial | null>(null);
  const { state, actions } = useData();
  const [isSaved, setIsSaved] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [showQuiz, setShowQuiz] = useState(false);
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [quizComplete, setQuizComplete] = useState(false);

  useEffect(() => {
    if (id) {
      const foundTrial = trialService.getById(id);
      setTrial(foundTrial || null);
      setIsConnected(trialService.isTrialConnected(id));
    }
  }, [id]);

  useEffect(() => {
    if (id) {
      setIsSaved(state.savedTrials.includes(id));
    }
  }, [id, state.savedTrials]);

  const handleSave = () => {
    if (id) {
      if (isSaved) {
        actions.unsaveTrial(id);
        toast.success('Trial Removed', {
          description: 'This trial has been removed from your saved trials.'
        });
      } else {
        actions.saveTrial(id);
        toast.success('Trial Saved', {
          description: 'This trial has been added to your saved trials.'
        });
      }
    }
  };

  const handleConnect = () => {
    if (id) {
      if (isConnected) {
        toast.info('Request Already Pending', {
          description: 'You have already requested to connect with this trial.',
        });
        return;
      }

      trialService.connectTrial(id);
      setIsConnected(true);
      toast.success('Connection Request Sent', {
        description: 'A trial coordinator will review your profile and contact you shortly.',
      });
    }
  };

  const handleAnswer = (answer: string) => {
    setAnswers(prev => ({ ...prev, [eligibilityQuestions[currentQuestion].id]: answer }));

    if (currentQuestion < eligibilityQuestions.length - 1) {
      setCurrentQuestion(prev => prev + 1);
    } else {
      setQuizComplete(true);
    }
  };

  const getEligibilityResult = () => {
    // Simple mock logic: if user answers mostly positively
    const yesCount = Object.values(answers).filter(a => a === 'Yes' || a === 'No medications').length;
    return yesCount >= 3;
  };

  const resetQuiz = () => {
    setCurrentQuestion(0);
    setAnswers({});
    setQuizComplete(false);
    setShowQuiz(false);
  };

  if (!trial) {
    return (
      <div className="container mx-auto p-4 md:p-8">
        <Card className="p-16 text-center border-dashed">
          <Activity className="mx-auto mb-4 text-muted-foreground opacity-50" size={64} />
          <h2 className="text-xl font-semibold mb-2">Trial not found</h2>
          <p className="text-muted-foreground mb-6">The trial you're looking for doesn't exist.</p>
          <Button onClick={() => navigate('/trials')}>Back to Trials</Button>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-4 md:p-8 space-y-6 animate-in fade-in duration-500">
      {/* Back Button */}
      <div>
        <Button variant="ghost" onClick={() => navigate('/trials')} className="gap-2 pl-0 hover:bg-transparent hover:text-primary transition-colors">
          <ArrowLeft size={16} />
          Back to Trials
        </Button>
      </div>

      <PageHeader
        title={trial.title}
        description={trial.description}
        variant="green"
        badgeText={`${trial.disease} • ${trial.phase}`}
        className="mb-8"
        action={
          <div className="flex flex-col sm:flex-row gap-3 min-w-[200px] justify-center sm:justify-end">
            <Button
              className={`font-bold shadow-lg h-12 px-6 rounded-xl transition-all hover:scale-105 ${isConnected
                ? 'bg-success hover:bg-success/90 text-success-foreground cursor-default'
                : 'bg-white text-primary hover:bg-white/90'
                }`}
              onClick={handleConnect}
              disabled={isConnected}
            >
              {isConnected ? (
                <>
                  <CheckCircle2 size={18} className="mr-2" /> Request Pending
                </>
              ) : (
                'Connect with Trial'
              )}
            </Button>
            <Button
              variant="outline"
              className={`h-12 px-4 rounded-xl border transition-colors ${isSaved
                ? 'bg-white/20 border-white/40 text-white hover:bg-white/30' // Saved state: glass
                : 'bg-transparent border-white/30 text-white hover:bg-white/10' // Default: outline white
                }`}
              onClick={handleSave}
            >
              <Heart
                size={20}
                className={`mr-2 transition-transform duration-300 ${isSaved ? 'fill-red-500 text-red-500 scale-110' : ''}`}
              />
              {isSaved ? 'Saved' : 'Save'}
            </Button>
            {/* HCP Only: Download Protocol */}
            {/* @ts-ignore - Mocking user role check without context for now */}
            {(localStorage.getItem('voce_user') && JSON.parse(localStorage.getItem('voce_user')!)?.role === 'hcp') && (
              <Button
                variant="outline"
                className="h-12 px-4 rounded-xl border border-white/30 text-white hover:bg-white/10"
                onClick={() => toast.success("Protocol Downloaded", { description: "PDF has been saved to your device." })}
              >
                <ShieldCheck size={20} className="mr-2" />
                Protocol
              </Button>
            )}
          </div>
        }
      />

      < div className="grid lg:grid-cols-3 gap-8" >
        {/* Main Content */}
        < div className="lg:col-span-2 space-y-8" >
          {/* Overview */}
          < Card className="p-6 md:p-8 border-border/60 shadow-sm" >
            <h2 className="text-xl font-bold mb-6 flex items-center gap-2">
              <Activity size={20} className="text-primary" />
              Overview
            </h2>
            <div className="grid sm:grid-cols-2 gap-6">
              <div className="flex items-start gap-4 p-4 bg-muted/30 rounded-xl border border-transparent hover:border-primary/20 transition-colors">
                <Building className="text-primary mt-1" size={20} />
                <div>
                  <div className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-1">Sponsor</div>
                  <div className="font-medium">{trial.sponsor}</div>
                </div>
              </div>
              <div className="flex items-start gap-4 p-4 bg-muted/30 rounded-xl border border-transparent hover:border-primary/20 transition-colors">
                <MapPin className="text-primary mt-1" size={20} />
                <div>
                  <div className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-1">Location</div>
                  <div className="font-medium">{trial.location}</div>
                </div>
              </div>
              <div className="flex items-start gap-4 p-4 bg-muted/30 rounded-xl border border-transparent hover:border-primary/20 transition-colors">
                <Calendar className="text-primary mt-1" size={20} />
                <div>
                  <div className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-1">Start Date</div>
                  <div className="font-medium">{new Date(trial.startDate).toLocaleDateString()}</div>
                </div>
              </div>
              <div className="flex items-start gap-4 p-4 bg-muted/30 rounded-xl border border-transparent hover:border-primary/20 transition-colors">
                <Clock className="text-primary mt-1" size={20} />
                <div>
                  <div className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-1">Est. Completion</div>
                  <div className="font-medium">{new Date(trial.estimatedCompletion).toLocaleDateString()}</div>
                </div>
              </div>
            </div>

            {/* Enrollment Progress */}
            <div className="mt-8 pt-6 border-t border-dashed">
              <div className="flex justify-between text-sm mb-2 font-medium">
                <span className="text-muted-foreground">Enrollment Progress</span>
                <span className="text-primary font-bold">{trial.enrollment} / {trial.maxEnrollment} Participants</span>
              </div>
              <div className="h-3 bg-muted rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary rounded-full transition-all duration-1000 ease-out relative overflow-hidden"
                  style={{ width: `${(trial.enrollment / trial.maxEnrollment) * 100}%` }}
                >
                  <div className="absolute inset-0 bg-white/20 animate-[shimmer_2s_infinite]"></div>
                </div>
              </div>
            </div>
          </Card >

          {/* Eligibility Criteria */}
          < Card className="p-6 md:p-8 border-border/60 shadow-sm" >
            <h2 className="text-xl font-bold mb-6 flex items-center gap-2">
              <ShieldCheck size={20} className="text-primary" />
              Eligibility Criteria
            </h2>
            <div className="space-y-4">
              {trial.eligibility.map((criteria, index) => (
                <div key={index} className="flex items-center gap-4 p-4 bg-muted/20 rounded-xl border border-muted hover:border-primary/20 transition-colors">
                  <div className="bg-success/10 p-1.5 rounded-full shrink-0">
                    <CheckCircle2 className="text-success" size={18} />
                  </div>
                  <span className="font-medium text-foreground/90">{criteria}</span>
                </div>
              ))}
            </div>
          </Card >

          {/* Eligibility Quiz Section */}
          < Card className="p-6 md:p-8 border-l-4 border-l-primary shadow-lg overflow-hidden relative" >
            <div className="absolute top-0 right-0 p-8 opacity-5 pointer-events-none">
              <FlaskConical size={140} />
            </div>

            <h2 className="text-xl font-bold mb-6">Eligibility Quiz</h2>

            {
              !showQuiz && !quizComplete && (
                <div className="text-center py-8">
                  <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-6 ring-4 ring-primary/5">
                    <HelpCircle className="text-primary" size={32} />
                  </div>
                  <h3 className="font-bold text-lg mb-2">Check Your Eligibility</h3>
                  <p className="text-muted-foreground mb-8 max-w-md mx-auto">
                    Take a quick 5-question quiz to see if you might be a good fit for this clinical trial.
                  </p>
                  <Button onClick={() => setShowQuiz(true)} size="lg" className="shadow-md rounded-xl px-8">Start Eligibility Check</Button>
                </div>
              )
            }

            {
              showQuiz && !quizComplete && (
                <div className="space-y-8 animate-in fade-in slide-in-from-bottom-2">
                  {/* Progress */}
                  <div className="space-y-2">
                    <div className="flex justify-between text-xs font-bold uppercase tracking-wider text-muted-foreground">
                      <span>Quiz Progress</span>
                      <span>{Math.round(((currentQuestion + 1) / eligibilityQuestions.length) * 100)}%</span>
                    </div>
                    <div className="flex gap-1.5">
                      {eligibilityQuestions.map((_, idx) => (
                        <div
                          key={idx}
                          className={`h-2 flex-1 rounded-full transition-colors duration-300 ${idx <= currentQuestion ? 'bg-primary' : 'bg-muted'
                            }`}
                        />
                      ))}
                    </div>
                  </div>

                  {/* Question */}
                  <div className="py-2">
                    <div className="text-sm font-bold text-primary mb-2 uppercase tracking-wide">
                      Question {currentQuestion + 1}
                    </div>
                    <h3 className="text-2xl font-bold mb-8 leading-tight">
                      {eligibilityQuestions[currentQuestion].question}
                    </h3>

                    <div className="space-y-3">
                      {eligibilityQuestions[currentQuestion].type === 'yesno' ? (
                        <div className="grid grid-cols-2 gap-4">
                          <Button
                            variant="outline"
                            className="h-16 text-lg font-medium hover:bg-primary hover:text-primary-foreground hover:border-primary transition-all rounded-xl"
                            onClick={() => handleAnswer('Yes')}
                          >
                            Yes
                          </Button>
                          <Button
                            variant="outline"
                            className="h-16 text-lg font-medium hover:bg-primary hover:text-primary-foreground hover:border-primary transition-all rounded-xl"
                            onClick={() => handleAnswer('No')}
                          >
                            No
                          </Button>
                        </div>
                      ) : (
                        <div className="space-y-3">
                          {eligibilityQuestions[currentQuestion].options?.map((option) => (
                            <Button
                              key={option}
                              variant="outline"
                              className="w-full justify-start h-14 text-base px-6 hover:bg-primary hover:text-primary-foreground hover:border-primary transition-all rounded-xl"
                              onClick={() => handleAnswer(option)}
                            >
                              {option}
                            </Button>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )
            }

            {
              quizComplete && (
                <div className="text-center py-8 animate-in zoom-in duration-300">
                  {getEligibilityResult() ? (
                    <>
                      <div className="w-20 h-20 bg-success/10 rounded-full flex items-center justify-center mx-auto mb-6 ring-4 ring-success/5">
                        <CheckCircle2 className="text-success" size={40} />
                      </div>
                      <h3 className="text-2xl font-bold text-success mb-3">You May Be Eligible!</h3>
                      <p className="text-muted-foreground mb-8 max-w-md mx-auto text-lg leading-relaxed">
                        Based on your answers, you appear to be a good candidate for this trial.
                      </p>
                      <div className="flex flex-col sm:flex-row gap-4 justify-center">
                        <Button onClick={handleConnect} size="lg" className="shadow-lg h-12 px-8 rounded-xl" disabled={isConnected}>
                          {isConnected ? 'Request Pending' : 'Connect with Trial Now'}
                        </Button>
                        <Button variant="outline" onClick={resetQuiz} className="h-12 rounded-xl">Retake Quiz</Button>
                      </div>
                    </>
                  ) : (
                    <>
                      <div className="w-20 h-20 bg-warning/10 rounded-full flex items-center justify-center mx-auto mb-6 ring-4 ring-warning/5">
                        <XCircle className="text-warning" size={40} />
                      </div>
                      <h3 className="text-2xl font-bold text-foreground mb-3">Eligibility Uncertain</h3>
                      <p className="text-muted-foreground mb-8 max-w-md mx-auto leading-relaxed">
                        Based on your answers, you might not meet all criteria. However, we recommend consulting with a healthcare provider to be sure.
                      </p>
                      <div className="flex flex-col sm:flex-row gap-4 justify-center">
                        <Button variant="outline" onClick={resetQuiz} className="h-12 rounded-xl">Retake Quiz</Button>
                        <Button variant="default" asChild className="h-12 rounded-xl">
                          <Link to="/trials">Browse Other Trials</Link>
                        </Button>
                      </div>
                    </>
                  )}
                </div>
              )
            }
          </Card >

          {/* Locations */}
          < Card className="p-6 md:p-8 border-border/60 shadow-sm" >
            <h2 className="text-xl font-bold mb-6 flex items-center gap-2">
              <MapPin size={20} className="text-primary" />
              Trial Locations
            </h2>
            <div className="space-y-3">
              <div className="flex items-center justify-between p-5 bg-muted/20 rounded-xl border hover:border-primary/30 transition-colors">
                <div className="flex items-center gap-4">
                  <div className="bg-primary/10 p-2.5 rounded-full">
                    <MapPin className="text-primary" size={20} />
                  </div>
                  <div>
                    <div className="font-bold text-lg">{trial.location}</div>
                    <div className="text-sm text-muted-foreground">Primary Research Center</div>
                  </div>
                </div>
                <Badge className="bg-success text-success-foreground hover:bg-success/90 h-7 px-3">Enrolling</Badge>
              </div>
            </div>
          </Card >
        </div >

        {/* Sidebar */}
        < div className="space-y-6" >
          {/* Contact Card */}
          < Card className="p-6 border-border/60 shadow-sm" >
            <h3 className="font-bold mb-4 text-lg">Contact Information</h3>
            <div className="space-y-4 p-4 bg-muted/30 rounded-xl mb-4 border border-border/50">
              <div className="space-y-1">
                <div className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Primary Contact</div>
                <div className="font-medium">{trial.contact.split(' - ')[0]}</div>
              </div>
              <div className="space-y-1">
                <div className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Email</div>
                <div className="font-medium text-primary break-all hover:underline cursor-pointer">{trial.contact.split(' - ')[1]}</div>
              </div>
            </div>
            <Button className="w-full font-bold h-11 rounded-xl shadow-sm" onClick={handleConnect} disabled={isConnected}>
              {isConnected ? 'Request Sent' : 'Contact Trial Team'}
            </Button>
          </Card >

          {/* Related Trials */}
          < Card className="p-6 border-border/60 shadow-sm" >
            <h3 className="font-bold mb-4 text-lg">Related Trials</h3>
            <div className="space-y-3">
              {trialService.getAll()
                .filter(t => t.id !== trial.id && t.disease === trial.disease)
                .slice(0, 2)
                .map(relatedTrial => (
                  <Link
                    key={relatedTrial.id}
                    to={`/trials/${relatedTrial.id}`}
                    className="group block p-4 bg-card border rounded-xl hover:shadow-md hover:border-primary/30 transition-all"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <Badge variant="outline" className="text-[10px] font-semibold text-muted-foreground bg-muted/50 uppercase tracking-wide">{relatedTrial.phase}</Badge>
                      <ChevronRight size={16} className="text-muted-foreground group-hover:text-primary transition-colors group-hover:translate-x-1 duration-200" />
                    </div>
                    <div className="font-bold text-sm line-clamp-2 leading-snug group-hover:text-primary transition-colors">{relatedTrial.title}</div>
                  </Link>
                ))}
            </div>
          </Card >
        </div >
      </div >
    </div >
  );
}