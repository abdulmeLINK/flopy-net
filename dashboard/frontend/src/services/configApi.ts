import api from './api';

export interface SystemConfig {
  gns3_url: string;
  collector_url: string;
  policy_engine_url: string;
  version: string;
}

export interface SystemInfo {
  application: {
    name: string;
    version: string;
    build_date: string;
    git_commit: string;
    environment: string;
  };
  services: {
    gns3_url: string;
    collector_url: string;
    policy_engine_url: string;
  };
  runtime: {
    startup_time: string;
    log_level: string;
    connection_timeout: string;
    connection_retries: string;
  };
  container: {
    hostname: string;
    container_name: string;
  };
}

/**
 * Get system configuration
 */
export const getSystemConfig = async (): Promise<SystemConfig> => {
  try {
    const response = await api.get('/config/service-urls');
    return response.data;
  } catch (error) {
    console.error('Failed to fetch system configuration:', error);
    // Don't provide fallbacks - let the UI handle the error
    throw error;
  }
};

/**
 * Get comprehensive system information including environment variables
 */
export const getSystemInfo = async (): Promise<SystemInfo> => {
  try {
    const response = await api.get('/config/system-info');
    return response.data;
  } catch (error) {
    console.error('Failed to fetch system information:', error);
    throw error;
  }
};