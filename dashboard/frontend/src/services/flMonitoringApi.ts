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

import axios, { CancelTokenSource } from 'axios';
import { io, Socket } from 'socket.io-client';

const BASE_URL = '/api/fl-monitoring';

// Reduced caching for real-time updates
const CACHE_DURATION = 1000; // 1 second cache only for very recent requests
const cache = new Map<string, { data: any; timestamp: number }>();

const getFromCache = (key: string) => {
  const cached = cache.get(key);
  if (cached && Date.now() - cached.timestamp < CACHE_DURATION) {
    return cached.data;
  }
  cache.delete(key);
  return null;
};

const setCache = (key: string, data: any) => {
  cache.set(key, { data, timestamp: Date.now() });
  // Clean old cache entries
  if (cache.size > 10) {
    const oldestKey = Array.from(cache.keys())[0];
    cache.delete(oldestKey);
  }
};

// Also use localStorage for persistence across page reloads
const getFromLocalStorage = (key: string) => {
  try {
    const cached = localStorage.getItem(`fl_${key}`);
    if (cached) {
      const parsed = JSON.parse(cached);
      if (Date.now() - parsed.timestamp < CACHE_DURATION) {
        return parsed.data;
      }
      localStorage.removeItem(`fl_${key}`);
    }
  } catch (error) {
    console.warn('Failed to get from localStorage:', error);
  }
  return null;
};

const setLocalStorage = (key: string, data: any) => {
  try {
    localStorage.setItem(`fl_${key}`, JSON.stringify({
      data,
      timestamp: Date.now()
    }));
  } catch (error) {
    console.warn('Failed to set localStorage:', error);
  }
};

// WebSocket configuration for real-time updates
let socket: Socket | null = null;
let wsConnected = false;
let wsConnectionFailed = false;
let fallbackPolling = false;
let fallbackInterval: NodeJS.Timeout | null = null;
let reconnectAttempts = 0;
let maxReconnectAttempts = 10;
let baseReconnectDelay = 2000; // 2 seconds
let maxReconnectDelay = 60000; // 1 minute max
const wsSubscribers = new Set<(data: any) => void>();

// Calculate exponential backoff with jitter
const getReconnectDelay = () => {
  const delay = Math.min(
    baseReconnectDelay * Math.pow(2, reconnectAttempts),
    maxReconnectDelay
  );
  return delay + Math.random() * 1000; // Add jitter
};

// Initialize WebSocket connection for real-time FL metrics
export const initFLWebSocket = (collectorBaseUrl: string = 'http://localhost:8083') => {
  if (socket) {
    socket.disconnect();
  }

  console.log(`FL WebSocket: Attempting to connect to ${collectorBaseUrl} (attempt ${reconnectAttempts + 1})`);
  wsConnectionFailed = false;

  try {
    // Connect to collector's WebSocket endpoint
    socket = io(`${collectorBaseUrl}`, {
      transports: ['websocket', 'polling'],
      timeout: 15000, // Increased timeout
      reconnection: true,
      reconnectionAttempts: maxReconnectAttempts,
      reconnectionDelay: getReconnectDelay(),
      reconnectionDelayMax: maxReconnectDelay,
      randomizationFactor: 0.5
    });

    socket.on('connect', () => {
      console.log('✅ FL WebSocket connected to collector successfully');
      wsConnected = true;
      wsConnectionFailed = false;
      reconnectAttempts = 0; // Reset on successful connection
      
      // Stop fallback polling if it was active
      if (fallbackPolling && fallbackInterval) {
        clearInterval(fallbackInterval);
        fallbackInterval = null;
        fallbackPolling = false;
        console.log('🔄 FL WebSocket: Stopped fallback polling - WebSocket connection restored');
      }
      
      // Subscribe to FL server metrics
      socket?.emit('subscribe', {
        type: 'fl_server',
        interval: 5000  // 5 second updates for real-time training
      });
    });

    socket.on('disconnect', (reason) => {
      console.warn(`❌ FL WebSocket disconnected from collector: ${reason}`);
      wsConnected = false;
      
      // Start fallback polling for immediate data availability
      if (!fallbackPolling) {
        startFallbackPolling();
      }
    });

    socket.on('metrics_update', (data) => {
      console.log('📡 FL WebSocket: Received metrics update:', data);
      // Notify all subscribers
      wsSubscribers.forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          console.error('❌ FL WebSocket: Error in callback:', error);
        }
      });
    });

    socket.on('connect_error', (error) => {
      reconnectAttempts++;
      const delay = getReconnectDelay();
      console.warn(`⚠️ FL WebSocket connection error (attempt ${reconnectAttempts}/${maxReconnectAttempts}):`, error);
      console.log(`Next reconnection attempt in ${delay/1000}s`);
      
      wsConnected = false;
      wsConnectionFailed = true;
      
      // Start fallback polling after connection errors
      if (!fallbackPolling) {
        startFallbackPolling();
      }
    });

    socket.on('reconnect_failed', () => {
      console.error('❌ FL WebSocket: All reconnection attempts failed');
      wsConnected = false;
      wsConnectionFailed = true;
      reconnectAttempts = maxReconnectAttempts;
      
      // Ensure fallback polling is active
      if (!fallbackPolling) {
        startFallbackPolling();
      }
      
      // Schedule a retry after a longer delay
      setTimeout(() => {
        if (!wsConnected) {
          console.log('🔄 FL WebSocket: Attempting fresh connection after total failure');
          reconnectAttempts = 0; // Reset for fresh start
          initFLWebSocket(collectorBaseUrl);
        }
      }, 30000); // Wait 30 seconds before fresh attempt
    });

    socket.on('reconnect_attempt', (attemptNumber) => {
      console.log(`🔄 FL WebSocket: Reconnection attempt ${attemptNumber}/${maxReconnectAttempts}`);
    });

    socket.on('reconnect', (attemptNumber) => {
      console.log(`✅ FL WebSocket: Reconnected after ${attemptNumber} attempts`);
      reconnectAttempts = 0;
    });

  } catch (error) {
    console.error('❌ FL WebSocket: Failed to initialize WebSocket:', error);
    wsConnectionFailed = true;
    reconnectAttempts++;
    startFallbackPolling();
  }
};

