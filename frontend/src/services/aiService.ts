import { apiClient } from '../lib/apiClient';
import { AI } from '../lib/api';

export type ContextType = 'general' | 'trial_inquiry' | 'symptom_guidance' | 'resource_qa';

export interface Citation {
  type: 'trial' | 'resource';
  id: string;
  title: string;
}

export interface ChatMessage {
  id: string;
  sender_role: 'user' | 'assistant' | 'system';
  content: string;
  citations: Citation[];
  safety_flagged: boolean;
  created_at: string;
}

export interface Conversation {
  id: string;
  title: string | null;
  context_type: ContextType;
  context_reference_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface ConversationDetail extends Conversation {
  messages: ChatMessage[];
}

export interface SendMessageResult {
  user_message: ChatMessage;
  assistant_message: ChatMessage;
}

export const aiService = {
  async listConversations(): Promise<Conversation[]> {
    const response = await apiClient.get<Conversation[]>(AI.CONVERSATIONS);
    return response.data;
  },

  async getConversation(id: string): Promise<ConversationDetail> {
    const response = await apiClient.get<ConversationDetail>(AI.CONVERSATION(id));
    return response.data;
  },

  async createConversation(contextType: ContextType = 'general'): Promise<Conversation> {
    const response = await apiClient.post<Conversation>(AI.CONVERSATIONS, { context_type: contextType });
    return response.data;
  },

  async deleteConversation(id: string): Promise<void> {
    await apiClient.delete(AI.CONVERSATION(id));
  },

  async sendMessage(conversationId: string, content: string): Promise<SendMessageResult> {
    // AI replies can take longer than the client's default 15s timeout.
    const response = await apiClient.post<SendMessageResult>(
      AI.MESSAGES(conversationId),
      { content },
      { timeout: 60000 },
    );
    return response.data;
  },

  async sendFeedback(messageId: string, rating: 1 | -1): Promise<void> {
    await apiClient.post(AI.FEEDBACK(messageId), { rating });
  },
};

export default aiService;
