import { writable } from 'svelte/store';
import type { ChatMessage } from './types';

export interface ChatState {
  messages: ChatMessage[];
  isLoading: boolean;
  isOpen: boolean;
  input: string;
}

class ChatStateService {
  private state = writable<ChatState>({
    messages: [],
    isLoading: false,
    isOpen: true,
    input: '',
  });

  // Get the state store
  getState() {
    return this.state;
  }

  // Update messages
  setMessages(messages: ChatMessage[]) {
    this.state.update(state => ({ ...state, messages }));
  }

  // Add a message
  addMessage(message: ChatMessage) {
    this.state.update(state => ({
      ...state,
      messages: [...state.messages, message],
    }));
  }

  // Clear all messages
  clearMessages() {
    this.state.update(state => ({
      ...state,
      messages: [],
    }));
  }

  // Set loading state
  setLoading(isLoading: boolean) {
    this.state.update(state => ({ ...state, isLoading }));
  }

  // Toggle sidebar
  toggleSidebar() {
    this.state.update(state => ({ ...state, isOpen: !state.isOpen }));
  }

  // Set sidebar open state
  setSidebarOpen(isOpen: boolean) {
    this.state.update(state => ({ ...state, isOpen }));
  }

  // Update input
  setInput(input: string) {
    this.state.update(state => ({ ...state, input }));
  }

  // Clear input
  clearInput() {
    this.state.update(state => ({ ...state, input: '' }));
  }

  // Get current state
  getCurrentState(): ChatState {
    let currentState: ChatState;
    this.state.subscribe(state => (currentState = state))();
    return currentState!;
  }
}

// Export singleton instance
export const chatStateService = new ChatStateService();
