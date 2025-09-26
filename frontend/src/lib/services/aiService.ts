import { AI_CONFIG } from '../aiConfig';
import type { ChatMessage, AIResponse } from './types';

export class AIService {
  private messages: ChatMessage[] = [];

  // Add a message to the conversation
  addMessage(role: 'user' | 'assistant', content: string): ChatMessage {
    const message: ChatMessage = {
      id: Date.now().toString(),
      role,
      content,
      timestamp: new Date(),
    };
    this.messages.push(message);
    return message;
  }

  // Get all messages
  getMessages(): ChatMessage[] {
    return this.messages;
  }

  // Clear all messages
  clearMessages(): void {
    this.messages = [];
  }

  // Process user input by calling the agent API
  async processUserInput(userInput: string): Promise<AIResponse> {
    // Add user message
    const userMessage = this.addMessage('user', userInput);

    try {
      // Call the agent API
      const response = await fetch(AI_CONFIG.apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: userInput,
          session_id: 'default' // Simple session management
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      // Add AI response message
      const aiMessage = this.addMessage('assistant', data.response);

      return { userMessage, aiMessage, isLoading: false };
    } catch (error) {
      console.error('Error calling agent API:', error);
      
      let errorMessage = AI_CONFIG.errorMessage;
      if (error instanceof Error) {
        if (error.message.includes('Failed to fetch') || error.message.includes('ERR_NAME_NOT_RESOLVED')) {
          errorMessage = 'Unable to connect to the agent. Please make sure the agent is running and accessible.';
        } else if (error.message.includes('HTTP error')) {
          errorMessage = 'Agent API error. Please check the agent logs.';
        }
      }

      const aiMessage = this.addMessage('assistant', errorMessage);
      return { userMessage, aiMessage, isLoading: false };
    }
  }
}

// Export singleton instance
export const aiService = new AIService();