// Fallback polling mechanism
const startFallbackPolling = () => {
  if (fallbackPolling) {
    return; // Already polling
  }
  
  console.log('🔄 FL WebSocket: Starting fallback API polling due to WebSocket connection issues');
  fallbackPolling = true;
  
  const pollForUpdates = async () => {
    try {
      // Get FL training status
      const statusResponse = await fetch('/api/fl-monitoring/metrics/fl/status');
      if (statusResponse.ok) {
        const statusData = await statusResponse.json();
        
        // Get recent rounds
        const roundsResponse = await fetch('/api/fl-monitoring/metrics/fl/rounds?limit=10');
        if (roundsResponse.ok) {
          const roundsData = await roundsResponse.json();
          
          // Simulate WebSocket data format
          const fallbackData = {
            type: 'fl_fallback_update',
            status: statusData,
            rounds: roundsData.rounds || [],
            timestamp: new Date().toISOString(),
            source: 'fallback_polling'
          };
          
          // Notify subscribers
          wsSubscribers.forEach(callback => {
            try {
              callback(fallbackData);
            } catch (error) {
              console.error('❌ FL Fallback: Error in callback:', error);
            }
          });
        }
      }
    } catch (error) {
      console.warn('⚠️ FL Fallback polling error:', error);
    }
  };
  
  // Poll every 5 seconds
  fallbackInterval = setInterval(pollForUpdates, 5000);
  
  // Run first poll immediately
  pollForUpdates();
};

// Subscribe to real-time FL updates
export const subscribeFLUpdates = (callback: (data: any) => void): (() => void) => {
  wsSubscribers.add(callback);
  
  // Return unsubscribe function
  return () => {
    wsSubscribers.delete(callback);
  };
};

// Get WebSocket connection status
export const getWebSocketStatus = () => ({
  connected: wsConnected,
  connectionFailed: wsConnectionFailed,
  fallbackActive: fallbackPolling,
  subscribers: wsSubscribers.size,
  status: wsConnected ? 'connected' : (fallbackPolling ? 'fallback_polling' : 'disconnected')
});

// Disconnect WebSocket
export const disconnectFLWebSocket = () => {
  console.log('🔌 FL WebSocket: Disconnecting and stopping all monitoring');
  
  if (socket) {
    socket.disconnect();
    socket = null;
    wsConnected = false;
  }
  
  // Stop fallback polling
  if (fallbackInterval) {
    clearInterval(fallbackInterval);
    fallbackInterval = null;
    fallbackPolling = false;
  }
  
  // Clear subscribers
  wsSubscribers.clear();
  
  wsConnectionFailed = false;
};

