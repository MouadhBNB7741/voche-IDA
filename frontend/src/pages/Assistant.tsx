import { useState, useRef, useEffect } from 'react';
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
  Calendar
} from 'lucide-react';
import { mockChatResponses } from '../data/mockData';
import { PageHeader } from '../components/ui/PageHeader';

interface Message {
  id: string;
  content: string;
  sender: 'user' | 'assistant';
  timestamp: Date;
  type?: 'suggestion' | 'normal';
}

const quickQuestions = [
  {
    icon: Search,
    text: "What trials are available for HIV in Kenya?",
    query: "trials in kenya"
  },
  {
    icon: MessageCircle,
    text: "How can I join a forum?",
    query: "join forum"
  },
  {
    icon: BookOpen,
    text: "Explain informed consent in simple terms",
    query: "informed consent"
  },
  {
    icon: Calendar,
    text: "Show me upcoming webinars",
    query: "upcoming webinars"
  }
];

const suggestions = [
  "Find clinical trials in my area",
  "Help me understand eligibility criteria",
  "What are my rights as a participant?",
  "Connect me with relevant community discussions",
  "Explain the clinical trial process",
  "Find educational resources about my condition"
];

export default function Assistant() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      content: "Hello! I'm your VOCE Platform assistant. I'm here to help you navigate clinical trials, community resources, and answer questions about participating in health research. How can I help you today?",
      sender: 'assistant',
      timestamp: new Date(),
    }
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async (messageText?: string) => {
    const messageContent = messageText || inputMessage.trim();
    if (!messageContent) return;

    // Add user message
    const userMessage: Message = {
      id: Date.now().toString(),
      content: messageContent,
      sender: 'user',
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsTyping(true);

    // Simulate AI response delay
    setTimeout(() => {
      const response = getResponse(messageContent.toLowerCase());
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: response,
        sender: 'assistant',
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, assistantMessage]);
      setIsTyping(false);
    }, 1500);
  };

  const getResponse = (query: string) => {
    // Simple keyword matching for demo
    for (const [key, response] of Object.entries(mockChatResponses)) {
      if (key !== 'default' && query.includes(key)) {
        return response;
      }
    }
    return mockChatResponses.default;
  };

  const handleQuickQuestion = (query: string) => {
    const question = quickQuestions.find(q => q.query === query);
    if (question) {
      handleSendMessage(question.text);
    }
  };

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: true
    });
  };

  return (
    <div className="container mx-auto p-4 md:p-8 max-w-5xl animate-in fade-in duration-500">
      <PageHeader
        title="VOCE AI Assistant"
        description="Your intelligent companion for navigating health research and clinical trials."
        variant="green"
        action={
          <div className="hidden md:block">
            <div className="w-16 h-16 bg-white/20 rounded-full flex items-center justify-center backdrop-blur-md shadow-lg">
              <Bot size={32} className="text-white" />
            </div>
          </div>
        }
      />

      <div className="grid lg:grid-cols-4 gap-6">
        {/* Chat Interface */}
        <div className="lg:col-span-3 space-y-4">
          {/* Messages Container */}
          <Card className="h-[600px] flex flex-col shadow-lg border-border/60">
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex gap-4 ${message.sender === 'user' ? 'flex-row-reverse' : 'flex-row'
                    }`}
                >
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center shadow-sm shrink-0 ${message.sender === 'user'
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-secondary text-secondary-foreground'
                    }`}>
                    {message.sender === 'user' ? <User size={18} /> : <Bot size={18} />}
                  </div>
                  <div className={`max-w-[85%] ${message.sender === 'user' ? 'text-right' : 'text-left'
                    }`}>
                    <div className={`p-4 rounded-2xl shadow-sm inline-block text-left ${message.sender === 'user'
                      ? 'bg-primary text-primary-foreground rounded-tr-none'
                      : 'bg-muted rounded-tl-none'
                      }`}>
                      <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
                    </div>
                    <p className="text-[10px] text-muted-foreground mt-1.5 font-medium px-1">
                      {formatTime(message.timestamp)}
                    </p>
                  </div>
                </div>
              ))}

              {isTyping && (
                <div className="flex gap-4">
                  <div className="w-10 h-10 bg-secondary text-secondary-foreground rounded-full flex items-center justify-center shrink-0">
                    <Bot size={18} />
                  </div>
                  <div className="bg-muted p-4 rounded-2xl rounded-tl-none">
                    <div className="flex gap-1.5">
                      <div className="w-2 h-2 bg-muted-foreground/50 rounded-full animate-bounce"></div>
                      <div className="w-2 h-2 bg-muted-foreground/50 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                      <div className="w-2 h-2 bg-muted-foreground/50 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div className="p-4 bg-muted/20 border-t">
              <div className="flex gap-3">
                <Input
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  placeholder="Ask about clinical trials, resources, or your rights..."
                  onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                  className="flex-1 h-12 shadow-sm bg-background border-input"
                />
                <Button
                  onClick={() => handleSendMessage()}
                  disabled={!inputMessage.trim() || isTyping}
                  size="icon"
                  className="h-12 w-12 shadow-md hover:scale-105 transition-transform"
                >
                  <Send size={18} />
                </Button>
              </div>
            </div>
          </Card>

          {/* Quick Questions */}
          <div className="grid md:grid-cols-2 gap-3">
            {quickQuestions.map((question, index) => {
              const Icon = question.icon;
              return (
                <Button
                  key={index}
                  variant="outline"
                  className="h-auto p-4 text-left justify-start bg-card hover:bg-muted hover:text-primary border-dashed hover:border-solid hover:border-primary/50 transition-all text-foreground"
                  onClick={() => handleQuickQuestion(question.query)}
                >
                  <div className="bg-primary/10 p-2 rounded-lg mr-3">
                    <Icon size={16} className="text-primary" />
                  </div>
                  <span className="text-sm font-medium">{question.text}</span>
                </Button>
              );
            })}
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Assistant Capabilities */}
          <Card className="p-5 shadow-sm">
            <h3 className="font-semibold mb-4 flex items-center gap-2 text-primary">
              <HelpCircle size={18} />
              I Can Help With
            </h3>
            <ul className="space-y-3 text-sm">
              <li className="flex items-start gap-3 p-2 rounded-lg hover:bg-muted transition-colors">
                <div className="w-1.5 h-1.5 bg-primary rounded-full mt-2 shrink-0"></div>
                <span>Finding clinical trials based on your condition and location</span>
              </li>
              <li className="flex items-start gap-3 p-2 rounded-lg hover:bg-muted transition-colors">
                <div className="w-1.5 h-1.5 bg-secondary rounded-full mt-2 shrink-0"></div>
                <span>Explaining informed consent and patient rights</span>
              </li>
              <li className="flex items-start gap-3 p-2 rounded-lg hover:bg-muted transition-colors">
                <div className="w-1.5 h-1.5 bg-accent rounded-full mt-2 shrink-0"></div>
                <span>Connecting you with relevant community discussions</span>
              </li>
              <li className="flex items-start gap-3 p-2 rounded-lg hover:bg-muted transition-colors">
                <div className="w-1.5 h-1.5 bg-info rounded-full mt-2 shrink-0"></div>
                <span>Recommending educational resources</span>
              </li>
            </ul>
          </Card>

          {/* Suggested Topics */}
          <Card className="p-5 shadow-sm">
            <h3 className="font-semibold mb-3">Suggested Topics</h3>
            <div className="space-y-2">
              {suggestions.map((suggestion, index) => (
                <Button
                  key={index}
                  variant="ghost"
                  size="sm"
                  className="w-full justify-start text-xs h-auto py-2.5 px-3 whitespace-normal text-left hover:bg-accent/10 hover:text-accent border border-transparent hover:border-accent/20"
                  onClick={() => handleSendMessage(suggestion)}
                >
                  <span className="line-clamp-2">{suggestion}</span>
                </Button>
              ))}
            </div>
          </Card>

          {/* Tips */}
          <div className="p-4 rounded-xl bg-info/10 border border-info/20">
            <h3 className="font-semibold mb-2 text-info text-sm flex items-center gap-2">
              <Lightbulb size={14} /> Tips for Better Help
            </h3>
            <ul className="text-xs space-y-1.5 text-muted-foreground/80 font-medium">
              <li>• Be specific about your location and condition</li>
              <li>• Ask follow-up questions for clarification</li>
              <li>• Use "show me" or "find" for actionable requests</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}