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
import api from './api';

export interface NetworkNode {
  id: string;
  name: string;
  node_type?: string;
  type?: string;
  status: 'started' | 'stopped' | 'suspended' | 'active' | 'unknown';
  x: number;
  y: number;
  z?: number;
  console?: number;
  console_host?: string;
  properties: {
    ip_address?: string;
    symbol?: string;
    [key: string]: any;
  };
  source?: 'gns3' | 'sdn';
}

export interface NetworkSwitch {
  id: string;
  dpid: number;
  type: 'switch';
  status: 'active' | 'inactive';
  ports: any[];
  flows: number;
  description: any;
}

export interface NetworkHost {
  id: string;
  mac: string;
  ipv4: string[];
  dpid: string;
  port: string;
  type: 'host';
  status: 'active' | 'inactive';
}

export interface NetworkLink {
  id: string;
  link_type?: string;
  source_node_id?: string;
  target_node_id?: string;
  source_dpid?: string;
  target_dpid?: string;
  source_port: number | string;
  target_port: number | string;
  bandwidth?: number;
  latency_ms?: number;
  status?: 'active' | 'inactive';
  properties?: {
    latency_ms?: number;
    bandwidth_mbps?: number;
    packet_loss_percent?: number;
    [key: string]: any;
  };
  source?: 'gns3' | 'sdn';
}

export interface NetworkTopology {
  nodes: NetworkNode[];
  links: NetworkLink[];
  switches?: NetworkSwitch[];
  hosts?: NetworkHost[];
  statistics?: {
    total_nodes: number;
    total_links: number;
    total_switches: number;
    total_hosts: number;
    gns3_links: number;
    sdn_links: number;
  };
  project_info?: {
    name: string;
    id: string;
    status: string;
  };
  metrics?: {
    sdn_status: string;
    switches_count: number;
    total_flows: number;
    total_ports: number;
    avg_latency_ms: number;
    packet_loss_percent: number;
    bandwidth_utilization_percent: number;
  };
  timestamp?: string;
  collection_time?: number;
}

export type TopologySource = 'gns3' | 'sdn' | 'all';

export interface NetworkMetrics {
  timestamp: string;
  node_id?: string;
  link_id?: string;
  metric_type: string;
  value: number;
  unit: string;
}

export interface NetworkHealth {
  health_score: number;
  status: 'excellent' | 'good' | 'fair' | 'poor' | 'critical';
  color: 'success' | 'warning' | 'error';
  issues: string[];
  recommendations: string[];
}

export interface NetworkStatus {
  status: string;
  gns3_status: {
    project_name?: string;
    project_status?: string;
    connection_status: string;
  };
  topology: {
    nodes_total: number;
    links_total: number;
    nodes_by_status: Record<string, number>;
    nodes_by_type: Record<string, number>;
  };
  sdn_controller: {
    status: string;
    switches_count: number;
    total_flows: number;
    total_ports: number;
    error?: string;
  };
  performance: {
    avg_latency_ms: number;
    packet_loss_percent: number;
    bandwidth_utilization_percent: number;
  };
  health: NetworkHealth;
  last_updated?: number;
  details: Record<string, any>;
}

export interface NetworkMetricsSummary {
  time_period_hours: number;
  data_points: number;
  latency: {
    min: number;
    max: number;
    avg: number;
  };
  packet_loss: {
    min: number;
    max: number;
    avg: number;
  };
  topology: {
    nodes: {
      min: number;
      max: number;
      avg: number;
    };
    links: {
      min: number;
      max: number;
      avg: number;
    };
  };
  availability: {
    uptime_percent: number;
    connected_periods: number;
    total_periods: number;
  };
  last_updated?: number;
}