export interface FLMetric {
  timestamp: string;
  round: number;
  accuracy: number;
  loss: number;
  clients_connected: number;
  clients_total: number;
  training_complete: boolean;
  model_size_mb?: number;
  status: string;
}

export interface FLLatestStatus {
  round: number;
  status: string;
  accuracy: number;
  loss: number;
  clients_connected: number;
  clients_total: number;
  start_time: string;
  last_update: string;
  training_complete: boolean;
  model_size_mb?: number;
}

export interface FLMetricsWindow {
  metrics: FLMetric[];
  start_round: number;
  end_round: number;
  actual_start: number;
  actual_end: number;
  count: number;
}

export interface FLMetricsPaginated {
  metrics: FLMetric[];
  page: number;
  page_size: number;
  total_pages: number;
  total_items: number;
  has_next: boolean;
  has_previous: boolean;
  start_round: number;
  end_round: number;
}

export interface FLMetricsSummary {
  total_rounds: number;
  min_accuracy: number;
  max_accuracy: number;
  min_loss: number;
  max_loss: number;
  avg_accuracy: number;
  avg_loss: number;
  training_complete: boolean;
  data_points: number;
  round_range: [number, number];
}

// Create axios instance with optimized settings for real-time data
const api = axios.create({
  timeout: 10000, // 10 seconds timeout
});

// Request management for cancellation
const activeRequests = new Map<string, CancelTokenSource>();

const cancelPendingRequest = (key: string) => {
  const existingCancel = activeRequests.get(key);
  if (existingCancel) {
    existingCancel.cancel('Cancelled due to new request');
    activeRequests.delete(key);
  }
};

export const getFLMetrics = async (params?: {
  start_time?: string;
  end_time?: string;
  limit?: number;
}): Promise<FLMetric[]> => {
  const requestKey = `fl-metrics-${JSON.stringify(params)}`;
  
  // Only use cache for identical requests within 1 second
  const cached = getFromCache(requestKey);
  if (cached) {
    console.log(`FL API: Using cached data for ${requestKey}, ${cached.length} items`);
    return cached;
  }
  
  cancelPendingRequest(requestKey);
  const cancelToken = axios.CancelToken.source();
  activeRequests.set(requestKey, cancelToken);

  try {
    // Get larger dataset for better charting - default to recent 500 points
    const optimizedParams = {
      ...params,
      limit: params?.limit || 200 // Reduced default for better performance
    };
    
    console.log(`FL API: Fetching metrics with params:`, optimizedParams);
    
    const response = await api.get(`${BASE_URL}/metrics`, { 
      params: optimizedParams,
      cancelToken: cancelToken.token
    });
    
    const data = response.data;
    activeRequests.delete(requestKey);
    
    console.log(`FL API: Received ${Array.isArray(data) ? data.length : 'non-array'} items from backend`);
    
    // Only cache small responses to avoid memory issues
    if (Array.isArray(data) && data.length < 100) {
      setCache(requestKey, data);
    }
    
    return Array.isArray(data) ? data : [];
  } catch (error) {
    activeRequests.delete(requestKey);
    if (axios.isCancel(error)) {
      console.log('FL metrics request cancelled');
      return [];
    }
    console.error('Failed to fetch FL metrics:', error);
    console.error('Request details:', { url: `${BASE_URL}/metrics`, params });
    throw error;
  }
};

export const getFLMetricsWindow = async (
  startRound: number,
  endRound: number
): Promise<FLMetricsWindow> => {
  const cacheKey = `window_${startRound}_${endRound}`;
  
  // Check cache first
  const cached = getFromCache(cacheKey);
  if (cached) {
    return cached;
  }

  try {
    const response = await api.get('/metrics/fl/rounds', {
      params: {
        start_round: startRound,
        end_round: endRound,
        limit: endRound - startRound + 1,
        format: 'detailed',
        source: 'both'  // Use both FL server and collector data
      }
    });

    const result: FLMetricsWindow = {
      metrics: response.data.rounds || [],
      start_round: startRound,
      end_round: endRound,
      actual_start: response.data.rounds?.[0]?.round || startRound,
      actual_end: response.data.rounds?.[response.data.rounds?.length - 1]?.round || endRound,
      count: response.data.returned_rounds || 0
    };

    setCache(cacheKey, result);
    return result;
  } catch (error) {
    console.error('Error fetching FL metrics window:', error);
    throw error;
  }
};

