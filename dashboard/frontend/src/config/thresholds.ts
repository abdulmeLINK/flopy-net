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
/**
 * Dashboard Thresholds Configuration
 * 
 * This file contains all configurable thresholds and limits used throughout the dashboard
 * to replace hardcoded values and make the dashboard more flexible for different scenarios.
 */

// Extend ImportMeta interface to include env
declare global {
  interface ImportMeta {
    env: Record<string, any>;
  }
}

// Environment variables with fallbacks to defaults
const getEnvNumber = (key: string, defaultValue: number): number => {
  const value = import.meta.env?.[key];
  return value ? Number(value) : defaultValue;
};

const getEnvString = (key: string, defaultValue: string): string => {
  return import.meta.env?.[key] || defaultValue;
};

// FL Training Thresholds
export const FL_THRESHOLDS = {
  accuracy: {
    good: getEnvNumber('VITE_FL_ACCURACY_GOOD_THRESHOLD', 80), // 80%
    warning: getEnvNumber('VITE_FL_ACCURACY_WARNING_THRESHOLD', 50), // 50%
  },
  loss: {
    good: getEnvNumber('VITE_FL_LOSS_GOOD_THRESHOLD', 0.1), // 0.1
    warning: getEnvNumber('VITE_FL_LOSS_WARNING_THRESHOLD', 0.5), // 0.5
    isHigherBetter: false,
  },
  clients: {
    warningThreshold: getEnvNumber('VITE_FL_CLIENTS_WARNING_THRESHOLD', 0), // Warn if 0 clients
  },
} as const;

// Network Performance Thresholds
export const NETWORK_THRESHOLDS = {
  latency: {
    good: getEnvNumber('VITE_NETWORK_LATENCY_GOOD_THRESHOLD', 10), // 10ms
    warning: getEnvNumber('VITE_NETWORK_LATENCY_WARNING_THRESHOLD', 50), // 50ms
    isHigherBetter: false,
  },
  packetLoss: {
    good: getEnvNumber('VITE_NETWORK_PACKET_LOSS_GOOD_THRESHOLD', 1), // 1%
    warning: getEnvNumber('VITE_NETWORK_PACKET_LOSS_WARNING_THRESHOLD', 5), // 5%
    isHigherBetter: false,
  },
  bandwidth: {
    good: getEnvNumber('VITE_NETWORK_BANDWIDTH_GOOD_THRESHOLD', 80), // 80%
    warning: getEnvNumber('VITE_NETWORK_BANDWIDTH_WARNING_THRESHOLD', 95), // 95%
    isHigherBetter: false, // High bandwidth utilization can be bad
  },
  nodes: {
    warningThreshold: getEnvNumber('VITE_NETWORK_NODES_WARNING_THRESHOLD', 0), // Warn if 0 nodes
  },
} as const;

// Policy Engine Thresholds
export const POLICY_THRESHOLDS = {
  decisionTime: {
    good: getEnvNumber('VITE_POLICY_DECISION_TIME_GOOD_THRESHOLD', 1), // 1ms
    warning: getEnvNumber('VITE_POLICY_DECISION_TIME_WARNING_THRESHOLD', 10), // 10ms
    isHigherBetter: false,
  },
  evaluationTime: {
    warning: getEnvNumber('VITE_POLICY_EVALUATION_TIME_WARNING_THRESHOLD', 100), // 100ms
    error: getEnvNumber('VITE_POLICY_EVALUATION_TIME_ERROR_THRESHOLD', 1000), // 1000ms
  },
  complexity: {
    warning: getEnvNumber('VITE_POLICY_COMPLEXITY_WARNING_THRESHOLD', 10),
  },
  rules: {
    many: getEnvNumber('VITE_POLICY_RULES_MANY_THRESHOLD', 20),
    some: getEnvNumber('VITE_POLICY_RULES_SOME_THRESHOLD', 10),
  },
  denialRate: {
    warning: getEnvNumber('VITE_POLICY_DENIAL_RATE_WARNING_THRESHOLD', 20), // 20%
    error: getEnvNumber('VITE_POLICY_DENIAL_RATE_ERROR_THRESHOLD', 50), // 50%
  },
} as const;