// Enhanced performance metrics from SDN controller - matches actual backend response
export interface EnhancedPerformanceMetrics {
  collection_timestamp: number;
  timestamp: number;
  source: string;
  bandwidth: {
    active_ports: number;
    current_average_bps: number;
    current_total_bps: number;
    peak_bandwidth_bps: number;
  };
  latency: {
    average_ms: number;
    min_ms: number;
    max_ms: number;
  };
  flows: {
    total: number;
    active: number;
  };
  ports: {
    total: number;
    up: number;
    errors: number;
  };
  network_health: {
    score: number;
    status: string;
    factors: {
      bandwidth_impact: number;
      error_impact: number;
      flow_impact: number;
      latency_impact: number;
    };
  };
  rates: {
    bytes_per_second: number;
    flows_per_hour: number;
    packets_per_second: number;
  };
  totals: {
    bytes_transferred: number;
    flows_created: number;
    gigabytes_transferred: number;
    megabytes_transferred: number;
    packets_transferred: number;
    total_errors: number;
    uptime_hours: number;
    uptime_minutes: number;
    uptime_seconds: number;
  };
  health_score: number;
  packet_loss: number;
}

/**
 * Get active network topology
 */
export const getNetworkTopology = async (
  source: TopologySource = 'all',
  format: 'detailed' | 'summary' = 'detailed',
  includeMetrics: boolean = true
): Promise<NetworkTopology> => {
  try {
    const params = new URLSearchParams({
      source,
      format,
      include_metrics: includeMetrics.toString()
    });
    const response = await api.get(`/network/topology/active?${params}`);
    return response.data;
  } catch (error) {
    console.error('Failed to fetch network topology:', error);
    // No fallbacks as per project rules
    throw error;
  }
};

/**
 * Get live network topology with real-time updates
 */
export const getLiveNetworkTopology = async (): Promise<NetworkTopology> => {
  try {
    const response = await api.get('/network/topology/live');
    return response.data;
  } catch (error) {
    console.error('Failed to fetch live network topology:', error);
    throw error;
  }
};

/**
 * Get network metrics
 */
export const getNetworkMetrics = async (
  params: {
    start_time?: string;
    end_time?: string;
    node_id?: string;
    link_id?: string;
    metric_type?: string;
    limit?: number;
  } = {}
): Promise<NetworkMetrics[]> => {
  try {
    const response = await api.get('/network/metrics', { params });
    return response.data;
  } catch (error) {
    console.error('Failed to fetch network metrics:', error);
    // No fallbacks as per project rules
    throw error;
  }
};

/**
 * Get node details
 */
export const getNodeDetails = async (nodeId: string): Promise<NetworkNode> => {
  try {
    const response = await api.get(`/network/topology/active/nodes/${nodeId}`);
    return response.data;
  } catch (error) {
    console.error(`Failed to fetch node details for ${nodeId}:`, error);
    throw error;
  }
};

/**
 * Get link details
 */
export const getLinkDetails = async (linkId: string): Promise<NetworkLink> => {
  try {
    const response = await api.get(`/network/topology/active/links/${linkId}`);
    return response.data;
  } catch (error) {
    console.error(`Failed to fetch link details for ${linkId}:`, error);
    throw error;
  }
};

/**
 * Get comprehensive network status including health scoring
 */
export const getNetworkStatus = async (): Promise<NetworkStatus> => {
  try {
    const response = await api.get('/network/status');
    return response.data;
  } catch (error) {
    console.error('Failed to fetch network status:', error);
    throw error;
  }
};

/**
 * Get network metrics summary over a time period
 */
export const getNetworkMetricsSummary = async (hours: number = 24): Promise<NetworkMetricsSummary> => {
  try {
    const response = await api.get('/network/metrics/summary', { 
      params: { hours } 
    });
    return response.data;
  } catch (error) {
    console.error('Failed to fetch network metrics summary:', error);
    throw error;
  }
};

/**
 * Get enhanced performance metrics from SDN controller
 */
export const getEnhancedPerformanceMetrics = async (): Promise<EnhancedPerformanceMetrics> => {
  try {
    const response = await api.get('/network/metrics');
    return response.data;
  } catch (error) {
    console.error('Failed to fetch enhanced performance metrics:', error);
    throw error;
  }
};