export const getFLMetricsPaginated = async (
  page: number,
  pageSize: number = 100
): Promise<FLMetricsPaginated> => {
  const requestKey = `fl-paginated-${page}-${pageSize}`;
  
  cancelPendingRequest(requestKey);
  const cancelToken = axios.CancelToken.source();
  activeRequests.set(requestKey, cancelToken);

  try {
    const response = await api.get(`${BASE_URL}/metrics/paginated`, {
      params: { page, page_size: pageSize },
      cancelToken: cancelToken.token
    });
    
    const data = response.data;
    activeRequests.delete(requestKey);
    return data;
  } catch (error) {
    activeRequests.delete(requestKey);
    if (axios.isCancel(error)) {
      throw new Error('Request cancelled');
    }
    console.error('Failed to fetch FL metrics paginated:', error);
    throw error;
  }
};

export const getFLMetricsAroundRound = async (
  targetRound: number,
  windowSize: number = 100
): Promise<FLMetricsWindow> => {
  const requestKey = `fl-around-${targetRound}-${windowSize}`;
  
  cancelPendingRequest(requestKey);
  const cancelToken = axios.CancelToken.source();
  activeRequests.set(requestKey, cancelToken);

  try {
    const response = await api.get(`${BASE_URL}/metrics/around`, {
      params: { target_round: targetRound, window_size: windowSize },
      cancelToken: cancelToken.token
    });
    
    const data = response.data;
    activeRequests.delete(requestKey);
    return data;
  } catch (error) {
    activeRequests.delete(requestKey);
    if (axios.isCancel(error)) {
      throw new Error('Request cancelled');
    }
    console.error('Failed to fetch FL metrics around round:', error);
    throw error;
  }
};

export const getFLMetricsSummary = async (): Promise<FLMetricsSummary> => {
  const requestKey = 'fl-summary';
  
  // Don't cache summary as it changes frequently
  cancelPendingRequest(requestKey);
  const cancelToken = axios.CancelToken.source();
  activeRequests.set(requestKey, cancelToken);

  try {
    const response = await api.get(`${BASE_URL}/metrics/summary`, {
      cancelToken: cancelToken.token
    });
    
    const data = response.data;
    activeRequests.delete(requestKey);
    return data;
  } catch (error) {
    activeRequests.delete(requestKey);
    if (axios.isCancel(error)) {
      throw new Error('Request cancelled');
    }
    console.error('Failed to fetch FL metrics summary:', error);
    throw error;
  }
};

export const getLatestFLStatus = async (): Promise<FLLatestStatus> => {
  const requestKey = 'latest-status';
  
  // Never cache latest status - always fetch fresh
  cancelPendingRequest(requestKey);
  const cancelToken = axios.CancelToken.source();
  activeRequests.set(requestKey, cancelToken);

  try {
    const response = await api.get(`${BASE_URL}/latest`, {
      cancelToken: cancelToken.token
    });
    
    const data = response.data;
    activeRequests.delete(requestKey);
    return data;
  } catch (error) {
    activeRequests.delete(requestKey);
    if (axios.isCancel(error)) {
      throw new Error('Request cancelled');
    }
    console.error('Failed to fetch latest FL status:', error);
    throw error;
  }
};

export const getFLRoundsWithFilters = async (params: {
  start_round?: number;
  end_round?: number;
  limit?: number;
  offset?: number;
  min_accuracy?: number;
  max_accuracy?: number;
  source?: 'collector' | 'fl_server' | 'both';
  format?: 'detailed' | 'summary';
  sort_order?: 'asc' | 'desc';
}): Promise<{
  rounds: FLMetric[];
  total_rounds: number;
  returned_rounds: number;
  latest_round: number;
  pagination: {
    limit: number;
    offset: number;
    has_more: boolean;
  };
  filters: any;
}> => {
  const cacheKey = `filtered_${JSON.stringify(params)}`;
  
  // Check cache first (shorter cache for filtered data)
  const cached = getFromCache(cacheKey);
  if (cached) {
    return cached;
  }

  try {
    const response = await api.get('/metrics/fl/rounds', {
      params: {
        ...params,
        source: params.source || 'both',
        format: params.format || 'detailed'
      }
    });

    const result = {
      rounds: response.data.rounds || [],
      total_rounds: response.data.total_rounds || 0,
      returned_rounds: response.data.returned_rounds || 0,
      latest_round: response.data.latest_round || 0,
      pagination: response.data.pagination || {},
      filters: response.data.filters || {}
    };

    setCache(cacheKey, result);
    return result;
  } catch (error) {
    console.error('Error fetching filtered FL rounds:', error);
    throw error;
  }
};

