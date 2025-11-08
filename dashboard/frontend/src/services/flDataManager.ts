/**
 * Copyright (c) 2025 Abdulmelik Saylan
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

/**
// Simplified FL Data Manager for direct API access
class FLDataManager {
  private baseUrl = '/api/fl-monitoring';

  /**
   * Get FL training status
   */
  async getTrainingStatus() {
    const response = await fetch(`${this.baseUrl}/metrics/fl/status`);
    if (!response.ok) {
      throw new Error(`Failed to get training status: ${response.status} ${response.statusText}`);
    }
    return response.json();
  }

  /**
   * Get FL rounds with optional parameters
   */
  async getRounds(params: {
    limit?: number;
    start_round?: number;
    end_round?: number;
    includeRoundsHistory?: boolean;
    source?: string;
  } = {}) {
    const searchParams = new URLSearchParams();
    
    if (params.limit) searchParams.append('limit', params.limit.toString());
    if (params.start_round) searchParams.append('start_round', params.start_round.toString());
    if (params.end_round) searchParams.append('end_round', params.end_round.toString());
    
    const url = `${this.baseUrl}/metrics/fl/rounds?${searchParams.toString()}`;
    const response = await fetch(url);
    
    if (!response.ok) {
      throw new Error(`Failed to get rounds: ${response.status} ${response.statusText}`);
    }
    
    const data = await response.json();
    return data.rounds || [];
  }

  /**
   * Get latest FL rounds
   */
  async getLatestRounds(limit: number = 10) {
    return this.getRounds({ limit });
  }

  /**
   * Initialize (simplified - no complex setup needed)
   */
  async initialize() {
    // Simple initialization - just verify API is reachable
    try {
      await this.getTrainingStatus();
      return true;
    } catch (error) {
      console.warn('FL Data Manager: API not reachable during initialization:', error);
      return false;
    }
  }

  /**
   * Cleanup method (for compatibility)
   */
  cleanup() {
    // No cleanup needed in simplified version
    console.log('FL Data Manager: Cleanup called');
  }

  /**
   * Reset method (alias for cleanup)
   */
  reset() {
    this.cleanup();
  }

  /**
   * Subscribe method (simplified - no real-time subscriptions)
   */
  subscribe(callback: (data: any) => void) {
    console.log('FL Data Manager: Subscribe called (no-op in simplified version)');
    // Return unsubscribe function
    return () => {};
  }

  /**
   * Subscribe to status (simplified)
   */
  subscribeToStatus(callback: (status: any) => void) {
    console.log('FL Data Manager: Subscribe to status called (no-op in simplified version)');
    // Return unsubscribe function
    return () => {};
  }
}

// Export singleton instance
export const flDataManager = new FLDataManager();

// Export initialization function for compatibility
export const initFLDataManager = async (enableRealTime: boolean = false) => {
  console.log('FL Data Manager: Initializing simplified version');
  return flDataManager.initialize();
};

// Export cleanup function for compatibility
export const cleanupFLDataManager = () => {
  flDataManager.cleanup();
}; 