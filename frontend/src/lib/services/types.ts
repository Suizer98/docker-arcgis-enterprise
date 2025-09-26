// Types and interfaces for AI service
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp?: Date;
}

export interface ToolCall {
  toolName: string;
  input: any;
  toolCallId?: string;
}

export interface ToolResult {
  toolName: string;
  output: any;
}

export interface AIResponse {
  userMessage: ChatMessage;
  aiMessage: ChatMessage;
  isLoading: boolean;
}
