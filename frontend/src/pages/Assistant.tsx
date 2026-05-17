import { useState, useRef, useEffect, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
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
  Trash2
} from 'lucide-react';
import { PageHeader } from '../components/ui/PageHeader';
import { aiService } from '../services/aiService';
import type { ChatMessage } from '../services/aiService';
import { formatMessageDate } from '../utils/date';

interface Message {
  id: string;
  content: string;
  sender: "user" | "assistant";
  timestamp: number;
}

const STORAGE_KEY = "voche-assistant-history-v1";

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

export default function Assistant() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      content: "Hello! I'm your VOCHE Platform assistant. I'm here to help you navigate clinical trials, community resources, and answer questions about participating in health research. How can I help you today?",
      sender: 'assistant',
      timestamp: Date.now(),
    }
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    if (scrollContainerRef.current) {
      scrollContainerRef.current.scrollTo({
        top: scrollContainerRef.current.scrollHeight,
        behavior: 'smooth'
      });
    }
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;

    try {
      const raw = localStorage.getItem(STORAGE_KEY);

      if (raw) {
        const parsed = JSON.parse(raw) as Message[];

        if (Array.isArray(parsed) && parsed.length > 0) {
          setMessages(parsed);
        }
      }
    } catch {
      // ignore invalid local storage data
    }
  }, []);

  // chat history save
  useEffect(() => {
    if (typeof window === "undefined") return;

    try {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify(messages.slice(-40))
      );
    } catch {
      // ignore storage failures
    }
  }, [messages]);

  // scroll to bottom
  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping, scrollToBottom]);

  const sendMessage = useCallback(
    async (text?: string) => {
      const content = (text ?? inputMessage)
        .replace(/[<>]/g, "")
        .trim();

      if (!content || isTyping) return;

      // Add user message
      const userMessage: Message = {
        id: Date.now().toString(),
        content: content,
        sender: 'user',
        timestamp: Date.now(),
      };

      const newMessages = [...messages, userMessage];
      setMessages(newMessages);
      setInputMessage('');
      setIsTyping(true);

      try {
        // Build conversation history for context
        const chatHistory: ChatMessage[] = newMessages.map(msg => ({
          role: msg.sender === 'user' ? 'user' : 'model',
          parts: [{ text: msg.content }]
        }));

        const responseText = await aiService.generateChatResponse(chatHistory);

        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          content: responseText,
          sender: 'assistant',
          timestamp: Date.now(),
        };
        setMessages(prev => [...prev, assistantMessage]);
      } catch (error) {
        console.error(error);
        const errorMessage: Message = {
          id: (Date.now() + 1).toString(),
          content: "Sorry, I encountered an error while processing your request. Please make sure the API key is set up correctly in the .env file.",
          sender: 'assistant',
          timestamp: Date.now(),
        };
        setMessages(prev => [...prev, errorMessage]);
      } finally {
        setIsTyping(false);
      }
    },
    [inputMessage, messages, isTyping]
  );

  const clearChat = () => {
    setMessages([
      {
        id: '1',
        content: "Hello! I'm your VOCHE Platform assistant. I'm here to help you navigate clinical trials, community resources, and answer questions about participating in health research. How can I help you today?",
        sender: 'assistant',
        timestamp: Date.now(),
      }
    ]);
    if (typeof window !== "undefined") {
      localStorage.removeItem(STORAGE_KEY);
    }
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
              onClick={clearChat}
              className="text-white/90 hover:bg-white/15 hover:text-white"
            >
              <Trash2
                size={16}
                className="mr-1.5"
              />
              New chat
            </Button>

            <div className="w-14 h-14 bg-white/20 rounded-full flex items-center justify-center backdrop-blur-md shadow-lg">
              <Bot
                size={28}
                className="text-white"
              />
            </div>
          </div>
        }
      />

      <div className="grid lg:grid-cols-4 gap-6">
        {/* Main Chat */}
        <div className="lg:col-span-3 space-y-4">
          {/* Messages Container */}
          <Card className="h-[calc(100vh-14rem)] min-h-[500px] flex flex-col shadow-lg border-border/60">
            <div ref={scrollContainerRef} className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex gap-4 ${
                    message.sender === "user"
                      ? "flex-row-reverse"
                      : "flex-row"
                  }`}
                >
                  <div
                    className={`w-10 h-10 rounded-full flex items-center justify-center shadow-sm shrink-0 ${
                      message.sender === "user"
                        ? "bg-primary text-primary-foreground"
                        : "bg-emerald-600 text-black"
                    }`}
                  >
                    {message.sender === "user" ? (
                      <User size={18} />
                    ) : (
                      <Bot size={18} />
                    )}
                  </div>
                  <div className={`max-w-[85%] ${message.sender === 'user' ? 'text-right' : 'text-left'}`}>
                    <div className={`p-4 rounded-2xl shadow-md inline-block text-left ${message.sender === 'user'
                      ? 'bg-primary-color !text-white rounded-tr-none border border-primary-color/50'
                      : 'bg-slate-600 dark:bg-secondary-color !text-white border border-slate-600 dark:border-secondary-color/50 rounded-tl-none'
                      }`}>
                      <div className={`text-sm leading-relaxed ${message.sender === 'user' ? 'font-medium' : ''}`}>
                        <ReactMarkdown
                          components={{
                            ul: ({node, ...props}) => <ul className="list-disc ml-5 space-y-1 mb-2" {...props} />,
                            ol: ({node, ...props}) => <ol className="list-decimal ml-5 space-y-1 mb-2" {...props} />,
                            li: ({node, ...props}) => <li className="mb-1" {...props} />,
                            p: ({node, ...props}) => <p className="mb-2 last:mb-0 whitespace-pre-wrap" {...props} />,
                            strong: ({node, ...props}) => <strong className="font-semibold" {...props} />,
                            a: ({node, ...props}) => <a className="text-blue-500 hover:underline" {...props} />
                          }}
                        >
                          {message.content}
                        </ReactMarkdown>
                      </div>
                    </div>

                    <p className="text-[10px] text-muted-foreground mt-1.5 font-medium px-1">
                      {formatMessageDate(message.timestamp)}
                    </p>
                  </div>
                </div>
              ))}

              {isTyping && (
                <div className="flex gap-4">
                  <div className="w-10 h-10 bg-secondary-color text-secondary-foreground rounded-full flex items-center justify-center shrink-0">
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
              <div ref={messagesEndRef} className="h-2 w-full" />
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
                    if (e.key === "Enter" && !e.shiftKey) {
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
                  className="h-12 w-12 shadow-md hover:scale-105 transition-transform bg-primary-color cursor-pointer text-white"
                >
                  <Send
                    size={18}
                  />
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
                  className="group h-auto p-4 text-left justify-start bg-background/50 border border-border/40 shadow-sm hover:shadow-md hover:translate-x-1 transition-all duration-300 cursor-pointer rounded-xl"
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