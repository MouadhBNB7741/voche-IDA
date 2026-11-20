import { useState, useRef, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import ReactMarkdown from 'react-markdown';
import { toast } from 'sonner';
import { Card } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import {
  Send,
  Bot,
  User,
  MessageCircle,
  Lightbulb,
  HelpCircle,
  Search,
  BookOpen,
  Calendar,
  Trash2,
  MessageSquarePlus,
  History,
  ThumbsUp,
  ThumbsDown,
  ShieldAlert,
  FlaskConical,
} from 'lucide-react';
import { PageHeader } from '../components/ui/PageHeader';
import { useAuthContext } from '../contexts/AuthContext';
import { aiService } from '../services/aiService';
import type { ChatMessage, ConversationDetail } from '../services/aiService';
import { formatMessageDate } from '../utils/date';

const WELCOME_MESSAGE: ChatMessage = {
  id: 'welcome',
  sender_role: 'assistant',
  content: "Hello! I'm your VOCHE Platform assistant. I'm here to help you navigate clinical trials, community resources, and answer questions about participating in health research. How can I help you today?",
  citations: [],
  safety_flagged: false,
  created_at: new Date().toISOString(),
};

const SIGN_IN_MESSAGE = 'Sign in to your Voche account to chat with the AI Assistant.';

const quickQuestions = [
  { icon: Search, text: "What trials are available for HIV in Kenya?" },
  { icon: MessageCircle, text: "How can I join a forum?" },
  { icon: BookOpen, text: "Explain informed consent in simple terms" },
  { icon: Calendar, text: "Show me upcoming webinars" },
];

const suggestions = [
  "Find clinical trials in my area",
  "Help me understand eligibility criteria",
  "What are my rights as a participant?",
  "Connect me with relevant community discussions",
  "Explain the clinical trial process",
  "Find educational resources about my condition",
];

const conversationKey = (id: string | null) => ['ai', 'conversation', id];

export default function Assistant() {
  const { isAuthenticated, openAuthModal } = useAuthContext();
  const queryClient = useQueryClient();

  const [activeId, setActiveId] = useState<string | null>(null);
  const [inputMessage, setInputMessage] = useState('');
  const [pendingText, setPendingText] = useState<string | null>(null);
  const [ratings, setRatings] = useState<Record<string, 1 | -1>>({});
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  const { data: conversations = [] } = useQuery({
    queryKey: ['ai', 'conversations'],
    queryFn: aiService.listConversations,
    enabled: isAuthenticated,
    staleTime: 30 * 1000,
  });

  const { data: activeConversation } = useQuery({
    queryKey: conversationKey(activeId),
    queryFn: () => aiService.getConversation(activeId as string),
    enabled: isAuthenticated && !!activeId,
  });

  const sendMutation = useMutation({
    mutationFn: async (text: string) => {
      const created = activeId ? null : await aiService.createConversation();
      const conversationId = activeId ?? created!.id;
      const result = await aiService.sendMessage(conversationId, text);
      return { conversationId, created, result };
    },
    onSuccess: ({ conversationId, created, result }) => {
      // Show the new exchange straight away instead of waiting for a refetch.
      queryClient.setQueryData<ConversationDetail | undefined>(conversationKey(conversationId), (old) => {
        const base = old ?? (created ? { ...created, messages: [] } : undefined);
        return base && { ...base, messages: [...base.messages, result.user_message, result.assistant_message] };
      });
      if (conversationId !== activeId) setActiveId(conversationId);
      queryClient.invalidateQueries({ queryKey: ['ai', 'conversations'] });
    },
    onSettled: () => setPendingText(null),
  });

  const deleteMutation = useMutation({
    mutationFn: aiService.deleteConversation,
    onSuccess: (_, deletedId) => {
      if (deletedId === activeId) setActiveId(null);
      queryClient.removeQueries({ queryKey: conversationKey(deletedId) });
      queryClient.invalidateQueries({ queryKey: ['ai', 'conversations'] });
      toast.success('Conversation deleted');
    },
  });

  const feedbackMutation = useMutation({
    mutationFn: ({ messageId, rating }: { messageId: string; rating: 1 | -1 }) =>
      aiService.sendFeedback(messageId, rating),
    onSuccess: (_, { messageId, rating }) => {
      setRatings((prev) => ({ ...prev, [messageId]: rating }));
      toast.success('Thanks for your feedback');
    },
  });

  const isTyping = sendMutation.isPending;

  const messages: ChatMessage[] = [WELCOME_MESSAGE, ...(activeConversation?.messages ?? [])];
  if (pendingText) {
    messages.push({ ...WELCOME_MESSAGE, id: 'pending', sender_role: 'user', content: pendingText, created_at: new Date().toISOString() });
  }

  const scrollToBottom = useCallback(() => {
    scrollContainerRef.current?.scrollTo({ top: scrollContainerRef.current.scrollHeight, behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages.length, isTyping, scrollToBottom]);

  const sendMessage = (text?: string) => {
    const content = (text ?? inputMessage).trim();
    if (!content || isTyping) return;
    if (!isAuthenticated) {
      openAuthModal(SIGN_IN_MESSAGE);
      return;
    }
    setInputMessage('');
    setPendingText(content);
    sendMutation.mutate(content);
  };

  const startNewChat = () => {
    if (!isTyping) setActiveId(null);
  };

  return (
    <div className="container mx-auto p-4 md:p-8 max-w-5xl animate-in fade-in duration-500">
      <PageHeader
        title="VOCHE AI Assistant"
        description="Your intelligent companion for navigating health research and clinical trials."
        variant="green"
        action={
          <div className="hidden md:flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={startNewChat}
              disabled={isTyping}
              className="text-white/90 hover:bg-white/15 hover:text-white cursor-pointer"
            >
              <MessageSquarePlus size={16} className="mr-1.5" />
              New chat
            </Button>

            <div className="w-14 h-14 bg-white/20 rounded-full flex items-center justify-center backdrop-blur-md shadow-lg">
              <Bot size={28} className="text-white" />
            </div>
          </div>
        }
      />

      <div className="grid lg:grid-cols-4 gap-6">
        {/* Main Chat */}
        <div className="lg:col-span-3 space-y-4">
          {/* Clinical safety disclaimer */}
          <div
            role="note"
            className="flex items-start gap-3 p-4 rounded-xl border border-amber-300 bg-amber-50 text-amber-900 dark:border-amber-700/60 dark:bg-amber-950/40 dark:text-amber-100 text-sm"
          >
            <ShieldAlert size={18} className="shrink-0 mt-0.5" aria-hidden="true" />
            <p>
              The VOCHE Assistant gives general information, <strong>not medical advice</strong>. Always talk to a
              healthcare provider about your own health. In an emergency, call your local emergency number.
            </p>
          </div>

          {/* Messages Container */}
          <Card className="h-[calc(100vh-14rem)] min-h-[500px] flex flex-col shadow-lg border-border/60">
            <div ref={scrollContainerRef} className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar">
              {messages.map((message) => {
                const isUser = message.sender_role === 'user';
                const canRate = !isUser && message.id !== 'welcome';
                const rating = ratings[message.id];

                return (
                  <div key={message.id} className={`flex gap-4 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
                    <div
                      className={`w-10 h-10 rounded-full flex items-center justify-center shadow-sm shrink-0 ${
                        isUser
                          ? 'bg-primary text-primary-foreground'
                          : 'bg-secondary-color dark:bg-secondary-color text-white'
                      }`}
                    >
                      {isUser ? <User size={18} /> : <Bot size={18} />}
                    </div>
                    <div className={`max-w-[85%] ${isUser ? 'text-right' : 'text-left'}`}>
                      {message.safety_flagged && (
                        <p className="flex items-center gap-1.5 text-xs font-semibold text-red-600 dark:text-red-400 mb-1.5 px-1">
                          <ShieldAlert size={14} aria-hidden="true" /> Safety notice
                        </p>
                      )}
                      <div
                        className={`p-4 rounded-2xl shadow-md inline-block text-left ${
                          isUser
                            ? 'bg-primary-color !text-white rounded-tr-none border border-primary-color/50'
                            : message.safety_flagged
                              ? 'bg-red-700 !text-white border border-red-700 rounded-tl-none'
                              : 'bg-slate-600 dark:bg-secondary-color !text-white border border-slate-600 dark:border-secondary-color/50 rounded-tl-none'
                        }`}
                      >
                        <div className={`text-sm leading-relaxed ${isUser ? 'font-medium' : ''}`}>
                          <ReactMarkdown
                            components={{
                              ul: ({ node, ...props }) => <ul className="list-disc ml-5 space-y-1 mb-2" {...props} />,
                              ol: ({ node, ...props }) => <ol className="list-decimal ml-5 space-y-1 mb-2" {...props} />,
                              li: ({ node, ...props }) => <li className="mb-1" {...props} />,
                              p: ({ node, ...props }) => <p className="mb-2 last:mb-0 whitespace-pre-wrap" {...props} />,
                              strong: ({ node, ...props }) => <strong className="font-semibold" {...props} />,
                              a: ({ node, ...props }) => <a className="text-blue-500 hover:underline" {...props} />,
                            }}
                          >
                            {message.content}
                          </ReactMarkdown>
                        </div>
                      </div>

                      {/* Citation cards */}
                      {message.citations.length > 0 && (
                        <div className="flex flex-wrap gap-2 mt-2">
                          {message.citations.map((citation) => {
                            const Icon = citation.type === 'trial' ? FlaskConical : BookOpen;
                            return (
                              <Link
                                key={`${citation.type}-${citation.id}`}
                                to={citation.type === 'trial' ? `/trials/${citation.id}` : `/resources/${citation.id}`}
                                className="flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-medium bg-background/50 border border-border/40 shadow-sm hover:shadow-md hover:bg-primary-color/10 hover:text-primary-color hover:border-primary-color/30 transition-all duration-300"
                              >
                                <Icon size={14} className="text-primary-color shrink-0" aria-hidden="true" />
                                <span className="sr-only">{citation.type === 'trial' ? 'Clinical trial:' : 'Resource:'}</span>
                                <span className="line-clamp-1">{citation.title}</span>
                              </Link>
                            );
                          })}
                        </div>
                      )}

                      <div className={`flex items-center gap-1 mt-1.5 px-1 ${isUser ? 'justify-end' : ''}`}>
                        <p className="text-[10px] text-muted-foreground font-medium">
                          {formatMessageDate(message.created_at)}
                        </p>
                        {canRate && (
                          <>
                            <Button
                              variant="ghost"
                              size="icon"
                              aria-label="Helpful answer"
                              aria-pressed={rating === 1}
                              disabled={feedbackMutation.isPending}
                              onClick={() => feedbackMutation.mutate({ messageId: message.id, rating: 1 })}
                              className={`h-7 w-7 ml-2 cursor-pointer ${rating === 1 ? 'text-primary-color' : 'text-muted-foreground'}`}
                            >
                              <ThumbsUp size={14} />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              aria-label="Unhelpful answer"
                              aria-pressed={rating === -1}
                              disabled={feedbackMutation.isPending}
                              onClick={() => feedbackMutation.mutate({ messageId: message.id, rating: -1 })}
                              className={`h-7 w-7 cursor-pointer ${rating === -1 ? 'text-red-500' : 'text-muted-foreground'}`}
                            >
                              <ThumbsDown size={14} />
                            </Button>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}

              {isTyping && (
                <div className="flex gap-4">
                  <div className="w-10 h-10 bg-secondary-color text-secondary-white rounded-full flex items-center justify-center shrink-0">
                    <Bot size={18} />
                  </div>
                  <div className="bg-card text-card-foreground border border-border shadow-md p-4 rounded-2xl rounded-tl-none">
                    <div className="flex gap-1.5 h-6 items-center">
                      <div className="w-2.5 h-2.5 bg-slate-400 dark:bg-slate-500 rounded-full animate-bounce"></div>
                      <div className="w-2.5 h-2.5 bg-slate-400 dark:bg-slate-500 rounded-full animate-bounce" style={{ animationDelay: '0.15s' }}></div>
                      <div className="w-2.5 h-2.5 bg-slate-400 dark:bg-slate-500 rounded-full animate-bounce" style={{ animationDelay: '0.3s' }}></div>
                    </div>
                  </div>
                </div>
              )}
              <div className="h-2 w-full" />
            </div>

            {/* Input */}
            <div className="p-4 bg-muted/20 border-t">
              <div className="flex gap-3">
                <Input
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  placeholder="Ask about clinical trials, resources, or your rights..."
                  maxLength={4000}
                  aria-label="Ask the VOCHE AI Assistant a question"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      sendMessage();
                    }
                  }}
                  disabled={isTyping}
                  className="flex-1 h-12 shadow-sm bg-background border-input"
                />

                <Button
                  onClick={() => sendMessage()}
                  disabled={!inputMessage.trim() || isTyping}
                  size="icon"
                  aria-label="Send message"
                  className="h-12 w-12 shadow-md hover:scale-105 transition-transform bg-primary-color cursor-pointer text-white"
                >
                  <Send size={18} />
                </Button>
              </div>
            </div>
          </Card>

          {/* Quick Questions */}
          <div className="grid md:grid-cols-2 gap-3">
            {quickQuestions.map((q, i) => {
              const Icon = q.icon;

              return (
                <Button
                  key={i}
                  variant="outline"
                  className="group h-auto p-4 text-left justify-start whitespace-normal bg-background/50 border border-border/40 shadow-sm hover:shadow-md hover:translate-x-1 transition-all duration-300 cursor-pointer rounded-xl"
                  onClick={() => sendMessage(q.text)}
                  disabled={isTyping}
                >
                  <div className="bg-primary-color/10 p-2 rounded-lg mr-3 transition-colors">
                    <Icon size={16} className="text-primary-color" />
                  </div>
                  <span className="text-sm font-medium transition-colors">{q.text}</span>
                </Button>
              );
            })}
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Conversation History */}
          <Card className="p-5 shadow-lg bg-gradient-to-br from-blue-50 to-blue-100 dark:from-slate-800 dark:to-slate-900 border border-blue-200 dark:border-slate-700 text-white/90 backdrop-blur-md hover:shadow-xl transition-all duration-300 rounded-2xl">
            <h3 className="font-bold text-sm mb-4 flex items-center gap-2 text-foreground pb-3 border-b border-border/50">
              <History size={18} className="text-primary-color" />
              <span className="text-blue-900 dark:text-blue-100">Your Conversations</span>
            </h3>

            {!isAuthenticated ? (
              <Button
                variant="ghost"
                size="sm"
                className="w-full justify-start text-xs h-auto py-3 px-4 whitespace-normal text-left bg-background/50 border border-border/40 shadow-sm hover:shadow-md hover:bg-primary-color/10 hover:text-primary-color hover:border-primary-color/30 transition-all duration-300 cursor-pointer rounded-xl"
                onClick={() => openAuthModal(SIGN_IN_MESSAGE)}
              >
                <span className="font-medium text-blue-900 dark:text-slate-200">Sign in to save and revisit your chats.</span>
              </Button>
            ) : (
              <div className="space-y-2.5">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={startNewChat}
                  disabled={isTyping}
                  className="w-full justify-start text-xs h-auto py-3 px-4 bg-background/50 border border-border/40 shadow-sm hover:shadow-md hover:bg-primary-color/10 dark:hover:bg-primary-color hover:text-primary-color dark:hover:text-white hover:border-primary-color/30 transition-all duration-300 cursor-pointer rounded-xl"
                >
                  <MessageSquarePlus size={14} className="mr-2 text-primary-color" />
                  <span className="font-medium text-blue-900 dark:text-slate-200">New chat</span>
                </Button>

                {conversations.length === 0 && (
                  <p className="text-xs text-blue-800 dark:text-slate-300 px-1">No saved conversations yet.</p>
                )}

                <ul className="space-y-2 max-h-72 overflow-y-auto custom-scrollbar">
                  {conversations.map((conversation) => {
                    const isActive = conversation.id === activeId;
                    return (
                      <li
                        key={conversation.id}
                        className={`group flex items-center gap-1 rounded-xl border shadow-sm transition-all duration-300 ${
                          isActive
                            ? 'bg-primary-color/10 border-primary-color/40'
                            : 'bg-background/50 border-border/40 hover:shadow-md hover:border-primary-color/30'
                        }`}
                      >
                        <button
                          type="button"
                          onClick={() => !isTyping && setActiveId(conversation.id)}
                          aria-current={isActive ? 'true' : undefined}
                          className="flex-1 min-w-0 text-left py-2.5 pl-3 cursor-pointer"
                        >
                          <span className={`block text-xs font-medium line-clamp-1 ${isActive ? 'text-primary-color' : 'text-blue-900 dark:text-slate-200'}`}>
                            {conversation.title || 'New conversation'}
                          </span>
                          <span className="block text-[10px] text-muted-foreground">
                            {formatMessageDate(conversation.updated_at)}
                          </span>
                        </button>
                        <Button
                          variant="ghost"
                          size="icon"
                          aria-label={`Delete conversation: ${conversation.title || 'New conversation'}`}
                          disabled={deleteMutation.isPending}
                          onClick={() => deleteMutation.mutate(conversation.id)}
                          className="h-8 w-8 mr-1 shrink-0 text-muted-foreground hover:text-red-500 cursor-pointer"
                        >
                          <Trash2 size={14} />
                        </Button>
                      </li>
                    );
                  })}
                </ul>
              </div>
            )}
          </Card>

          {/* Assistant Capabilities */}
          <Card className="p-5 shadow-lg bg-gradient-to-br from-blue-50 to-blue-100 dark:from-slate-800 dark:to-slate-900 border border-blue-200 dark:border-slate-700 text-white/90 backdrop-blur-md hover:shadow-xl transition-all duration-300 rounded-2xl">
            <h3 className="font-bold text-sm mb-4 flex items-center gap-2 text-primary-color pb-3 border-b border-border/50">
              <HelpCircle size={18} className="text-primary-color/80"/>
              I Can Help With
            </h3>

            <ul className="space-y-3 text-sm">
              <li className="group flex items-start gap-3 p-3 rounded-xl bg-background/50 border border-border/40 shadow-sm hover:shadow-md hover:bg-primary-color/5 hover:border-primary-color/30 hover:scale-[1.02] transition-all duration-300">
                <div className="w-1.5 h-1.5 bg-primary-color rounded-full mt-2 shrink-0 group-hover:scale-125 transition-transform duration-300"></div>
                <span className="text-foreground/70 group-hover:text-primary-color dark:group-hover:text-foreground transition-colors font-medium">Finding clinical trials based on your condition and location</span>
              </li>
              <li className="group flex items-start gap-3 p-3 rounded-xl bg-background/50 border border-border/40 shadow-sm hover:shadow-md hover:bg-primary-color/5 hover:border-primary-color/30 hover:scale-[1.02] transition-all duration-300">
                <div className="w-1.5 h-1.5 bg-secondary-color rounded-full mt-2 shrink-0 group-hover:scale-125 transition-transform duration-300"></div>
                <span className="text-foreground/70 group-hover:text-primary-color dark:group-hover:text-foreground transition-colors font-medium">Explaining informed consent and patient rights</span>
              </li>
              <li className="group flex items-start gap-3 p-3 rounded-xl bg-background/50 border border-border/40 shadow-sm hover:shadow-md hover:bg-primary-color/5 hover:border-primary-color/30 hover:scale-[1.02] transition-all duration-300">
                <div className="w-1.5 h-1.5 bg-accent-color rounded-full mt-2 shrink-0 group-hover:scale-125 transition-transform duration-300"></div>
                <span className="text-foreground/70 group-hover:text-primary-color dark:group-hover:text-foreground transition-colors font-medium">Connecting you with relevant community discussions</span>
              </li>
              <li className="group flex items-start gap-3 p-3 rounded-xl bg-background/50 border border-border/40 shadow-sm hover:shadow-md hover:bg-primary-color/5 hover:border-primary-color/30 hover:scale-[1.02] transition-all duration-300">
                <div className="w-1.5 h-1.5 bg-blue-color rounded-full mt-2 shrink-0 group-hover:scale-125 transition-transform duration-300"></div>
                <span className="text-foreground/70 group-hover:text-primary-color dark:group-hover:text-foreground transition-colors font-medium">Recommending educational resources</span>
              </li>
            </ul>
          </Card>

          {/* Suggested Topics */}
          <Card className="p-5 shadow-lg bg-gradient-to-br from-blue-50 to-blue-100 dark:from-slate-800 dark:to-slate-900 border border-blue-200 dark:border-slate-700 text-white/90 backdrop-blur-md hover:shadow-xl transition-all duration-300 rounded-2xl">
            <h3 className="font-bold text-sm mb-4 flex items-center gap-2 text-foreground pb-3 border-b border-border/50">
              <MessageCircle size={18} className="text-primary-color" />
              Suggested Topics
            </h3>
            <div className="space-y-2.5">
              {suggestions.map((suggestion, index) => (
                <Button
                  key={index}
                  variant="ghost"
                  size="sm"
                  className="w-full justify-start text-xs h-auto py-3 px-4 whitespace-normal text-left bg-background/50 border border-border/40 shadow-sm hover:shadow-md hover:bg-primary-color/10 dark:hover:bg-primary-color hover:text-primary-color dark:hover:text-white hover:border-primary-color/30 hover:translate-x-1.5 transition-all duration-300 cursor-pointer rounded-xl"
                  onClick={() => sendMessage(suggestion)}
                  disabled={isTyping}
                >
                  <span className="line-clamp-2 font-medium">{suggestion}</span>
                </Button>
              ))}
            </div>
          </Card>

          {/* Tips */}
          <div className="p-5 rounded-xl bg-gradient-to-br from-blue-50 to-blue-100 dark:from-slate-800 dark:to-slate-900 border border-blue-200 dark:border-slate-700 shadow-md">
            <h3 className="font-semibold mb-3 text-blue-900 dark:text-blue-100 text-sm flex items-center gap-2">
              <Lightbulb size={16} className="text-yellow-500" /> Tips for Better Help
            </h3>
            <ul className="text-xs space-y-2 text-blue-800 dark:text-slate-300 font-medium">
              <li className="flex items-start gap-2"><span className="text-blue-500 mt-0.5">•</span> Be specific about your location and condition</li>
              <li className="flex items-start gap-2"><span className="text-blue-500 mt-0.5">•</span> Ask follow-up questions for clarification</li>
              <li className="flex items-start gap-2"><span className="text-blue-500 mt-0.5">•</span> Use "show me" or "find" for actionable requests</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
