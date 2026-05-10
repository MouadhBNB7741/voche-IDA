import { useState, useRef, useEffect, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeSanitize from "rehype-sanitize";

import { Card } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";

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
} from "lucide-react";

import { toast } from "sonner";
import { PageHeader } from "../components/ui/PageHeader";

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

const greeting: Message = {
  id: "greeting",
  content:
    "Hello! I'm your **VOCHE Platform assistant**. I can help you navigate clinical trials, community resources, and questions about participating in health research. What can I help you with today?",
  sender: "assistant",
  timestamp: Date.now(),
};

const CHAT_URL = `${import.meta.env.VITE_API_BASE_URL}/system/stats`;

function Assistant() {
  const [messages, setMessages] = useState<Message[]>([greeting]);
  const [inputMessage, setInputMessage] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

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

  // chat history
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

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({
      behavior: "smooth",
    });
  }, [messages, isStreaming]);

  const sendMessage = useCallback(
    async (text?: string) => {
      const content = (text ?? inputMessage)
        .replace(/[<>]/g, "")
        .trim();

      if (!content || isStreaming) return;

      const userMsg: Message = {
        id: crypto.randomUUID(),
        content,
        sender: "user",
        timestamp: Date.now(),
      };

      const history = [...messages, userMsg];

      setMessages(history);
      setInputMessage("");
      setIsStreaming(true);

      const assistantId = crypto.randomUUID();

      setMessages((m) => [
        ...m,
        {
          id: assistantId,
          content: "",
          sender: "assistant",
          timestamp: Date.now(),
        },
      ]);

      const controller = new AbortController();
      abortRef.current = controller;

      // Request timeout
      const timeout = setTimeout(() => {
        controller.abort();
      }, 30000);

      try {
        const resp = await fetch(CHAT_URL, {
          method: "POST",

          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY}`,
          },

          body: JSON.stringify({
            system:
              "You are the VOCHE AI Assistant helping users understand clinical trials, patient rights, community discussions, and health research resources. Provide clear, safe, and supportive responses.",

            context: {
              platform: "VOCHE",
              feature: "AI Assistant",
              version: "v1",
            },

            messages: history
              .slice(-20)
              .filter((m) => m.id !== "greeting")
              .map((m) => ({
                role: m.sender === "user" ? "user" : "assistant",
                content: m.content,
              })),
          }),

          signal: controller.signal,
        });

        if (!resp.ok || !resp.body) {
          let msg = "Something went wrong. Please try again.";

          if (resp.status === 429) {
            msg = "Too many requests — please wait a moment.";
          }

          if (resp.status === 402) {
            msg =
              "AI credits exhausted. Please add credits to continue.";
          }

          toast.error(msg);

          setMessages((m) =>
            m.filter((x) => x.id !== assistantId)
          );

          setIsStreaming(false);

          return;
        }

        const reader = resp.body.getReader();
        const decoder = new TextDecoder();

        let buffer = "";
        let assistantText = "";
        let done = false;

        while (!done) {
          const { value, done: readerDone } =
            await reader.read();

          if (readerDone) break;

          buffer += decoder.decode(value, {
            stream: true,
          });

          let nl: number;

          while ((nl = buffer.indexOf("\n")) !== -1) {
            let line = buffer.slice(0, nl);

            buffer = buffer.slice(nl + 1);

            if (line.endsWith("\r")) {
              line = line.slice(0, -1);
            }

            if (!line || line.startsWith(":")) continue;

            if (!line.startsWith("data: ")) continue;

            const json = line.slice(6).trim();

            if (json === "[DONE]") {
              done = true;
              break;
            }

            try {
              const parsed = JSON.parse(json);

              const delta = parsed.choices?.[0]?.delta
                ?.content as string | undefined;

              if (delta) {
                assistantText += delta;

                setMessages((m) =>
                  m.map((x) =>
                    x.id === assistantId
                      ? {
                          ...x,
                          content: assistantText,
                        }
                      : x
                  )
                );
              }
            } catch {
              buffer = line + "\n" + buffer;
              break;
            }
          }
        }
      } catch (err) {
        if ((err as Error).name === "AbortError") {
          toast.info("Response stopped.");
        } else {
          console.error(err);

          toast.error(
            "Connection error. Please try again."
          );

          setMessages((m) =>
            m.filter((x) => x.id !== assistantId)
          );
        }
      } finally {
        clearTimeout(timeout);

        setIsStreaming(false);
        abortRef.current = null;
      }
    },
    [inputMessage, isStreaming, messages]
  );

  const clearChat = () => {
    abortRef.current?.abort();

    setMessages([
      {
        ...greeting,
        timestamp: Date.now(),
      },
    ]);
  };

  const formatTime = (ts: number) =>
    new Date(ts).toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
      hour12: true,
    });

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
          <Card className="h-[70vh] min-h-[500px] flex flex-col shadow-lg border-border/60">
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              {messages.length === 1 && (
                <div className="text-center py-12">
                  <Bot
                    size={42}
                    className="mx-auto text-emerald-600 mb-4"
                  />

                  <h3 className="text-lg font-semibold mb-2">
                    Start a conversation
                  </h3>

                  <p className="text-sm text-muted-foreground max-w-md mx-auto">
                    Ask about clinical trials,
                    patient rights, research
                    participation, or community
                    resources.
                  </p>
                </div>
              )}

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

                  <div
                    className={`max-w-[85%] ${
                      message.sender === "user"
                        ? "text-right"
                        : "text-left"
                    }`}
                  >
                    <div
                      className={`p-4 rounded-2xl shadow-sm inline-block text-left ${
                        message.sender === "user"
                          ? "bg-primary text-primary-foreground rounded-tr-none"
                          : "bg-muted rounded-tl-none"
                      }`}
                    >
                      {message.sender ===
                      "assistant" ? (
                        message.content ? (
                          <div className="prose prose-sm dark:prose-invert max-w-none prose-p:my-2 prose-ul:my-2 prose-ol:my-2 prose-headings:mt-3 prose-headings:mb-2">
                            <ReactMarkdown
                              remarkPlugins={[
                                remarkGfm,
                              ]}
                              rehypePlugins={[
                                rehypeSanitize,
                              ]}
                            >
                              {message.content}
                            </ReactMarkdown>
                          </div>
                        ) : (
                          <div className="flex gap-1.5 py-1">
                            <span className="w-2 h-2 bg-muted-foreground/50 rounded-full animate-bounce" />

                            <span
                              className="w-2 h-2 bg-muted-foreground/50 rounded-full animate-bounce"
                              style={{
                                animationDelay:
                                  "0.1s",
                              }}
                            />

                            <span
                              className="w-2 h-2 bg-muted-foreground/50 rounded-full animate-bounce"
                              style={{
                                animationDelay:
                                  "0.2s",
                              }}
                            />
                          </div>
                        )
                      ) : (
                        <p className="text-sm leading-relaxed whitespace-pre-wrap">
                          {message.content}
                        </p>
                      )}
                    </div>

                    <p className="text-[10px] text-muted-foreground mt-1.5 font-medium px-1">
                      {formatTime(
                        message.timestamp
                      )}
                    </p>
                  </div>
                </div>
              ))}

              <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <div className="p-4 bg-muted/20 border-t">
              <div className="flex gap-3">
                <Input
                  value={inputMessage}
                  onChange={(e) =>
                    setInputMessage(
                      e.target.value
                    )
                  }
                  placeholder="Ask about clinical trials, resources, or your rights..."
                  maxLength={4000}
                  aria-label="Ask the VOCHE AI Assistant a question"
                  onKeyDown={(e) => {
                    if (
                      e.key === "Enter" &&
                      !e.shiftKey
                    ) {
                      e.preventDefault();
                      sendMessage();
                    }
                  }}
                  disabled={isStreaming}
                  className="flex-1 h-12 shadow-sm bg-background border-input"
                />

                {isStreaming && (
                  <Button
                    variant="outline"
                    onClick={() =>
                      abortRef.current?.abort()
                    }
                    className="h-12"
                  >
                    Stop
                  </Button>
                )}

                <Button
                  onClick={() => sendMessage()}
                  disabled={
                    !inputMessage.trim() ||
                    isStreaming
                  }
                  size="icon"
                  className="h-12 w-12 shadow-md hover:scale-105 transition-transform bg-emerald-600 hover:bg-emerald-700"
                >
                  <Send
                    size={18}
                    className="text-white"
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
                  disabled={isStreaming}
                  className="h-auto p-4 text-left justify-start bg-card hover:bg-muted hover:text-emerald-700 border-dashed hover:border-solid hover:border-emerald-500/50 transition-all text-foreground"
                  onClick={() =>
                    sendMessage(q.text)
                  }
                >
                  <div className="bg-emerald-500/10 p-2 rounded-lg mr-3">
                    <Icon
                      size={16}
                      className="text-emerald-600"
                    />
                  </div>

                  <span className="text-sm font-medium">
                    {q.text}
                  </span>
                </Button>
              );
            })}
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          <Card className="p-5 shadow-sm">
            <h3 className="font-semibold mb-4 flex items-center gap-2 text-emerald-700">
              <HelpCircle size={18} />
              I Can Help With
            </h3>

            <ul className="space-y-3 text-sm">
              {[
                "Finding clinical trials based on your condition and location",
                "Explaining informed consent and patient rights",
                "Connecting you with relevant community discussions",
                "Recommending educational resources",
              ].map((item, i) => (
                <li
                  key={i}
                  className="flex items-start gap-3 p-2 rounded-lg hover:bg-muted transition-colors"
                >
                  <div className="w-1.5 h-1.5 bg-emerald-600 rounded-full mt-2 shrink-0" />

                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </Card>

          <Card className="p-5 shadow-sm">
            <h3 className="font-semibold mb-3">
              Suggested Topics
            </h3>

            <div className="space-y-2">
              {suggestions.map((s, i) => (
                <Button
                  key={i}
                  variant="ghost"
                  size="sm"
                  disabled={isStreaming}
                  className="w-full justify-start text-xs h-auto py-2.5 px-3 whitespace-normal text-left hover:bg-emerald-500/10 hover:text-emerald-700 border border-transparent hover:border-emerald-500/20"
                  onClick={() =>
                    sendMessage(s)
                  }
                >
                  <span className="line-clamp-2">
                    {s}
                  </span>
                </Button>
              ))}
            </div>
          </Card>

          <div className="p-4 rounded-xl bg-sky-500/10 border border-sky-500/20">
            <h3 className="font-semibold mb-2 text-sky-700 text-sm flex items-center gap-2">
              <Lightbulb size={14} />
              Tips for Better Help
            </h3>

            <ul className="text-xs space-y-1.5 text-muted-foreground font-medium">
              <li>
                • Be specific about your location
                and condition
              </li>

              <li>
                • Ask follow-up questions for
                clarification
              </li>

              <li>
                • Use "show me" or "find" for
                actionable requests
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Assistant;