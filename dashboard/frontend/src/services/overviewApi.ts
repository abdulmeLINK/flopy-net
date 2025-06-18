import api from './api';
import axios from 'axios';

// Reduced cache for better real-time updates but still responsive
const CACHE_DURATION = 10000; // 10 seconds cache
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
  if (cache.size > 20) {
    const oldestKey = Array.from(cache.keys())[0];
    cache.delete(oldestKey);
  }
};

// Simplified localStorage for critical data only
const getFromLocalStorage = (key: string) => {
  try {
    const cached = localStorage.getItem(`overview_${key}`);
    if (cached) {
      const parsed = JSON.parse(cached);
      // Use longer TTL for localStorage (30 seconds)
      if (Date.now() - parsed.timestamp < 30000) {
        return parsed.data;
      }
      localStorage.removeItem(`overview_${key}`);
    }
  } catch (error) {
    console.warn('Failed to get from localStorage:', error);
  }
  return null;
};

const setLocalStorage = (key: string, data: any) => {
  try {
    localStorage.setItem(`overview_${key}`, JSON.stringify({
      data,
      timestamp: Date.now()
    }));
  } catch (error) {
    console.warn('Failed to set localStorage:', error);
  }
};

// Enhanced retry logic with exponential backoff
const retryWithBackoff = async <T>(
  fn: () => Promise<T>,
  maxRetries: number = 3,
  baseDelay: number = 1000
): Promise<T> => {
  let lastError: any;
  
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;
      
      if (attempt === maxRetries) {
        break;
      }
      
      // Only retry on network/timeout errors, not 4xx errors
      if (axios.isAxiosError(error)) {
        const shouldRetry = 
          error.code === 'ECONNABORTED' || // Timeout
          error.code === 'ECONNRESET' ||   // Connection reset
          error.code === 'ECONNREFUSED' || // Connection refused
          error.code === 'ENOTFOUND' ||    // DNS resolution failed
          (error.response && error.response.status >= 500); // Server errors
        
        if (!shouldRetry) {
          break; // Don't retry client errors (4xx)
        }
      }
      
      const delay = baseDelay * Math.pow(2, attempt);
      console.log(`Attempt ${attempt + 1} failed, retrying in ${delay}ms...`);
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }
  
  throw lastError;
};

// Create axios instance with better timeout settings
const overviewApi = axios.create({
  timeout: 8000, // 8 seconds - more reasonable for potential network issues
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request/response interceptors for better error handling
overviewApi.interceptors.request.use(
  (config) => {
    console.log(`Making request to: ${config.url}`);
    return config;
  },
  (error) => Promise.reject(error)
);

overviewApi.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error(`Request failed:`, {
      url: error.config?.url,
      status: error.response?.status,
      message: error.message,
      code: error.code
    });
    return Promise.reject(error);
  }
);

export interface FLStatus {
  round: number;
  clients_connected: number;
  accuracy: number;
  loss: number;
  status: string;
  error?: string;
}

export interface NetworkStatus {
  nodes_count: number;
  links_count: number;
  avg_latency: number;
  packet_loss_percent: number;
  bandwidth_utilization: number;
  sdn_status: string;
  switches_count: number;
  total_flows: number;
  active_nodes: number;
  stopped_nodes: number;
  status: string;
  error?: string;
  // Enhanced metrics from the new performance endpoint
  bandwidth?: {
    current_total_bps: number;
    current_average_bps: number;
    active_ports: number;
    peak_bandwidth_bps: number;
  };
  latency?: {
    average_ms: number;
    min_ms: number;
    max_ms: number;
  };
  flows?: {
    total: number;
    active: number;
  };
  ports?: {
    total: number;
    up: number;
    errors: number;
  };
  health_score?: number;
  totals?: {
    bytes_transferred: number;
    megabytes_transferred: number;
    gigabytes_transferred: number;
    packets_transferred: number;
    flows_created: number;
    total_errors: number;
    uptime_seconds: number;
    uptime_minutes: number;
    uptime_hours: number;
  };
  rates?: {
    bytes_per_second: number;
    packets_per_second: number;
    flows_per_hour: number;
  };
}

