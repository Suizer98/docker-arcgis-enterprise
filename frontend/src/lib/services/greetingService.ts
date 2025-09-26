import { generateText } from 'ai';
import { createGroq } from '@ai-sdk/groq';
import { getApiKey, hasValidApiKey } from '../aiConfig';

const DEFAULT_GREETING =
  "Hi! I'm your Map Assistant. Ask me about locations, directions, or exploring places!";

export class GreetingService {
  // Generate AI greeting
  async generateAIGreeting(): Promise<string> {
    // Return default greeting if no API key
    if (!hasValidApiKey()) {
      return DEFAULT_GREETING;
    }

    try {
      // Generate a dynamic greeting using AI
      const groq = createGroq({ apiKey: getApiKey() });

      const result = await generateText({
        model: groq('llama-3.1-8b-instant'),
        messages: [
          {
            role: 'user',
            content: `Generate a very short, friendly greeting for an ArcGIS AI Map Assistant. The greeting should:
- Be extremely concise (1 sentence, max 15 words)
- Mention map assistance capabilities
- Sound natural and welcoming
- NOT include technical details

Examples of good short greetings:
- "Hi! I'm your Map Assistant. Ask me about locations and directions!"
- "Welcome! I can help you explore places and find locations."
- "Hello! I'm here to help with maps and navigation."

Generate a unique, very short greeting:`,
          },
        ],
        temperature: 0.9,
      });

      return result.text.trim();
    } catch (error) {
      console.error('Error generating AI greeting:', error);
      return DEFAULT_GREETING;
    }
  }
}

// Export singleton instance
export const greetingService = new GreetingService();
