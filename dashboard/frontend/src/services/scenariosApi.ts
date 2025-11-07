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

import api from './api';

export interface Scenario {
  id: string;
  name: string;
  description?: string;
  gns3_project_id?: string;
  created_at?: string;
  updated_at?: string;
  is_active?: boolean;
  status: 'idle' | 'starting' | 'running' | 'stopping' | 'error' | 'completed' | 'failed';
  started_at?: string;
  message?: string;
  config?: any;
  topology?: {
    nodes: any[];
    links: any[];
  };
  has_config?: boolean;
  has_topology?: boolean;
}

export interface ScenarioStatus {
  scenario_name: string;
  status: string;
  started_at?: string;
  completed_at?: string;
  message?: string;
}

export interface ScenarioConfig {
  scenario_name: string;
  config_file: string;
  config: any;
}

export interface ScenarioTopology {
  scenario_name: string;
  topology_file: string;
  topology: any;
}

export interface ScenarioLogs {
  scenario_name: string;
  logs: string[];
  total_lines: number;
  message?: string;
}

/**
 * Check if the API is available before making requests
 */
let apiAvailabilityStatus = {
  available: true,
  lastCheck: 0,
  retryAfterMs: 30000 // Only retry after 30 seconds
};

// Prevent multiple simultaneous API calls when API is down
const checkApiAvailability = async (): Promise<boolean> => {
  const now = Date.now();
  
  // Return cached status if checked recently
  if (!apiAvailabilityStatus.available && 
      (now - apiAvailabilityStatus.lastCheck) < apiAvailabilityStatus.retryAfterMs) {
    return false;
  }
  
  try {
    // Simple health check request
    await api.get('/health');
    apiAvailabilityStatus.available = true;
    return true;
  } catch (error) {
    console.warn('API is currently unavailable. Will retry later.');
    apiAvailabilityStatus.available = false;
    apiAvailabilityStatus.lastCheck = now;
    return false;
  }
};

/**
 * Get all scenarios
 */
export const getScenarios = async (): Promise<Scenario[]> => {
  // Skip request if API is known to be down
  if (apiAvailabilityStatus.lastCheck > 0 && !apiAvailabilityStatus.available) {
    const now = Date.now();
    if ((now - apiAvailabilityStatus.lastCheck) < apiAvailabilityStatus.retryAfterMs) {
      console.warn('Skipping scenarios API call as API is unavailable');
      return [];
    }
  }
  
  try {
    const response = await api.get('/scenarios');
    
    // Reset API availability status on success
    apiAvailabilityStatus.available = true;
    
    // Handle the response format - API returns array of scenario objects
    if (response.data && Array.isArray(response.data)) {
      return response.data.map((scenario: any) => ({
        id: scenario.name || 'unknown',
        name: scenario.name || 'Unknown',
        description: scenario.description || `Scenario: ${scenario.name}`,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        is_active: scenario.status === 'running',
        status: scenario.status || 'idle',
        started_at: scenario.started_at,
        message: scenario.message,
        has_config: scenario.has_config || false,
        has_topology: scenario.has_topology || false,
        config: {},
        topology: { nodes: [], links: [] }
      }));
    } else if (response.data && response.data.scenarios && Array.isArray(response.data.scenarios)) {
      // Fallback for wrapped response format
      return response.data.scenarios.map((scenario: any) => ({
        id: scenario.name || 'unknown',
        name: scenario.name || 'Unknown',
        description: scenario.description || `Scenario: ${scenario.name}`,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        is_active: scenario.status === 'running',
        status: scenario.status || 'idle',
        started_at: scenario.started_at,
        message: scenario.message,
        has_config: scenario.has_config || false,
        has_topology: scenario.has_topology || false,
        config: {},
        topology: { nodes: [], links: [] }
      }));
    } else {
      console.warn('Unexpected response format from scenarios API:', response.data);
      return [];
    }
  } catch (error: any) {
    // Update API availability status
    apiAvailabilityStatus.available = false;
    apiAvailabilityStatus.lastCheck = Date.now();
    
    // Only log detailed error if it's not a network error (to reduce log noise)
    if (!error.message?.includes('Network Error')) {
      console.error('Failed to fetch scenarios:', error);
      // Check if we have more detailed error info
      if (error.response) {
        console.error('Server response:', error.response.status, error.response.data);
      }
    } else {
      console.warn('Network error when fetching scenarios. Will retry later.');
    }
    return [];
  }
};

/**
 * Get scenario status
 */
export const getScenarioStatus = async (scenarioId: string): Promise<ScenarioStatus | null> => {
  if (!apiAvailabilityStatus.available) {
    return null;
  }
  
  try {
    const response = await api.get(`/scenarios/${scenarioId}/status`);
    return response.data;
  } catch (error) {
    console.error(`Failed to fetch scenario status ${scenarioId}:`, error);
    return null;
  }
};