export const getFLLatestRounds = async (limit: number = 50): Promise<FLMetric[]> => {
  const cacheKey = `latest_${limit}`;
  
  // Check cache first
  const cached = getFromCache(cacheKey);
  if (cached) {
    return cached;
  }

  try {
    // Try FL server direct endpoint first for latest data
    const response = await api.get('/metrics/fl/rounds', {
      params: {
        limit: limit,
        sort_order: 'desc',
        source: 'fl_server',  // Prefer FL server for latest data
        format: 'summary'
      }
    });

    const rounds = response.data.rounds || [];
    setCache(cacheKey, rounds);
    return rounds;
  } catch (error) {
    console.error('Error fetching latest FL rounds:', error);
    // Fallback to collector data
    try {
      const fallbackResponse = await api.get('/metrics/fl/rounds', {
        params: {
          limit: limit,
          sort_order: 'desc',
          source: 'collector',
          format: 'summary'
        }
      });
      
      const rounds = fallbackResponse.data.rounds || [];
      setCache(cacheKey, rounds);
      return rounds;
    } catch (fallbackError) {
      console.error('Fallback FL rounds fetch also failed:', fallbackError);
      throw error;
    }
  }
};

// Cleanup function to cancel all pending requests
export const cancelAllFLRequests = () => {
  activeRequests.forEach((cancelToken, key) => {
    cancelToken.cancel('Component unmounted or cleanup');
  });
  activeRequests.clear();
  cache.clear(); // Also clear cache on cleanup
};

// Export interface for FL rounds updates (incremental)
export interface FLRoundsUpdate {
  new_rounds: FLMetric[];
  count: number;
  latest_round_collector: number;
  latest_round_fl_server: number;
  since_round: number;
  has_more: boolean;
  timestamp: string;
  events?: any[];
}

// Export interface for FL training status
export interface FLTrainingStatus {
  timestamp: string;
  training_active: boolean;
  current_round: number;
  latest_accuracy: number;
  latest_loss: number;
  connected_clients: number;
  training_complete: boolean;
  data_source: string;
  fl_server_available: boolean;
  collector_monitoring: boolean;
}

export interface FLConfiguration {
  timestamp: string;
  fl_server: {
    model: string;
    dataset: string;
    total_rounds: number;
    current_round: number;
    min_clients: number;
    min_available_clients: number;
    server_host: string;
    server_port: number;
    metrics_port: number;
    training_complete: boolean;
    stay_alive_after_training: boolean;
    source: string;
  };
  policy_engine: {
    policy_allowed: boolean;
    policy_decision: string;
    total_rounds?: number;
    local_epochs?: number;
    batch_size?: number;
    learning_rate?: number;
    min_clients?: number;
    min_available_clients?: number;
    max_clients?: number;
    aggregation_strategy?: string;
    evaluation_strategy?: string;
    privacy_mechanism?: string;
    differential_privacy_epsilon?: number;
    differential_privacy_delta?: number;
    secure_aggregation?: boolean;
    source: string;
  };
  training_parameters: {
    total_rounds: number;
    local_epochs: number;
    batch_size: number;
    learning_rate: number;
    aggregation_strategy: string;
    evaluation_strategy: string;
    privacy_mechanism: string;
    differential_privacy_epsilon?: number;
    differential_privacy_delta?: number;
    secure_aggregation: boolean;
  };
  model_config: {
    model_type?: string;
    input_shape?: number[];
    input_size?: number;
    hidden_sizes?: number[];
    num_classes: number;
    architecture?: string;
    estimated_parameters?: string;
    source: string;
  };
  federation_config: {
    model?: string;
    dataset?: string;
    rounds?: number;
    min_clients?: number;
    min_available_clients?: number;
    stay_alive_after_training?: boolean;
    source?: string;
    timestamp?: string;
  };
  data_sources: string[];
  status: string;
  metadata: {
    execution_time_ms: number;
    data_sources_used: string[];
    config_completeness: string;
    timestamp: string;
    api_version: string;
  };
}

