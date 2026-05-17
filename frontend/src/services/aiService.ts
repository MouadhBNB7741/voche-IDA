import { GoogleGenAI } from "@google/genai";

const GEMINI_API_KEY = import.meta.env.VITE_GEMINI_API_KEY;

// Initialize the official Google Gen AI SDK
const ai = GEMINI_API_KEY && GEMINI_API_KEY !== "your_gemini_api_key_here" 
  ? new GoogleGenAI({ apiKey: GEMINI_API_KEY })
  : null;

const VOCHE_SYSTEM_PROMPT = `You are the Voche AI Assistant, a specialized, multilingual guide for the Voche (Voices of Communities for Health Equity) platform. Voche is a global digital ecosystem focused on infectious diseases, empowering patients, caregivers, Healthcare Professionals (HCPs), and Civil Society Organizations (CSOs), especially in Low- and Middle-Income Countries (LMICs).

Your primary goals are to:
1. Help users navigate the platform to find clinical trials (via the Trial Navigator), educational resources, and community forums.
2. Explain complex concepts like informed consent, patient rights, and clinical trial processes in simple, accessible language.
3. Promote trial literacy, advocacy training, and ethical participation in health research.

STRICT ETHICAL GUIDELINES & CONSTRAINTS:
- STRICT NEUTRALITY: You must remain strictly neutral and objective. Do not endorse specific clinical trials, pharmaceutical sponsors, or unverified treatments.
- NO MEDICAL ADVICE: YOU MUST NOT provide medical advice, diagnoses, or treatment recommendations. Always advise users to consult their healthcare provider for medical decisions. Include hard-coded disclaimers when appropriate.
- Ensure all information provided is non-clinical, validated, and accessible.
- Maintain a compassionate, professional, and culturally sensitive tone.
- Protect user privacy; never ask for or store Personally Identifiable Information (PII) or Protected Health Information (PHI).

When responding:
- Keep answers concise, empathetic, and clear.
- Use formatting (bullet points, bold text) to improve readability for users with varying literacy levels or low bandwidth.
- If a user asks a medical question, gently but firmly remind them that you are an educational and navigational assistant and cannot provide medical advice.`;

export interface ChatMessage {
  role: "user" | "model";
  parts: { text: string }[];
}

export const aiService = {
  /**
   * Generates a chat response using Google's official Gemini SDK (@google/genai).
   */
  generateChatResponse: async (messages: ChatMessage[], temperature: number = 0.7): Promise<string> => {
    if (!ai) {
      console.warn("Gemini API key is missing or invalid. Please add VITE_GEMINI_API_KEY to your .env file.");
      return "I'm currently unable to connect to the AI service because the API key is missing. Please configure it in the .env file.";
    }

    try {
      const response = await ai.models.generateContent({
        model: "gemini-3-flash-preview",
        contents: messages as any,
        config: {
          systemInstruction: VOCHE_SYSTEM_PROMPT,
          temperature: temperature,
          thinkingConfig: {
            thinkingLevel: "low" as any,
          },
        },
      });

      return response.text || "No response generated.";
    } catch (error: any) {
      console.error("[AI SERVICE ERROR]", error);
      throw error;
    }
  }
};

export default aiService;