/**
 * Get scenario configuration
 */
export const getScenarioConfig = async (scenarioId: string): Promise<ScenarioConfig | null> => {
  if (!apiAvailabilityStatus.available) {
    return null;
  }
  
  try {
    const response = await api.get(`/scenarios/${scenarioId}/config`);
    return response.data;
  } catch (error) {
    console.error(`Failed to fetch scenario config ${scenarioId}:`, error);
    return null;
  }
};

/**
 * Get scenario by ID
 */
export const getScenarioById = async (scenarioId: string): Promise<Scenario | null> => {
  if (!apiAvailabilityStatus.available) {
    return null;
  }
  
  try {
    const response = await api.get(`/scenarios/${scenarioId}`);
    return response.data;
  } catch (error) {
    console.error(`Failed to fetch scenario ${scenarioId}:`, error);
    return null;
  }
};

/**
 * Create new scenario
 */
export const createScenario = async (scenario: Omit<Scenario, 'id' | 'created_at' | 'updated_at' | 'status'>): Promise<Scenario | null> => {
  if (!await checkApiAvailability()) {
    throw new Error('API is currently unavailable. Please try again later.');
  }
  
  try {
    const response = await api.post('/scenarios', scenario);
    return response.data;
  } catch (error) {
    console.error('Failed to create scenario:', error);
    throw error;
  }
};

/**
 * Update existing scenario
 */
export const updateScenario = async (scenarioId: string, scenario: Partial<Scenario>): Promise<Scenario | null> => {
  if (!await checkApiAvailability()) {
    throw new Error('API is currently unavailable. Please try again later.');
  }
  
  try {
    const response = await api.put(`/scenarios/${scenarioId}`, scenario);
    return response.data;
  } catch (error) {
    console.error(`Failed to update scenario ${scenarioId}:`, error);
    throw error;
  }
};

/**
 * Delete scenario
 */
export const deleteScenario = async (scenarioId: string): Promise<boolean> => {
  if (!await checkApiAvailability()) {
    throw new Error('API is currently unavailable. Please try again later.');
  }
  
  try {
    await api.delete(`/scenarios/${scenarioId}`);
    return true;
  } catch (error) {
    console.error(`Failed to delete scenario ${scenarioId}:`, error);
    throw error;
  }
};

/**
 * Start scenario
 */
export const startScenario = async (scenarioId: string): Promise<any> => {
  if (!await checkApiAvailability()) {
    throw new Error('API is currently unavailable. Please try again later.');
  }
  
  try {
    const response = await api.post(`/scenarios/${scenarioId}/run`);
    return response.data;
  } catch (error) {
    console.error(`Failed to start scenario ${scenarioId}:`, error);
    throw error;
  }
};

/**
 * Stop scenario
 */
export const stopScenario = async (scenarioId: string): Promise<any> => {
  if (!await checkApiAvailability()) {
    throw new Error('API is currently unavailable. Please try again later.');
  }
  
  try {
    const response = await api.post(`/scenarios/${scenarioId}/stop`);
    return response.data;
  } catch (error) {
    console.error(`Failed to stop scenario ${scenarioId}:`, error);
    throw error;
  }
};

/**
 * Get scenario topology
 */
export const getScenarioTopology = async (scenarioId: string): Promise<ScenarioTopology | null> => {
  if (!await checkApiAvailability()) {
    throw new Error('API is currently unavailable. Please try again later.');
  }
  
  try {
    const response = await api.get(`/scenarios/${scenarioId}/topology`);
    return response.data;
  } catch (error) {
    console.error(`Failed to fetch topology for scenario ${scenarioId}:`, error);
    return null;
  }
};

/**
 * Update scenario topology
 */
export const updateScenarioTopology = async (scenarioId: string, topology: any): Promise<any> => {
  if (!await checkApiAvailability()) {
    throw new Error('API is currently unavailable. Please try again later.');
  }
  
  try {
    const response = await api.put(`/scenarios/${scenarioId}/topology`, topology);
    return response.data;
  } catch (error) {
    console.error(`Failed to update topology for scenario ${scenarioId}:`, error);
    throw error;
  }
};

/**
 * Get scenario logs
 */
export const getScenarioLogs = async (scenarioId: string, lines: number = 100): Promise<ScenarioLogs> => {
  if (!await checkApiAvailability()) {
    throw new Error('API is currently unavailable. Please try again later.');
  }
  
  try {
    const response = await api.get(`/scenarios/${scenarioId}/logs?lines=${lines}`);
    return response.data;
  } catch (error) {
    console.error(`Failed to get scenario logs for ${scenarioId}:`, error);
    throw error;
  }
}; 