export const getFLRoundsUpdates = async (params: {
  since_round?: number;
  since_timestamp?: string;
  limit?: number;
  include_events?: boolean;
}): Promise<FLRoundsUpdate> => {
  const cacheKey = `updates_${JSON.stringify(params)}`;
  
  // Don't cache updates - always get fresh data
  try {
    const response = await api.get('/metrics/fl/rounds/updates', {
      params: {
        ...params,
        limit: params.limit || 50
      }
    });

    const result: FLRoundsUpdate = {
      new_rounds: response.data.new_rounds || [],
      count: response.data.count || 0,
      latest_round_collector: response.data.latest_round_collector || 0,
      latest_round_fl_server: response.data.latest_round_fl_server || 0,
      since_round: response.data.since_round || 0,
      has_more: response.data.has_more || false,
      timestamp: response.data.timestamp || new Date().toISOString(),
      events: response.data.events || []
    };

    return result;
  } catch (error) {
    console.error('Error fetching FL rounds updates:', error);
    throw error;
  }
};

export const getFLTrainingStatus = async (): Promise<FLTrainingStatus> => {
  const cacheKey = 'fl_training_status';
  
  // Check cache first
  const cached = getFromCache(cacheKey);
  if (cached) {
    return cached;
  }

  try {
    const response = await fetch('/api/fl-monitoring/metrics/fl/status');
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data: FLTrainingStatus = await response.json();
    
    // Cache the result
    setCache(cacheKey, data);
    
    return data;
  } catch (error) {
    console.error('Error fetching FL training status:', error);
    throw error;
  }
};

export const getFLConfiguration = async (): Promise<FLConfiguration> => {
  const cacheKey = `fl_config`;
  const cached = getFromCache(cacheKey) || getFromLocalStorage(cacheKey);
  if (cached) {
    return cached;
  }

  try {
    // Use the proper config endpoint that's now available
    console.log('Fetching FL configuration from /api/fl/config endpoint');
    const response = await api.get('/fl/config');
    
    if (!response.data) {
      throw new Error('No configuration data received');
    }
    
    const config: FLConfiguration = response.data;
    
    // Validate that the response has the expected structure
    const requiredSections: (keyof FLConfiguration)[] = ['fl_server', 'policy_engine', 'training_parameters', 'model_config', 'federation_config'];
    for (const section of requiredSections) {
      if (!config[section]) {
        console.warn(`Missing section '${section}' in FL configuration response`);
        (config as any)[section] = {};
      }
    }
    
    // Ensure metadata exists
    if (!config.metadata) {
      config.metadata = {
        execution_time_ms: 0,
        data_sources_used: ['dashboard_backend'],
        config_completeness: 'unknown',
        timestamp: new Date().toISOString(),
        api_version: '2.0'
      };
    }
    
    console.log(`FL configuration retrieved successfully with status: ${config.status}`);
    console.log(`Data sources used: ${config.data_sources?.join(', ') || 'unknown'}`);
    console.log(`Configuration completeness: ${config.metadata.config_completeness}`);
    
    setCache(cacheKey, config);
    setLocalStorage(cacheKey, config);
    return config;

  } catch (error) {
    console.error('Failed to fetch FL configuration from endpoint, falling back to derived config:', error);
    
    // Fallback: Try to build configuration from available data
    try {
      const [statusResponse, roundsResponse] = await Promise.allSettled([
        axios.get(`${BASE_URL}/metrics/fl/status`),
        axios.get(`${BASE_URL}/metrics/fl/rounds?limit=5`)
      ]);

      let status = null;
      let rounds = [];

      if (statusResponse.status === 'fulfilled' && statusResponse.value.data) {
        status = statusResponse.value.data;
      }

      if (roundsResponse.status === 'fulfilled' && roundsResponse.value.data) {
        rounds = roundsResponse.value.data.rounds || [];
      }

      // Build a configuration object from available data with proper defaults
      const derivedConfig: FLConfiguration = {
        timestamp: new Date().toISOString(),
        fl_server: {
          model: status?.model || 'Configuration Pending',
          dataset: status?.dataset || 'Configuration Pending',
          total_rounds: status?.max_rounds || 0,
          current_round: status?.current_round || 0,
          min_clients: 1,
          min_available_clients: 1,
          server_host: 'fl-server',
          server_port: 8081,
          metrics_port: 8081,
          training_complete: status?.training_complete || false,
          stay_alive_after_training: true,
          source: 'derived_from_status'
        },
        policy_engine: {
          policy_allowed: true,
          policy_decision: 'allow',
          source: 'default_policy'
        },
        training_parameters: {
          total_rounds: status?.max_rounds || 0,
          local_epochs: 1,
          batch_size: 32,
          learning_rate: 0.01,
          aggregation_strategy: 'fedavg',
          evaluation_strategy: 'server',
          privacy_mechanism: 'none',
          secure_aggregation: false
        },
        model_config: {
          model_type: status?.model || 'pending',
          num_classes: 10,
          source: 'estimated_config'
        },
        federation_config: {
          model: status?.model || 'Configuration Pending',
          dataset: status?.dataset || 'Configuration Pending',
          rounds: status?.max_rounds || 0,
          min_clients: 1,
          min_available_clients: 1,
          stay_alive_after_training: true,
          source: 'derived_from_status',
          timestamp: new Date().toISOString()
        },
        data_sources: ['status_derived', 'estimated_values'],
        status: status?.fl_server_available ? 'partial_config' : 'config_unavailable',
        metadata: {
          execution_time_ms: 0,
          data_sources_used: ['status_derived'],
          config_completeness: 'partial',
          timestamp: new Date().toISOString(),
          api_version: '2.0'
        }
      };

      console.warn('Using derived configuration built from available status data');
      setCache(cacheKey, derivedConfig);
      setLocalStorage(cacheKey, derivedConfig);
      return derivedConfig;

    } catch (fallbackError) {
      console.error('Failed to build derived configuration:', fallbackError);
      
      // Return minimal default configuration as last resort
      const defaultConfig: FLConfiguration = {
        timestamp: new Date().toISOString(),
        fl_server: {
          model: 'Configuration Unavailable',
          dataset: 'Configuration Unavailable',
          total_rounds: 0,
          current_round: 0,
          min_clients: 1,
          min_available_clients: 1,
          server_host: 'fl-server',
          server_port: 8081,
          metrics_port: 8081,
          training_complete: false,
          stay_alive_after_training: true,
          source: 'default_config'
        },
        policy_engine: {
          policy_allowed: false,
          policy_decision: 'unknown',
          source: 'default_config'
        },
        training_parameters: {
          total_rounds: 0,
          local_epochs: 1,
          batch_size: 32,
          learning_rate: 0.01,
          aggregation_strategy: 'fedavg',
          evaluation_strategy: 'server',
          privacy_mechanism: 'none',
          secure_aggregation: false
        },
        model_config: {
          model_type: 'unknown',
          num_classes: 10,
          source: 'default_config'
        },
        federation_config: {
          model: 'Configuration Unavailable',
          dataset: 'Configuration Unavailable',
          rounds: 0,
          min_clients: 1,
          min_available_clients: 1,
          stay_alive_after_training: true,
          source: 'default_config',
          timestamp: new Date().toISOString()
        },
        data_sources: ['default_config'],
        status: 'config_unavailable',
        metadata: {
          execution_time_ms: 0,
          data_sources_used: ['default_config'],
          config_completeness: 'minimal',
          timestamp: new Date().toISOString(),
          api_version: '2.0'
        }
      };

      console.warn('Using minimal default configuration');
      setCache(cacheKey, defaultConfig);
      setLocalStorage(cacheKey, defaultConfig);
      return defaultConfig;
    }
  }
};

