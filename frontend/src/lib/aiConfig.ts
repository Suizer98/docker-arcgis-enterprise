import { API_URLS } from './config/apiConfig';

// AI Configuration
export const AI_CONFIG = {
  // Model settings
  model: 'llama-3.1-8b-instant',

  // API settings - Use centralized config
  apiUrl: API_URLS.CHAT,

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
