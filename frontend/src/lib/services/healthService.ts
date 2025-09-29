import { API_URLS } from '$lib/config/apiConfig';

export interface HealthStatus {
  status: 'healthy' | 'unhealthy' | 'checking';
  groq_api?: string;
  mcp_server_url?: string;
  version?: string;
  framework?: string;
  initialized?: boolean;
  tools_count?: number;
  error?: string;
}

class HealthService {
  private healthStatus: HealthStatus = { status: 'checking' };
  private checkInterval: NodeJS.Timeout | null = null;
  private listeners: ((status: HealthStatus) => void)[] = [];

  constructor() {
    this.startHealthCheck();
  }

  private async checkHealth(): Promise<HealthStatus> {
    try {
      const response = await fetch(API_URLS.HEALTH);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const data = await response.json();
      return {
        status: data.status === 'healthy' ? 'healthy' : 'unhealthy',
        ...data
      };
    } catch (error) {
      console.error('Health check failed:', error);
      return {
        status: 'unhealthy',
        error: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  }

  private async updateHealthStatus() {
    const newStatus = await this.checkHealth();
    this.healthStatus = newStatus;
    this.notifyListeners();
  }

  private startHealthCheck() {
    // Check immediately
    this.updateHealthStatus();
    
    // Then check every 5 seconds
    this.checkInterval = setInterval(() => {
      this.updateHealthStatus();
    }, 5000);
  }

  private notifyListeners() {
    this.listeners.forEach(listener => listener(this.healthStatus));
  }

  public subscribe(listener: (status: HealthStatus) => void) {
    this.listeners.push(listener);
    // Immediately call with current status
    listener(this.healthStatus);
    
    // Return unsubscribe function
    return () => {
      this.listeners = this.listeners.filter(l => l !== listener);
    };
  }

  public getCurrentStatus(): HealthStatus {
    return this.healthStatus;
  }

  public destroy() {
    if (this.checkInterval) {
      clearInterval(this.checkInterval);
      this.checkInterval = null;
    }
    this.listeners = [];
  }
}

// Export singleton instance
export const healthService = new HealthService();
