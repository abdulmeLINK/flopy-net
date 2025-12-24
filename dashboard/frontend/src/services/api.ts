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

import axios from 'axios';

// Create an axios instance with default configuration
const api = axios.create({
  baseURL: '/api', // This will be prefixed to all relative URLs
  timeout: 30000,   // Increased to 30 seconds for better reliability
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  }
});

// Track API availability with improved backoff
const apiStatus = {
  isAvailable: true,
  retryAfter: 0, // Timestamp when to retry after outage
  outageDetected: false,
  consecutiveFailures: 0,
  maxRetryDelay: 300000, // 5 minutes max
  baseRetryDelay: 5000   // 5 seconds base
};

// Calculate exponential backoff delay
const getRetryDelay = () => {
  const delay = Math.min(
    apiStatus.baseRetryDelay * Math.pow(2, apiStatus.consecutiveFailures),
    apiStatus.maxRetryDelay
  );
  return delay + Math.random() * 1000; // Add jitter
};

// Add a request interceptor to handle authentication if needed
api.interceptors.request.use(
  config => {
    // Check if we're in a known API outage and should avoid the request
    const now = Date.now();
    if (apiStatus.outageDetected && now < apiStatus.retryAfter) {
      // Return a custom error for network issues without making the request
      return Promise.reject({
        isApiUnavailableError: true,
        message: 'API unavailable, request skipped',
        config
      });
    }
    
    // Check for POST requests with missing or invalid data - common source of errors
    if (config.method?.toLowerCase() === 'post') {
      if (!config.data && !config.params) {
        console.warn('POST request with no data detected:', config.url);
      }
    }
    
    // You can add auth tokens here if needed
    return config;
  },
  error => {
    return Promise.reject(error);
  }
);

// Add a response interceptor to handle common error cases
api.interceptors.response.use(
  response => {
    // Reset API availability on successful response
    if (apiStatus.outageDetected) {
      apiStatus.outageDetected = false;
      apiStatus.consecutiveFailures = 0;
      console.log('API connectivity restored');
    }
    return response;
  },
  error => {
    // Check if this is our custom API unavailable error
    if (error.isApiUnavailableError) {
      // Don't log these as they are expected during outages
      console.warn(`Skipped request to ${error.config?.url} - API is unavailable`);
      return Promise.reject(error);
    }
    
    // Add any common error handling here
    if (error.response) {
      // Server responded with a status code outside of 2xx range
      console.error('API Error:', error.response.status, error.response.data);
      
      // Log specific API errors to the backend
      logClientError(new Error(`API Error ${error.response.status}: ${error.config?.url || 'unknown endpoint'}`), {
        type: 'api_error',
        status: error.response.status,
        url: error.config?.url,
        method: error.config?.method,
        responseData: error.response.data,
        endpoint: error.config?.url?.split('?')[0]?.replace(/^\/api\//, '') || 'unknown',
      });
    } else if (error.request) {
      // No response received from server - likely a network issue
      console.error('API Error: No response received');
      
      // Mark API as unavailable with exponential backoff
      apiStatus.outageDetected = true;
      apiStatus.consecutiveFailures++;
      const retryDelay = getRetryDelay();
      apiStatus.retryAfter = Date.now() + retryDelay;
      
      console.log(`API marked unavailable for ${retryDelay/1000}s (failure #${apiStatus.consecutiveFailures})`);
      
      // Log network errors to the backend - but limit volume during outages
      if (apiStatus.consecutiveFailures === 1) {
        logClientError(new Error('API Network Error: No response received'), {
          type: 'network_error',
          url: error.config?.url,
          method: error.config?.method
        });
      }
    } else {
      // Something happened in setting up the request
      console.error('API Error:', error.message);
      
      // Log request setup errors
      logClientError(error, {
        type: 'request_setup_error',
        message: error.message
      });
    }
    
    // Continue with the error
    return Promise.reject(error);
  }
);

/**
 * Log client-side errors to the backend
 * @param error The error object to log
 * @param context Additional context information
 */
export const logClientError = async (
  error: Error, 
  context: Record<string, unknown> = {}
): Promise<void> => {
  try {
    const errorData = {
      message: error.message || 'Unknown error',
      stack: error.stack || '',
      name: error.name,
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      component: context.component || 'unknown',
      additionalData: {
        ...context,
        url: window.location.href,
        pathname: window.location.pathname,
        referrer: document.referrer
      }
    };
    
    // Don't use the main axios instance to avoid infinite loops with error interceptors
    const loggerAxios = axios.create({
      baseURL: '/api',
      timeout: 10000, // Shorter timeout for error logging
    });
    
    // Make sure we're contacting the correct endpoint based on backend route
    await loggerAxios.post('/log/client-error', errorData);
    console.debug('Client error logged to backend');  // Less verbose
  } catch (loggingError) {
    console.error('Failed to log client error to backend');
    
    // Attempt to store the error locally since we couldn't reach the backend
    try {
      const storedErrors = JSON.parse(localStorage.getItem('clientErrors') || '[]');
      const newErrorEntry = {
        message: error.message,
        timestamp: new Date().toISOString(),
        path: window.location.pathname
      };
      localStorage.setItem('clientErrors', JSON.stringify([...storedErrors, newErrorEntry].slice(-20))); // Keep last 20
    } catch (storageError) {
      console.error('Failed to store error in localStorage:', storageError);
    }
  }
};

export default api;