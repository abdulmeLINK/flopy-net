import api from './api';

export interface Policy {
  id: string;
  name: string;
  description?: string;
  type: string;
  rule_type?: string;
  priority: number;
  status: string; // 'active' | 'inactive'
  rules?: PolicyRule[];
  enabled?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface PolicyRule {
  action: string;
  description: string;
  match: Record<string, any>;
  parameters?: Record<string, any>;
}

export interface PolicyRequest {
  id?: string;
  name: string;
  type: string;
  description: string;
  priority: number;
  rules: PolicyRule[];
}

export interface PolicyDecision {
  id: string;
  policy_id: string;
  policy_name: string;
  timestamp: string;
  context: any;
  decision: 'allow' | 'deny' | 'modify';
  result?: boolean | string;
  action_taken: string;
  reason?: string;
  execution_time?: number;
  request_id?: string;
  component?: string;
  metadata?: any;
  
  // Enhanced policy evaluation details
  rule_evaluations?: Array<{
    policy_id: string;
    policy_name: string;
    policy_type: string;
    priority: number;
    rules_evaluated: Array<{
      rule_index: number;
      rule_type: string;
      description?: string;
      matched: boolean;
      action: string;
      reason: string;
      parameters: any;
      match_details?: Array<{
        field: string;
        expected: any;
        actual: any;
        matched: boolean;
        reason: string;
      }>;
      evaluation_time_ms: number;
    }>;
    matched_rules: any[];
    actions_applied: any[];
    evaluation_time_ms: number;
    result: string;
  }>;
  
  applied_actions?: Array<{
    action: string;
    policy_id: string;
    policy_name: string;
    rule_index: number;
    reason: string;
    parameters: any;
    match_details?: any[];
  }>;
  
  decision_path?: string[];
  
  evaluation_details?: {
    total_policies: number;
    matched_policies: number;
    evaluated_rules: number;
    matched_rules: number;
    policy_priorities?: number[];
  };
  
  violations?: Array<{
    policy_id: string;
    policy_name: string;
    rule_index: number;
    rule_type: string;
    action: string;
    reason: string;
    details: any[];
    match_details?: any[];
    parameters?: any;
  }>;
  
  // Summary statistics for dashboard display
  total_rules_evaluated?: number;
  matched_rules_count?: number;
  policies_involved?: number;
  actions_count?: number;
  complexity?: 'simple' | 'moderate' | 'complex' | 'very_complex';
  primary_action?: string;
  
  violation_summary?: {
    count: number;
    primary_violation: any;
    violation_types: string[];
  };
}

export interface PolicyMetrics {
  timestamp: string;
  metric_type: string;
  value: number;
  policy_id?: string;
}

export interface ValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
}

export interface PolicyEngineStatus {
  connected: boolean;
  status: 'healthy' | 'disconnected' | 'error';
  url: string;
  last_check?: number;
  error?: string;
  timestamp?: number;
}

// Policy version tracking for cache invalidation
export interface PolicyVersion {
  version: number;
  timestamp: string;
}

export interface PolicyCacheCheck {
  valid: boolean;
  current_version: number;
  client_version: number;
  needs_refresh: boolean;
}

/**
 * Get policy engine connection status
 */
export const getPolicyEngineStatus = async (): Promise<PolicyEngineStatus> => {
  try {
    const response = await api.get('/policy-engine/status');
    return response.data;
  } catch (error) {
    console.error('Failed to fetch policy engine status:', error);
    return {
      connected: false,
      status: 'error',
      url: 'unknown',
      error: error instanceof Error ? error.message : 'Unknown error'
    };
  }
};

/**
 * Get all policies
 */
export const getPolicies = async (type?: string, cacheBust?: boolean): Promise<Policy[]> => {
  try {
    const params: any = type ? { type } : {};
    
    // Add cache-busting parameter when force refreshing
    if (cacheBust) {
      params._t = Date.now();
    }
    
    const response = await api.get('/policy-engine/policies', { params });
    
    const policies = Array.isArray(response.data) ? response.data : [];
    
    return policies.map(policy => ({
      ...policy,
      id: policy.id || `policy-${Math.random().toString(36).substring(2, 9)}`,
      name: policy.name || 'Unnamed Policy',
      priority: typeof policy.priority === 'number' ? policy.priority : parseInt(policy.priority) || 0,
      status: policy.status || (policy.enabled !== false ? 'active' : 'inactive'),
      type: policy.type || policy.policy_type || 'unknown',
      rule_type: policy.rule_type || policy.type || 'unknown'
    }));
  } catch (error) {
    console.error('Failed to fetch policies:', error);
    throw error;
  }
};

/**
 * Get policy by ID
 */
export const getPolicyById = async (policyId: string): Promise<Policy> => {
  try {
    const response = await api.get(`/policy-engine/policies/${policyId}`);
    return response.data;
  } catch (error) {
    console.error(`Failed to fetch policy ${policyId}:`, error);
    throw error;
  }
};

/**
 * Create new policy
 */
export const createPolicy = async (policy: PolicyRequest): Promise<Policy> => {
  try {
    const response = await api.post('/policy-engine/policies', policy);
    return response.data;
  } catch (error) {
    console.error('Failed to create policy:', error);
    throw error;
  }
};

/**
 * Update existing policy
 */
