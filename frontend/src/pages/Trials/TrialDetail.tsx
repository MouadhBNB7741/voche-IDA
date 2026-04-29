import { useState, useEffect } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { Card } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Badge } from "../../components/ui/badge";
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
  FlaskConical,
  ClipboardList,
} from "lucide-react";
import { trialService } from "../../services/trialService";
import { useTrialById } from "../../hooks/useTrialById";
import { useTrials } from "../../hooks/useTrials";
import {
  useSurveys,
  useSurveyById,
  useSubmitSurvey,
  useCompletedSurveys,
} from "../../hooks/useSurvey";

import { useSaveTrial } from "../../hooks/useSaveTrial";
import { toast } from "sonner";
import { PageHeader } from "../../components/ui/PageHeader";

export default function TrialDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const { data: trial, isLoading, error } = useTrialById(id);
  const { data: allTrials = [] } = useTrials();

  const { toggleSave, isSaved: getIsSaved } = useSaveTrial();
  const isSaved = getIsSaved(id ?? "");

  const { data: surveys = [] } = useSurveys();
  const { data: completedSurveys = [] } = useCompletedSurveys();

  // Find the survey linked to this trial (if any)
  const trialSurvey =
    surveys.find((s) => s.trial_id === id) ?? surveys[0] ?? null;
  const { data: surveyDetail, isLoading: isSurveyLoading } = useSurveyById(
    trialSurvey?.survey_id,
  );
  const submitSurvey = useSubmitSurvey();

  const [isConnected, setIsConnected] = useState(false);
  const [showQuiz, setShowQuiz] = useState(false);
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string | number>>({});
  const [quizComplete, setQuizComplete] = useState(false);
  const [isEligible, setIsEligible] = useState<boolean | null>(null);

  useEffect(() => {
    if (id) setIsConnected(trialService.isTrialConnected(id));
  }, [id]);

  const handleConnect = () => {
    if (id) {
      if (isConnected) {
        toast.info("Request Already Pending", {
          description: "You have already requested to connect with this trial.",
        });
        return;
      }
      trialService.connectTrial(id);
      setIsConnected(true);
      toast.success("Connection Request Sent", {
        description:
          "A trial coordinator will review your profile and contact you shortly.",
      });
    }
  };

  const questions = surveyDetail?.questions ?? [];

  const handleAnswer = (questionId: string, answer: string | number) => {
    const updatedAnswers = { ...answers, [questionId]: answer };
    setAnswers(updatedAnswers);

    if (currentQuestion < questions.length - 1) {
      setCurrentQuestion((prev) => prev + 1);
    } else {
      const yesCount = Object.values(updatedAnswers).filter(
        (a) => a === "yes" || a === "Yes" || a === "No medications",
      ).length;
      setIsEligible(yesCount >= Math.ceil(questions.length / 2));
      setQuizComplete(true);
    }
  };

  const handleSubmitSurvey = async () => {
    if (!surveyDetail) return;

    const payload = {
      consent_given: true,
      anonymous: false,
      responses: Object.entries(answers).map(([question_id, answer]) => ({
        question_id,
        answer,
      })),
    };

    await submitSurvey.mutateAsync({
      surveyId: surveyDetail.survey_id,
      payload,
    });
  };

  const resetQuiz = () => {
    setCurrentQuestion(0);
    setAnswers({});
    setQuizComplete(false);
    setShowQuiz(false);
    setIsEligible(null);
  };

  const alreadyCompleted = completedSurveys.some(
    (c) => c.survey_id === trialSurvey?.survey_id,
  );

  if (isLoading) {
    return (
      <div className="container mx-auto p-4 md:p-8 space-y-6">
        <div className="h-9 w-32 bg-muted rounded animate-pulse" />
        <div className="h-40 bg-muted rounded-2xl animate-pulse" />
        <div className="grid lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 space-y-6">
            <div className="h-64 bg-muted rounded-2xl animate-pulse" />
            <div className="h-48 bg-muted rounded-2xl animate-pulse" />
            <div className="h-56 bg-muted rounded-2xl animate-pulse" />
          </div>
          <div className="space-y-6">
            <div className="h-48 bg-muted rounded-2xl animate-pulse" />
            <div className="h-40 bg-muted rounded-2xl animate-pulse" />
          </div>
        </div>
      </div>
    );
  }

  if (error || !trial) {
    return (
      <div className="container mx-auto p-4 md:p-8">
        <Button
          variant="ghost"
          onClick={() => navigate("/trials")}
          className="gap-2 pl-0 hover:bg-transparent hover:text-primary-color transition-colors mb-6"
        >
          <ArrowLeft size={16} />
          Back to Trials
        </Button>
        <Card className="p-16 text-center border-dashed">
          <Activity
            className="mx-auto mb-4 text-muted-foreground opacity-50"
            size={64}
          />
          <h2 className="text-xl font-semibold mb-2">Trial not found</h2>
          <p className="text-muted-foreground mb-6">
            The trial you're looking for doesn't exist or may have been removed.
          </p>
          <Button onClick={() => navigate("/trials")}>Browse All Trials</Button>
        </Card>
      </div>
    );
  }

  const relatedTrials = allTrials
    .filter((t) => t.id !== trial.id && t.disease === trial.disease)
    .slice(0, 2);

  return (
    <div className="container mx-auto p-4 md:p-8 space-y-6 animate-in fade-in duration-500">
      <div>
        <Button
          variant="ghost"
          onClick={() => navigate("/trials")}
          className="gap-2 pl-0 hover:bg-transparent hover:text-primary-color transition-colors"
        >
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
              className={`font-bold shadow-lg h-12 px-6 rounded-xl transition-all hover:scale-105 ${
                isConnected
                  ? "text-success-color hover:text-success-color/90 text-success-foreground cursor-default"
                  : "bg-white text-primary-color hover:bg-white/90"
              }`}
              onClick={handleConnect}
              disabled={isConnected}
            >
              {isConnected ? (
                <>
                  <CheckCircle2 size={18} className="mr-2" /> Request Pending
                </>
              ) : (
                "Connect with Trial"
              )}
            </Button>
            <Button
              variant="outline"
              className={`h-12 px-4 rounded-xl border transition-colors ${
                isSaved
                  ? "bg-white/20 border-white/40 text-white hover:bg-white/30"
                  : "bg-transparent border-white/30 text-white hover:bg-white/10"
              }`}
              onClick={() => toggleSave(id!)}
            >
              <Heart
                size={20}
                className={`mr-2 transition-transform duration-300 ${isSaved ? "fill-red-500 text-red-500 scale-110" : ""}`}
              />
              {isSaved ? "Saved" : "Save"}
            </Button>
            {localStorage.getItem("voce_user") &&
              JSON.parse(localStorage.getItem("voce_user")!)?.role ===
                "hcp" && (
                <Button
                  variant="outline"
                  className="h-12 px-4 rounded-xl border border-white/30 text-white hover:bg-white/10"
                  onClick={() =>
                    toast.success("Protocol Downloaded", {
                      description: "PDF has been saved to your device.",
                    })
                  }
                >
                  <ShieldCheck size={20} className="mr-2" />
                  Protocol
                </Button>
              )}
          </div>
        }
      />

      <div className="grid lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-8">
          <Card className="p-6 md:p-8 border-border/60 shadow-sm">
            <h2 className="text-xl font-bold mb-6 flex items-center gap-2">
              <Activity size={20} className="text-primary-color" />
              Overview
            </h2>
            <div className="grid sm:grid-cols-2 gap-6">
              <div className="flex items-start gap-4 p-4 bg-muted/30 rounded-xl border border-transparent hover:border-primary/20 transition-colors">
                <Building className="text-primary-color mt-1" size={20} />
                <div>
                  <div className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-1">
                    Sponsor
                  </div>
                  <div className="font-medium">{trial.sponsor}</div>
                </div>
              </div>
              <div className="flex items-start gap-4 p-4 bg-muted/30 rounded-xl border border-transparent hover:border-primary/20 transition-colors">
                <MapPin className="text-primary-color mt-1" size={20} />
                <div>
                  <div className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-1">
                    Location
                  </div>
                  <div className="font-medium">{trial.location}</div>
                </div>
              </div>
              <div className="flex items-start gap-4 p-4 bg-muted/30 rounded-xl border border-transparent hover:border-primary/20 transition-colors">
                <Calendar className="text-primary-color mt-1" size={20} />
                <div>
                  <div className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-1">
                    Start Date
                  </div>
                  <div className="font-medium">
                    {new Date(trial.startDate).toLocaleDateString()}
                  </div>
                </div>
              </div>
              <div className="flex items-start gap-4 p-4 bg-muted/30 rounded-xl border border-transparent hover:border-primary/20 transition-colors">
                <Clock className="text-primary-color mt-1" size={20} />
                <div>
                  <div className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-1">
                    Est. Completion
                  </div>
                  <div className="font-medium">
                    {new Date(trial.estimatedCompletion).toLocaleDateString()}
                  </div>
                </div>
              </div>
            </div>

            <div className="mt-8 pt-6 border-t border-dashed">
              <div className="flex justify-between text-sm mb-2 font-medium">
                <span className="text-muted-foreground">
                  Enrollment Progress
                </span>
                <span className="text-primary-color font-bold">
                  {trial.enrollment} / {trial.maxEnrollment} Participants
                </span>
              </div>
              <div className="h-3 bg-muted rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary-color rounded-full transition-all duration-1000 ease-out relative overflow-hidden"
                  style={{
                    width: `${(trial.enrollment / trial.maxEnrollment) * 100}%`,
                  }}
                >
                  <div className="absolute inset-0 bg-white/20 animate-[shimmer_2s_infinite]"></div>
                </div>
              </div>
            </div>
          </Card>

          {/* Eligibility Criteria */}
          <Card className="p-6 md:p-8 border-border/60 shadow-sm">
            <h2 className="text-xl font-bold mb-6 flex items-center gap-2">
              <ShieldCheck size={20} className="text-primary-color" />
              Eligibility Criteria
            </h2>
            <div className="space-y-4">
              {trial.eligibility.map((criteria, index) => (
                <div
                  key={index}
                  className="flex items-center gap-4 p-4 bg-muted/20 rounded-xl border border-muted hover:border-primary/20 transition-colors"
                >
                  <div className="bg-success/10 p-1.5 rounded-full shrink-0">
                    <CheckCircle2 className="text-success-color" size={18} />
                  </div>
                  <span className="font-medium text-foreground/90">
                    {criteria}
                  </span>
                </div>
              ))}
            </div>
          </Card>

          <Card className="p-6 md:p-8 border-l-4 border-l-primary shadow-lg overflow-hidden relative">
            <div className="absolute top-0 right-0 p-8 opacity-5 pointer-events-none">
              <FlaskConical size={140} />
            </div>
            <h2 className="text-xl font-bold mb-6">Eligibility Quiz</h2>

            {alreadyCompleted && !showQuiz && (
              <div className="flex items-center gap-3 p-4 bg-success/10 rounded-xl border border-success/20 mb-6">
                <CheckCircle2
                  className="text-success-color shrink-0"
                  size={20}
                />
                <div>
                  <div className="font-semibold text-sm">Already Completed</div>
                  <div className="text-xs text-muted-foreground">
                    You have previously submitted this eligibility quiz.
                  </div>
                </div>
              </div>
            )}

            {isSurveyLoading && (
              <div className="text-center py-8">
                <div className="h-6 w-48 bg-muted rounded animate-pulse mx-auto mb-3" />
                <div className="h-4 w-64 bg-muted rounded animate-pulse mx-auto" />
              </div>
            )}

            {!isSurveyLoading && !surveyDetail && (
              <div className="text-center py-8 text-muted-foreground">
                <HelpCircle className="mx-auto mb-3 opacity-40" size={32} />
                <p className="text-sm">
                  No eligibility quiz available for this trial.
                </p>
              </div>
            )}

            {!isSurveyLoading && surveyDetail && !showQuiz && !quizComplete && (
              <div className="text-center py-8">
                <div className="w-16 h-16 bg-primary-color/10 rounded-full flex items-center justify-center mx-auto mb-6 ring-4 ring-primary/5">
                  <HelpCircle className="text-primary-color" size={32} />
                </div>
                <h3 className="font-bold text-lg mb-2">{surveyDetail.title}</h3>
                <p className="text-muted-foreground mb-2 max-w-md mx-auto">
                  {surveyDetail.description ??
                    "Take a quick quiz to see if you might be a good fit for this clinical trial."}
                </p>
                <p className="text-xs text-muted-foreground mb-8">
                  {questions.length} questions
                </p>
                <Button
                  style={{
                    backgroundColor: "hsl(var(--primary))",
                    color: "white",
                  }}
                  onClick={() => setShowQuiz(true)}
                  size="lg"
                  className="shadow-md rounded-xl px-8"
                >
                  Start Eligibility Check
                </Button>
              </div>
            )}

            {showQuiz && !quizComplete && questions.length > 0 && (
              <div className="space-y-8 animate-in fade-in slide-in-from-bottom-2">
                <div className="space-y-2">
                  <div className="flex justify-between text-xs font-bold uppercase tracking-wider text-muted-foreground">
                    <span>Quiz Progress</span>
                    <span>
                      {Math.round(
                        ((currentQuestion + 1) / questions.length) * 100,
                      )}
                      %
                    </span>
                  </div>
                  <div className="flex gap-1.5">
                    {questions.map((_, idx) => (
                      <div
                        key={idx}
                        className={`h-2 flex-1 rounded-full transition-colors duration-300 ${idx <= currentQuestion ? "bg-primary-color" : "bg-muted"}`}
                      />
                    ))}
                  </div>
                </div>

                <div className="py-2">
                  <div className="text-sm font-bold text-primary-color mb-2 uppercase tracking-wide">
                    Question {currentQuestion + 1} of {questions.length}
                  </div>
                  <h3 className="text-2xl font-bold mb-8 leading-tight">
                    {questions[currentQuestion].text}
                  </h3>

                  <div className="space-y-3">
                    {questions[currentQuestion].type === "yes_no" && (
                      <div className="grid grid-cols-2 gap-4">
                        <Button
                          variant="outline"
                          className="h-16 text-lg font-medium hover:bg-primary-color hover:text-primary-foreground hover:border-primary transition-all rounded-xl"
                          onClick={() =>
                            handleAnswer(
                              questions[currentQuestion].question_id,
                              "yes",
                            )
                          }
                        >
                          Yes
                        </Button>
                        <Button
                          variant="outline"
                          className="h-16 text-lg font-medium hover:bg-primary-color hover:text-primary-foreground hover:border-primary transition-all rounded-xl"
                          onClick={() =>
                            handleAnswer(
                              questions[currentQuestion].question_id,
                              "no",
                            )
                          }
                        >
                          No
                        </Button>
                      </div>
                    )}

                    {questions[currentQuestion].type === "multiple_choice" && (
                      <div className="space-y-3">
                        {questions[currentQuestion].options?.map(
                          (option, idx) => (
                            <Button
                              key={option}
                              variant="outline"
                              className="w-full justify-start h-14 text-base px-6 hover:bg-primary-color hover:text-primary-foreground hover:border-primary transition-all rounded-xl"
                              onClick={() =>
                                handleAnswer(
                                  questions[currentQuestion].question_id,
                                  idx,
                                )
                              }
                            >
                              {option}
                            </Button>
                          ),
                        )}
                      </div>
                    )}

                    {questions[currentQuestion].type === "scale" && (
                      <div className="flex gap-3 justify-center flex-wrap">
                        {[1, 2, 3, 4, 5].map((n) => (
                          <Button
                            key={n}
                            variant="outline"
                            className="w-14 h-14 text-lg font-bold hover:bg-primary-color hover:text-primary-foreground rounded-xl"
                            onClick={() =>
                              handleAnswer(
                                questions[currentQuestion].question_id,
                                n,
                              )
                            }
                          >
                            {n}
                          </Button>
                        ))}
                      </div>
                    )}

                    {questions[currentQuestion].type === "text" && (
                      <div className="space-y-3">
                        <textarea
                          className="w-full p-4 rounded-xl border bg-muted/30 resize-none focus:outline-none focus:ring-2 focus:ring-primary/30"
                          rows={3}
                          placeholder="Type your answer..."
                          onKeyDown={(e) => {
                            if (e.key === "Enter" && !e.shiftKey) {
                              e.preventDefault();
                              handleAnswer(
                                questions[currentQuestion].question_id,
                                (e.target as HTMLTextAreaElement).value,
                              );
                            }
                          }}
                        />
                        <Button
                          className="w-full h-12 rounded-xl"
                          onClick={(e) => {
                            const ta = e.currentTarget
                              .previousElementSibling as HTMLTextAreaElement;
                            handleAnswer(
                              questions[currentQuestion].question_id,
                              ta.value,
                            );
                          }}
                        >
                          Next
                        </Button>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {quizComplete && (
              <div className="text-center py-8 animate-in zoom-in duration-300">
                {isEligible ? (
                  <>
                    <div className="w-20 h-20 bg-success/10 rounded-full flex items-center justify-center mx-auto mb-6 ring-4 ring-success/5">
                      <CheckCircle2 className="text-success" size={40} />
                    </div>
                    <h3 className="text-2xl font-bold text-success mb-3">
                      You May Be Eligible!
                    </h3>
                    <p className="text-muted-foreground mb-8 max-w-md mx-auto text-lg leading-relaxed">
                      Based on your answers, you appear to be a good candidate
                      for this trial.
                    </p>
                    <div className="flex flex-col sm:flex-row gap-4 justify-center">
                      <Button
                        onClick={handleSubmitSurvey}
                        size="lg"
                        className="shadow-lg h-12 px-8 rounded-xl"
                        disabled={submitSurvey.isPending}
                      >
                        {submitSurvey.isPending
                          ? "Submitting..."
                          : "Submit & Connect"}
                      </Button>
                      <Button
                        variant="outline"
                        onClick={resetQuiz}
                        className="h-12 rounded-xl"
                      >
                        Retake Quiz
                      </Button>
                    </div>
                  </>
                ) : (
                  <>
                    <div className="w-20 h-20 bg-warning/10 rounded-full flex items-center justify-center mx-auto mb-6 ring-4 ring-warning/5">
                      <XCircle className="text-warning" size={40} />
                    </div>
                    <h3 className="text-2xl font-bold text-foreground mb-3">
                      Eligibility Uncertain
                    </h3>
                    <p className="text-muted-foreground mb-8 max-w-md mx-auto leading-relaxed">
                      Based on your answers, you might not meet all criteria. We
                      still recommend submitting and consulting with a
                      healthcare provider.
                    </p>
                    <div className="flex flex-col sm:flex-row gap-4 justify-center">
                      <Button
                        onClick={handleSubmitSurvey}
                        size="lg"
                        variant="outline"
                        className="h-12 px-8 rounded-xl"
                        disabled={submitSurvey.isPending}
                      >
                        {submitSurvey.isPending
                          ? "Submitting..."
                          : "Submit Anyway"}
                      </Button>
                      <Button
                        variant="outline"
                        onClick={resetQuiz}
                        className="h-12 rounded-xl"
                      >
                        Retake Quiz
                      </Button>
                      <Button
                        variant="default"
                        asChild
                        className="h-12 rounded-xl"
                      >
                        <Link to="/trials">Browse Other Trials</Link>
                      </Button>
                    </div>
                  </>
                )}
              </div>
            )}
          </Card>

          {completedSurveys.length > 0 && (
            <Card className="p-6 md:p-8 border-border/60 shadow-sm">
              <h2 className="text-xl font-bold mb-6 flex items-center gap-2">
                <ClipboardList size={20} className="text-primary-color" />
                Completed Surveys
              </h2>
              <div className="space-y-3">
                {completedSurveys.map((completed) => (
                  <div
                    key={completed.completion_id}
                    className="flex items-center justify-between p-4 bg-muted/20 rounded-xl border hover:border-primary/20 transition-colors"
                  >
                    <div>
                      <div className="font-semibold text-sm">
                        {completed.survey_title}
                      </div>
                      <div className="text-xs text-muted-foreground mt-0.5">
                        Completed{" "}
                        {new Date(completed.completed_at).toLocaleDateString()}
                      </div>
                    </div>
                    <Badge
                      className="bg-success/10 text-success-color border-success/20"
                      variant="outline"
                    >
                      <CheckCircle2 size={12} className="mr-1" /> Done
                    </Badge>
                  </div>
                ))}
              </div>
            </Card>
          )}

          <Card className="p-6 md:p-8 border-border/60 shadow-sm">
            <h2 className="text-xl font-bold mb-6 flex items-center gap-2">
              <MapPin size={20} className="text-primary-color" />
              Trial Locations
            </h2>
            <div className="space-y-3">
              <div className="flex items-center justify-between p-5 bg-muted/20 rounded-xl border hover:border-primary/30 transition-colors">
                <div className="flex items-center gap-4">
                  <div className="bg-primary-color/10 p-2.5 rounded-full">
                    <MapPin className="text-primary-color" size={20} />
                  </div>
                  <div>
                    <div className="font-bold text-lg">{trial.location}</div>
                    <div className="text-sm text-muted-foreground">
                      Primary Research Center
                    </div>
                  </div>
                </div>
                <Badge className="bg-success text-success-foreground hover:bg-success/90 h-7 px-3">
                  Enrolling
                </Badge>
              </div>
            </div>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          <Card className="p-6 border-border/60 shadow-sm">
            <h3 className="font-bold mb-4 text-lg">Contact Information</h3>
            <div className="space-y-4 p-4 bg-muted/30 rounded-xl mb-4 border border-border/50">
              <div className="space-y-1">
                <div className="text-xs font-bold text-muted-foreground uppercase tracking-wider">
                  Primary Contact
                </div>
                <div className="font-medium">
                  {trial.contact.split(" - ")[0]}
                </div>
              </div>
              <div className="space-y-1">
                <div className="text-xs font-bold text-muted-foreground uppercase tracking-wider">
                  Email
                </div>
                <div className="font-medium text-primary-color break-all hover:underline cursor-pointer">
                  {trial.contact.split(" - ")[1]}
                </div>
              </div>
            </div>
            <Button
              className="w-full font-bold h-11 rounded-xl shadow-sm"
              onClick={handleConnect}
              disabled={isConnected}
            >
              {isConnected ? "Request Sent" : "Contact Trial Team"}
            </Button>
          </Card>

          {/* Related Trials */}
          <Card className="p-6 border-border/60 shadow-sm">
            <h3 className="font-bold mb-4 text-lg">Related Trials</h3>
            <div className="space-y-3">
              {relatedTrials.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No related trials found.
                </p>
              ) : (
                relatedTrials.map((relatedTrial) => (
                  <Link
                    key={relatedTrial.id}
                    to={`/trials/${relatedTrial.id}`}
                    className="group block p-4 bg-card border rounded-xl hover:shadow-md hover:border-primary/30 transition-all"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <Badge
                        variant="outline"
                        className="text-[10px] font-semibold text-muted-foreground bg-muted/50 uppercase tracking-wide"
                      >
                        {relatedTrial.phase}
                      </Badge>
                      <ChevronRight
                        size={16}
                        className="text-muted-foreground group-hover:text-primary-color transition-colors group-hover:translate-x-1 duration-200"
                      />
                    </div>
                    <div className="font-bold text-sm line-clamp-2 leading-snug group-hover:text-primary-color transition-colors">
                      {relatedTrial.title}
                    </div>
                  </Link>
                ))
              )}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