// Enhanced version of getFLRoundsWithFilters that uses the new API
export const getFLRoundsWithFiltersEnhanced = async (params: {
  start_round?: number;
  end_round?: number;
  limit?: number;
  offset?: number;
  min_accuracy?: number;
  max_accuracy?: number;
  source?: 'collector' | 'fl_server' | 'both';
  format?: 'detailed' | 'summary';
  sort_order?: 'asc' | 'desc';
  since_round?: number;
}): Promise<{
  rounds: FLMetric[];
  total_rounds: number;
  returned_rounds: number;
  latest_round: number;
  pagination: {
    limit: number;
    offset: number;
    has_more: boolean;
  };
  filters: any;
  sources_used: {
    fl_server_rounds: number;
    collector_rounds: number;
    merged_rounds: number;
  };
}> => {
  const cacheKey = `enhanced_${JSON.stringify(params)}`;
  
  // Only cache if not requesting recent data
  const shouldCache = !params.since_round && (params.offset || 0) === 0 && (params.limit || 1000) <= 100;
  
  if (shouldCache) {
    const cached = getFromCache(cacheKey);
    if (cached) {
      return cached;
    }
  }

  try {
    const response = await api.get('/metrics/fl/rounds', {
      params: {
        ...params,
        source: params.source || 'both',
        format: params.format || 'detailed',
        sort_order: params.sort_order || 'asc'
      }
    });

    const result = {
      rounds: response.data.rounds || [],
      total_rounds: response.data.total_rounds || 0,
      returned_rounds: response.data.returned_rounds || 0,
      latest_round: response.data.latest_round || 0,
      pagination: response.data.pagination || {
        limit: params.limit || 1000,
        offset: params.offset || 0,
        has_more: false
      },
      filters: response.data.filters || {},
      sources_used: response.data.sources_used || {
        fl_server_rounds: 0,
        collector_rounds: 0,
        merged_rounds: 0
      }
    };

    if (shouldCache) {
      setCache(cacheKey, result);
    }

    return result;
  } catch (error) {
    console.error('Error fetching enhanced FL rounds:', error);
    throw error;
  }
};