export interface PolicyStatus {
  active_policies: number;
  decisions_last_hour: number;
  allow_count_last_hour?: number;
  deny_count_last_hour?: number;
  avg_decision_time_ms: number;
  status: string;
  error?: string;
}

export interface EventsSummary {
  total_count: number;
  error_count: number;
  warning_count: number;
  info_count: number;
  status: string;
  error?: string;
}

export interface SystemSummary {
  fl_status: FLStatus;
  network_status: NetworkStatus;
  policy_status: PolicyStatus;
  events: EventsSummary;
}

/**
 * Get FL status with improved error handling
 */
export const getFLStatus = async (): Promise<FLStatus> => {
  const cacheKey = 'fl-status';
  
  // Try cache first for responsive UI
  const cached = getFromCache(cacheKey);
  if (cached) {
    return cached;
  }
  
  return retryWithBackoff(async () => {
    const response = await overviewApi.get('/api/overview/fl-status');
    const data = response.data;
    setCache(cacheKey, data);
    setLocalStorage(cacheKey, data);
    return data;
  });
};

/**
 * Get network status with improved error handling
 */
export const getNetworkStatus = async (): Promise<NetworkStatus> => {
  const cacheKey = 'network-status';
  
  // Try cache first for responsive UI
  const cached = getFromCache(cacheKey);
  if (cached) {
    return cached;
  }
    return retryWithBackoff(async () => {
    const response = await overviewApi.get('/api/overview/network-status');
    const data = response.data;
      // Map the flat API response structure to the expected NetworkStatus interface
    const transformedData: NetworkStatus = {
      nodes_count: data.nodes_count || 0,
      links_count: data.links_count || 0,
      avg_latency: data.avg_latency || 0,
      packet_loss_percent: data.packet_loss_percent || 0,
      bandwidth_utilization: data.bandwidth_utilization || 0,
      sdn_status: data.sdn_status || 'unknown',
      switches_count: data.switches_count || 0,
      total_flows: data.total_flows || 0,
      active_nodes: data.active_nodes || 0,
      stopped_nodes: data.stopped_nodes || 0,
      status: data.status || 'unknown',
      health_score: data.health_score || 0,
      // Include additional metrics if available
      bandwidth: data.bandwidth,
      latency: data.latency,
      flows: data.flows,
      ports: data.ports,
      totals: data.totals,
      rates: data.rates
    };
    
    setCache(cacheKey, transformedData);
    setLocalStorage(cacheKey, transformedData);
    return transformedData;
  });
};

/**
 * Get policy status with improved error handling
 */
export const getPolicyStatus = async (): Promise<PolicyStatus> => {
  const cacheKey = 'policy-status';
  
  // Try cache first for responsive UI
  const cached = getFromCache(cacheKey);
  if (cached) {
    return cached;
  }
  
  return retryWithBackoff(async () => {
    const response = await overviewApi.get('/api/overview/policy-status');
    const data = response.data;
    setCache(cacheKey, data);
    setLocalStorage(cacheKey, data);
    return data;
  });
};

/**
 * Get events summary with improved error handling
 */
export const getEventsSummary = async (): Promise<EventsSummary> => {
  const cacheKey = 'events-summary';
  
  // Try cache first for responsive UI
  const cached = getFromCache(cacheKey);
  if (cached) {
    return cached;
  }
  
  return retryWithBackoff(async () => {
    const response = await overviewApi.get('/api/overview/events-summary');
    const data = response.data;
    setCache(cacheKey, data);
    setLocalStorage(cacheKey, data);
    return data;
  });
};

/**
 * Get system overview summary data (backward compatibility)
 */
export const getSystemSummary = async (): Promise<SystemSummary> => {
  try {
    const response = await api.get('/overview/summary', { timeout: 15000 });
    return response.data;
  } catch (error) {
    console.error('Failed to fetch system summary:', error);
    // Don't return mock data - let the error bubble up so we can see what's wrong
    throw error;
  }
}; 