// API and UI Limits
export const API_LIMITS = {
  defaultPageSize: getEnvNumber('VITE_DEFAULT_PAGE_SIZE', 100),
  maxPageSize: getEnvNumber('VITE_MAX_PAGE_SIZE', 500),
  maxFlRounds: getEnvNumber('VITE_MAX_FL_ROUNDS_LIMIT', 5000),
  defaultEventsLimit: getEnvNumber('VITE_DEFAULT_EVENTS_LIMIT', 1000),
  maxClientErrors: getEnvNumber('VITE_MAX_CLIENT_ERRORS_STORED', 20),
} as const;

// Timing and Intervals
export const TIMING = {
  websocketReconnectDelay: getEnvNumber('VITE_WEBSOCKET_RECONNECT_DELAY', 15), // Reduced for faster reconnect
  pollingInterval: getEnvNumber('VITE_POLLING_INTERVAL', 10), // Reduced for more responsive updates
  flRefreshInterval: getEnvNumber('VITE_FL_REFRESH_INTERVAL', 15), // Reduced
  overviewUpdateInterval: getEnvNumber('VITE_OVERVIEW_UPDATE_INTERVAL', 20), // Reduced
  apiRetryDelay: getEnvNumber('VITE_API_RETRY_DELAY', 15), // Reduced for faster recovery
  httpTimeout: getEnvNumber('VITE_HTTP_TIMEOUT', 30), // Increased for stability
} as const;

// Chart and Display Settings
export const DISPLAY = {
  chartDataPoints: getEnvNumber('VITE_CHART_DATA_POINTS', 500),
  tablePageSize: getEnvNumber('VITE_TABLE_PAGE_SIZE', 100),
  maxTablePageSize: getEnvNumber('VITE_MAX_TABLE_PAGE_SIZE', 200),
  metricsWindowSize: getEnvNumber('VITE_METRICS_WINDOW_SIZE', 300),
  summaryWindowSize: getEnvNumber('VITE_SUMMARY_WINDOW_SIZE', 100),
} as const;

// Helper function to get status indicator color based on thresholds
export const getStatusIndicator = (
  value: number,
  thresholds: { good: number; warning: number; isHigherBetter?: boolean }
): 'success' | 'warning' | 'error' => {
  const { good, warning, isHigherBetter = true } = thresholds;
  
  if (isHigherBetter) {
    if (value >= good) return 'success';
    if (value >= warning) return 'warning';
    return 'error';
  } else {
    if (value <= good) return 'success';
    if (value <= warning) return 'warning';
    return 'error';
  }
};

// Helper function to get FL status color
export const getFLStatusColor = (
  clients: number,
  accuracy: number,
  status: string
): 'success' | 'warning' | 'error' => {
  if (status === 'error') return 'error';
  if (status === 'idle') return 'warning';
  if (status === 'active') {
    if (clients === 0) return 'warning'; // Active but no clients
    if (accuracy < FL_THRESHOLDS.accuracy.warning) return 'error'; // Low accuracy
    if (accuracy < FL_THRESHOLDS.accuracy.good) return 'warning'; // Medium accuracy
    return 'success'; // Good accuracy
  }
  if (status === 'completed') {
    if (accuracy >= FL_THRESHOLDS.accuracy.good) return 'success'; // Good final accuracy
    if (accuracy >= FL_THRESHOLDS.accuracy.warning) return 'warning'; // Decent final accuracy
    return 'error'; // Poor final accuracy
  }
  return 'warning';
};

// Helper function to get network status color
export const getNetworkStatusColor = (
  nodes: number,
  packetLoss: number,
  status: string
): 'success' | 'warning' | 'error' => {
  if (status === 'error') return 'error';
  if (nodes === 0) return 'warning';
  if (packetLoss > NETWORK_THRESHOLDS.packetLoss.warning) return 'error';
  if (packetLoss > NETWORK_THRESHOLDS.packetLoss.good) return 'warning';
  return 'success';
};

export default {
  FL_THRESHOLDS,
  NETWORK_THRESHOLDS,
  POLICY_THRESHOLDS,
  API_LIMITS,
  TIMING,
  DISPLAY,
  getStatusIndicator,
  getFLStatusColor,
  getNetworkStatusColor,
}; 