// Real-time polling for training updates
class FLRealTimePoller {
  private isPolling = false;
  private pollingInterval: NodeJS.Timeout | null = null;
  private lastRound = 0;
  private subscribers = new Set<(update: FLRoundsUpdate) => void>();
  private statusSubscribers = new Set<(status: FLTrainingStatus) => void>();
  private pollInterval = 3000; // 3 seconds for active training

  startPolling(initialRound: number = 0) {
    if (this.isPolling) {
      return;
    }

    this.isPolling = true;
    this.lastRound = initialRound;
    console.log(`FL Real-time poller: Starting with round ${initialRound}`);

    this.pollingInterval = setInterval(async () => {
      try {
        // Get status first to check if training is active
        const status = await getFLTrainingStatus();
        
        // Notify status subscribers
        this.statusSubscribers.forEach(callback => {
          try {
            callback(status);
          } catch (error) {
            console.error('Error in status subscriber callback:', error);
          }
        });

        // If training is active, check for new rounds
        if (status.training_active || status.current_round > this.lastRound) {
          const updates = await getFLRoundsUpdates({
            since_round: this.lastRound,
            limit: 20,
            include_events: true
          });

          if (updates.count > 0) {
            this.lastRound = Math.max(this.lastRound, updates.latest_round_collector, updates.latest_round_fl_server);
            
            // Notify subscribers
            this.subscribers.forEach(callback => {
              try {
                callback(updates);
              } catch (error) {
                console.error('Error in subscriber callback:', error);
              }
            });
            
            console.log(`FL Real-time poller: Got ${updates.count} new rounds, latest: ${this.lastRound}`);
          }
        }

        // Adjust polling interval based on training activity
        if (status.training_active) {
          this.pollInterval = 2000; // Fast polling during training
        } else if (status.training_complete) {
          this.pollInterval = 10000; // Slow polling after completion
        } else {
          this.pollInterval = 5000; // Medium polling for other states
        }

      } catch (error) {
        console.error('FL Real-time poller error:', error);
      }
    }, this.pollInterval);
  }

  stopPolling() {
    if (this.pollingInterval) {
      clearInterval(this.pollingInterval);
      this.pollingInterval = null;
    }
    this.isPolling = false;
    console.log('FL Real-time poller: Stopped');
  }

  subscribe(callback: (update: FLRoundsUpdate) => void): () => void {
    this.subscribers.add(callback);
    return () => this.subscribers.delete(callback);
  }

  subscribeToStatus(callback: (status: FLTrainingStatus) => void): () => void {
    this.statusSubscribers.add(callback);
    return () => this.statusSubscribers.delete(callback);
  }

  updateLastRound(round: number) {
    this.lastRound = Math.max(this.lastRound, round);
  }

  isActive() {
    return this.isPolling;
  }

  getStatus() {
    return {
      isPolling: this.isPolling,
      lastRound: this.lastRound,
      pollInterval: this.pollInterval,
      subscribers: this.subscribers.size,
      statusSubscribers: this.statusSubscribers.size
    };
  }
}

// Export singleton poller instance
export const flRealTimePoller = new FLRealTimePoller();

// Enhanced initialization with real-time polling option
export const initFLMonitoringWithPoller = (startPolling: boolean = false, initialRound: number = 0) => {
  // Initialize WebSocket for real-time updates (if available)
  initFLWebSocket();

  // Optionally start polling for guaranteed updates
  if (startPolling) {
    flRealTimePoller.startPolling(initialRound);
  }
};

// Cleanup function that handles both WebSocket and polling
export const cleanupFLMonitoring = () => {
  // Stop polling
  flRealTimePoller.stopPolling();
  
  // Disconnect WebSocket
  disconnectFLWebSocket();
  
  // Cancel all pending requests
  cancelAllFLRequests();
  
  console.log('FL monitoring cleanup completed');
};