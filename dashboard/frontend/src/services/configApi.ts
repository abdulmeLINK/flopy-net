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