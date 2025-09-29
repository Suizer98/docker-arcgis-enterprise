// API Configuration
// Centralized configuration for all API endpoints

export const API_CONFIG = {
  // Get base API URL from environment variable or fallback to localhost
  getBaseUrl: (): string => {
    const envUrl = import.meta.env.VITE_AGENT_API_URL;
    if (envUrl) {
      // Remove /chat suffix if present to get base URL
      return envUrl.replace(/\/chat$/, '');
    }
    return 'http://localhost:8000';
  },

  // Get full chat API URL
  getChatUrl: (): string => {
    return `${API_CONFIG.getBaseUrl()}/chat`;
  },

  // Get health check URL
  getHealthUrl: (): string => {
    return `${API_CONFIG.getBaseUrl()}/health`;
  },

  // Get tools URL
  getToolsUrl: (): string => {
    return `${API_CONFIG.getBaseUrl()}/tools`;
  }
};

// Export individual URLs for convenience
export const API_URLS = {
  BASE: API_CONFIG.getBaseUrl(),
  CHAT: API_CONFIG.getChatUrl(),
  HEALTH: API_CONFIG.getHealthUrl(),
  TOOLS: API_CONFIG.getToolsUrl()
};
