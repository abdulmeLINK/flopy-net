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
import api from './api'; // Use the shared axios instance

// Base URL from environment variable or default to relative path
// const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || '/api'; // Remove this line
// const COLLECTOR_API_BASE_URL = process.env.COLLECTOR_URL; // Reverted change

// Types
export interface MetricQuery {
  metric_types: string[];
  start_time: string;
  end_time: string;
  components?: string[];
  aggregation: 'avg' | 'min' | 'max' | 'sum' | 'count';
  interval: string;
}

export interface MetricDataPoint {
  metric_type: string;
  component: string;
  timestamp: string;
  value: number;
  metadata?: Record<string, any>;
}

/**
 * Get available metric types that can be queried
 */
export async function getMetricTypes(): Promise<string[]> {
  try {
    const response = await api.get('/metrics/types'); // Use shared api instance
    return response.data;
  } catch (error) {
    console.error('Error fetching metric types:', error);
    throw error;
  }
}

/**
 * Get available components that can be filtered on
 */
export async function getMetricComponents(): Promise<string[]> {
  try {
    const response = await api.get('/metrics/components'); // Use shared api instance
    return response.data;
  } catch (error) {
    console.error('Error fetching metric components:', error);
    throw error;
  }
}

/**
 * Query metrics with advanced filtering options
 */
export async function queryMetrics(query: MetricQuery): Promise<MetricDataPoint[]> {
  try {
    const response = await api.post('/metrics/query', query); // Use shared api instance
    return response.data.metrics;
  } catch (error) {
    console.error('Error querying metrics:', error);
    throw error;
  }
}

/**
 * Export metrics data as CSV
 */
export async function exportMetricsData(query: MetricQuery): Promise<Blob> {
  try {
    const response = await api.post('/metrics/export', query, { // Use shared api instance
      responseType: 'blob'
    });
    return response.data;
  } catch (error) {
    console.error('Error exporting metrics data:', error);
    throw error;
  }
}

/**
 * Get metric data for a specific time range and metric type
 */
export async function getMetricTimeRange(
  metricType: string,
  startTime: string,
  endTime: string,
  component?: string
): Promise<MetricDataPoint[]> {
  try {
    const params: any = {
      metric_type: metricType,
      start_time: startTime,
      end_time: endTime
    };

    if (component) {
      params.component = component;
    }

    const response = await api.get('/metrics/time-range', { params }); // Use shared api instance
    return response.data;
  } catch (error) {
    console.error('Error fetching metric time range:', error);
    throw error;
  }
}

/**
 * Get the latest metrics for all types or a specific type
 */
export async function getLatestMetrics(metricType?: string): Promise<MetricDataPoint[]> {
  try {
    const params: any = {};
    if (metricType) {
      params.metric_type = metricType;
    }

    const response = await api.get('/metrics/latest', { params }); // Use shared api instance
    return response.data;
  } catch (error) {
    console.error('Error fetching latest metrics:', error);
    throw error;
  }
} 