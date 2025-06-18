import axios from 'axios';

const BASE_URL = '/api/events';

// Reduced caching for better real-time updates
const CACHE_DURATION = 10000; // 10 seconds
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
};

// Utility function to safely convert values to numbers
const safeNumber = (value: any, defaultValue: number = 0): number => {
  const num = Number(value);
  return isNaN(num) ? defaultValue : num;
};

// Simple retry utility
const retryWithBackoff = async <T>(
  fn: () => Promise<T>,
  maxRetries: number = 3,
  baseDelay: number = 1000
): Promise<T> => {
  let lastError: Error;
  
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error as Error;
      
      if (attempt === maxRetries) {
        throw lastError;
      }
      
      const delay = baseDelay * Math.pow(2, attempt);
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }
  
  throw lastError!;
};

// Create axios instance with proper timeout
const eventsApi = axios.create({
  timeout: 8000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add logging for debugging
eventsApi.interceptors.request.use(
  (config) => {
    console.log(`Events API request: ${config.url}`);
    return config;
  },
  (error) => Promise.reject(error)
);

eventsApi.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error(`Events API error:`, error);
    return Promise.reject(error);
  }
);

export interface SystemEvent {
  id?: string;
  timestamp: string;
  level: 'info' | 'warning' | 'error' | 'debug';
  component: string;
  event_type: string;
  message: string;
  details?: any;
}

export interface EventsResponse {
  events: SystemEvent[];
  total: number;
  page?: number;
  page_size?: number;
  has_more?: boolean;
  limit?: number;
  offset?: number;
}

export interface EventsSummary {
  total_count: number;
  error_count: number;
  warning_count: number;
  info_count: number;
  debug_count?: number;
  recent_events?: SystemEvent[];
  by_component?: Record<string, number>;
  by_level?: Record<string, number>;
}

export const getEvents = async (params?: {
  start_time?: string;
  end_time?: string;
  level?: string;
  component?: string;
  page?: number;
  page_size?: number;
  limit?: number;
  offset?: number;
  search?: string;
}): Promise<EventsResponse> => {
  const cacheKey = `events-${JSON.stringify(params)}`;
  
  // Try cache first for responsive UI
  const cached = getFromCache(cacheKey);
  if (cached) {
    return cached;
  }
  
  return retryWithBackoff(async () => {
    // Use the correct /log endpoint
    const response = await eventsApi.get(`${BASE_URL}/log`, { params });
    const data = response.data;
    
    // Ensure we have a proper EventsResponse structure
    const eventsResponse: EventsResponse = {
      events: Array.isArray(data.events) ? data.events : [],
      total: safeNumber(data.total, 0),
      page: safeNumber(data.page, 0),
      page_size: safeNumber(data.page_size || data.limit, params?.limit || 100),
      limit: safeNumber(data.limit, params?.limit || 100),
      offset: safeNumber(data.offset, params?.offset || 0),
      has_more: data.has_more || (data.total > (data.offset || 0) + (data.limit || 100))
    };
    
    setCache(cacheKey, eventsResponse);
    return eventsResponse;
  });
};

export const getEventsSummary = async (timeRange?: string): Promise<EventsSummary> => {
  const cacheKey = `events-summary-${timeRange || 'default'}`;
  
  // Try cache first
  const cached = getFromCache(cacheKey);
  if (cached) {
    return cached;
  }
  
  return retryWithBackoff(async () => {
    const params = timeRange ? { time_range: timeRange } : {};
    const response = await eventsApi.get(`${BASE_URL}/summary`, { params });
    const data = response.data;
    
    // Convert the backend response to expected format
    const summary: EventsSummary = {
      total_count: safeNumber(data.total, 0),
      error_count: safeNumber(data.by_level?.error || data.by_level?.ERROR, 0),
      warning_count: safeNumber(data.by_level?.warning || data.by_level?.WARNING, 0),
      info_count: safeNumber(data.by_level?.info || data.by_level?.INFO, 0),
      debug_count: safeNumber(data.by_level?.debug || data.by_level?.DEBUG, 0),
      by_component: data.by_component || {},
      by_level: data.by_level || {},
      recent_events: []
    };
    
    setCache(cacheKey, summary);
    return summary;
  });
};

// WebSocket URL - ensure this matches your backend configuration
// The /ws prefix is handled by the FastAPI router in main.py for WebSockets
const EVENTS_WEBSOCKET_URL = (() => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const hostname = window.location.hostname;
  // Use the same port as the current page or 8085 as a fallback
  // (8085 is the default frontend port in docker-compose.yml)
  const port = window.location.port || '8085';
  return `${protocol}//${hostname}:${port}/ws/events`;
})();

export interface WebSocketEvent {
  type: string;
  message?: string;
  event?: SystemEvent | any; // Can be a SystemEvent or other event types like client_error
  events?: SystemEvent[]; // For initial batch of events
  timestamp: string;
  container?: string; // For container-specific logs, if ever mixed here
  container_id?: string;
  container_name?: string;
}

export const connectToEventsStream = (
  onEvent: (event: WebSocketEvent) => void,
  onError: (error: Event) => void,
  onConnect: () => void,
  onDisconnect: () => void
): () => void => {
  console.log('Connecting to events WebSocket:', EVENTS_WEBSOCKET_URL);
  
  let reconnectAttempts = 0;
  const maxReconnectAttempts = 5;
  const reconnectDelay = 1000;
  let ws: WebSocket | null = null;
  let reconnectTimer: NodeJS.Timeout | null = null;
  let isClosed = false;

  const connect = () => {
    if (isClosed) return;
    
    ws = new WebSocket(EVENTS_WEBSOCKET_URL);

    ws.onopen = () => {
      console.log('Events WebSocket connected');
      reconnectAttempts = 0;
      onConnect();
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onEvent(data);
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };

    ws.onerror = (error) => {
      console.error('Events WebSocket error:', error);
      onError(error);
    };

    ws.onclose = () => {
      console.log('Events WebSocket closed');
      onDisconnect();
      
      // Attempt to reconnect unless manually closed
      if (!isClosed && reconnectAttempts < maxReconnectAttempts) {
        reconnectAttempts++;
        const delay = reconnectDelay * Math.pow(2, reconnectAttempts - 1);
        console.log(`Attempting to reconnect in ${delay}ms (attempt ${reconnectAttempts})`);
        
        reconnectTimer = setTimeout(() => {
          if (!isClosed) {
            connect();
          }
        }, delay);
      }
    };
  };

  // Initial connection
  connect();

  // Return cleanup function
  return () => {
    isClosed = true;
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
    }
    if (ws) {
      ws.close();
    }
  };
};