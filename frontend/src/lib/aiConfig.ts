// AI Configuration
export const AI_CONFIG = {
  // Model settings
  model: 'llama-3.1-8b-instant',

  // API settings - Use environment variable or fallback to localhost
  apiUrl: import.meta.env.VITE_AGENT_API_URL ? `${import.meta.env.VITE_AGENT_API_URL}/chat` : 'http://localhost:8000/chat',

  // Response settings
  maxTokens: 1000,
  temperature: 0.7,

  // UI settings
  loadingMessage: 'Thinking...',
  errorMessage: 'Sorry, there was an error processing your request.',

  // Map-specific settings
  defaultZoom: 10,
  maxZoom: 20,
  minZoom: 1,

  // Supported map operations
  supportedOperations: [
    'setMapCenter',
    'setMapZoom',
    'findCoordinates',
    'geographicInfo',
  ],
};

// No environment variables needed for local agent backend