export const updatePolicy = async (policyId: string, policy: PolicyRequest): Promise<Policy> => {
  try {
    const response = await api.put(`/policy-engine/policies/${policyId}`, policy);
    return response.data;
  } catch (error) {
    console.error(`Failed to update policy ${policyId}:`, error);
    throw error;
  }
};

/**
 * Delete policy
 */
export const deletePolicy = async (policyId: string): Promise<void> => {
  try {
    await api.delete(`/policy-engine/policies/${policyId}`);
  } catch (error) {
    console.error(`Failed to delete policy ${policyId}:`, error);
    throw error;
  }
};

/**
 * Enable policy
 */
export const enablePolicy = async (policyId: string): Promise<void> => {
  try {
    await api.post(`/policy-engine/policies/${policyId}/enable`);
  } catch (error) {
    console.error(`Failed to enable policy ${policyId}:`, error);
    throw error;
  }
};

/**
 * Disable policy
 */
export const disablePolicy = async (policyId: string): Promise<void> => {
  try {
    await api.post(`/policy-engine/policies/${policyId}/disable`);
  } catch (error) {
    console.error(`Failed to disable policy ${policyId}:`, error);
    throw error;
  }
};

/**
 * Validate policy structure
 */
export const validatePolicy = async (policy: Record<string, any>): Promise<ValidationResult> => {
  try {
    const response = await api.post('/policy-engine/validate', { policy });
    return response.data;
  } catch (error) {
    console.error('Failed to validate policy:', error);
    throw error;
  }
};

/**
 * Get policy decisions from the policy engine
 */
export const getPolicyDecisions = async (params?: {
  start_time?: string;
  end_time?: string;
  policy_id?: string;
  component?: string;
  result?: string;
  limit?: number;
}): Promise<PolicyDecision[]> => {
  const response = await api.get('/policy-engine/decisions', { params });
  const data = response.data;
  
  if (Array.isArray(data)) {
    return data;
  } else if (data && Array.isArray(data.decisions)) {
    return data.decisions;
  } else {
    // NO FALLBACKS - throw error if unexpected format
    throw new Error(`Unexpected response format for policy decisions: ${typeof data}`);
  }
};

/**
 * Get policy metrics for charts and analytics
 */
export const getPolicyMetrics = async (params?: {
  start_time?: string;
  end_time?: string;
  metric_type?: string;
}): Promise<PolicyMetrics[]> => {
  const response = await api.get('/policy-engine/metrics/timeseries', { params });
  const data = response.data;
  
  if (Array.isArray(data)) {
    return data;
  } else if (data && Array.isArray(data.metrics)) {
    return data.metrics;
  } else {
    // NO FALLBACKS - throw error if unexpected format
    throw new Error(`Unexpected response format for policy metrics: ${typeof data}`);
  }
};

/**
 * Get current policy version for cache validation
 */
export const getPolicyVersion = async (): Promise<PolicyVersion> => {
  try {
    const response = await api.get('/policy-engine/version');
    return response.data;
  } catch (error) {
    console.error('Failed to fetch policy version:', error);
    throw error;
  }
};

/**
 * Check if cached policy version is still valid
 */
export const checkPolicyCacheValidity = async (clientVersion: number): Promise<PolicyCacheCheck> => {
  try {
    const response = await api.post('/policy-engine/cache-check', {
      policy_version: clientVersion
    });
    return response.data;
  } catch (error) {
    console.error('Failed to check policy cache validity:', error);
    throw error;
  }
};

/**
 * Get fresh policies bypassing all cache mechanisms
 * Use this for force refresh scenarios
 */
export const getFreshPolicies = async (type?: string): Promise<Policy[]> => {
  try {
    // Always use cache-busting to ensure fresh data
    return await getPolicies(type, true);
  } catch (error) {
    console.error('Failed to fetch fresh policies:', error);
    throw error;
  }
};

/**
 * Get policies with version checking and cache invalidation
 */
export const getPoliciesWithVersionCheck = async (
  type?: string,
  cachedVersion?: number
): Promise<{ policies: Policy[]; version: number; fromCache: boolean }> => {
  try {
    // If cachedVersion is undefined, this implies a force refresh - bypass all cache logic
    if (cachedVersion === undefined) {
      // Force refresh: fetch fresh policies and version directly with cache busting
      const [policies, versionInfo] = await Promise.all([
        getPolicies(type, true), // Add cache-busting for force refresh
        getPolicyVersion()
      ]);

      return {
        policies,
        version: versionInfo.version,
        fromCache: false
      };
    }

    // If we have a cached version, check if it's still valid
    try {
      const cacheCheck = await checkPolicyCacheValidity(cachedVersion);
      if (cacheCheck.valid && !cacheCheck.needs_refresh) {
        // Cache is still valid - return empty array to indicate no new data needed
        return {
          policies: [], // Empty array to indicate no new data
          version: cacheCheck.current_version,
          fromCache: true
        };
      }
    } catch (error) {
      console.warn('Cache validity check failed, fetching fresh data:', error);
      // Continue to fetch fresh data
    }

    // Cache was invalid or needs refresh - fetch fresh policies and version
    const [policies, versionInfo] = await Promise.all([
      getPolicies(type, true), // Use cache-busting for fresh data
      getPolicyVersion()
    ]);

    return {
      policies,
      version: versionInfo.version,
      fromCache: false
    };
  } catch (error) {
    console.error('Failed to fetch policies with version check:', error);
    throw error;
  }
}; 