#!/usr/bin/env python3
"""
Copyright (c) 2025 Abdulmelik Saylan

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import requests
import logging
import os
import json
import time
from datetime import datetime, timedelta

from .storage import MetricsStorage

logger = logging.getLogger(__name__)

class PolicyMonitor:
    """Monitors the Policy Engine for metrics and decisions."""

    def __init__(self, policy_engine_url: str, storage: MetricsStorage):
        """Initialize the PolicyMonitor.

        Args:
            policy_engine_url: The base URL of the Policy Engine API.
            storage: The MetricsStorage instance for saving metrics.
        """
        if not policy_engine_url:
            raise ValueError("Policy Engine URL cannot be empty")
        self.policy_engine_url = policy_engine_url.rstrip('/')
        self.metrics_endpoint = f"{self.policy_engine_url}/metrics"
        self.decisions_endpoint = f"{self.policy_engine_url}/api/v1/policy_decisions"
        self.policy_metrics_endpoint = f"{self.policy_engine_url}/api/v1/policy_metrics"
        self.storage = storage
        self.last_decision_timestamp = time.time() - 3600  # Start from 1 hour ago
        logger.info(f"Policy Monitor initialized for URL: {self.policy_engine_url}")

    def collect_metrics(self):
        """Collect all metrics from the Policy Engine."""
        self.collect_legacy_metrics()
        self.collect_policy_decisions()
        self.collect_policy_metrics()

    def collect_legacy_metrics(self):
        """Collect metrics from the Policy Engine /metrics endpoint."""
        logger.debug(f"Attempting to collect legacy metrics from {self.metrics_endpoint}")
        try:
            response = requests.get(self.metrics_endpoint, timeout=10)
            response.raise_for_status()

            metrics_data = response.json()
            if metrics_data:
                self.storage.store_metric("policy_engine", metrics_data)
                logger.info(f"Successfully collected legacy metrics from Policy Engine: {metrics_data}")
            else:
                logger.warning("Received empty legacy metrics data from Policy Engine")

        except requests.exceptions.RequestException as e:
            logger.error(f"Error connecting to Policy Engine at {self.metrics_endpoint}: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON response from Policy Engine: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred during Policy Engine legacy metric collection: {e}")

    def collect_policy_decisions(self):
        """Collect policy decisions from the Policy Engine."""
        logger.debug(f"Attempting to collect policy decisions from {self.decisions_endpoint}")
        try:
            # Get decisions since last collection
            params = {
                'start_time': self.last_decision_timestamp,
                'limit': 1000
            }
            
            response = requests.get(self.decisions_endpoint, params=params, timeout=10)
            response.raise_for_status()

            decisions_data = response.json()
            if decisions_data:
                # Store each decision
                for decision in decisions_data:
                    self.storage.store_metric("policy_decisions", decision)
                    
                # Update last timestamp
                if decisions_data:
                    latest_timestamp = max(d.get('timestamp', 0) for d in decisions_data)
                    self.last_decision_timestamp = latest_timestamp
                    
                logger.info(f"Successfully collected {len(decisions_data)} policy decisions from Policy Engine")
            else:
                logger.debug("No new policy decisions found")

        except requests.exceptions.RequestException as e:
            logger.error(f"Error connecting to Policy Engine decisions endpoint: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON response from Policy Engine decisions: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred during policy decisions collection: {e}")

    def collect_policy_metrics(self):
        """Collect policy metrics for charts from the Policy Engine."""
        logger.debug(f"Attempting to collect policy metrics from {self.policy_metrics_endpoint}")
        try:
            # Get metrics for the last 24 hours
            end_time = time.time()
            start_time = end_time - 24 * 3600
            
            params = {
                'start_time': start_time,
                'end_time': end_time
            }
            
            response = requests.get(self.policy_metrics_endpoint, params=params, timeout=10)
            response.raise_for_status()

            response_data = response.json()
            
            # Handle the correct response structure: {"metrics": [...], "summary": {...}}
            if response_data and isinstance(response_data, dict) and 'metrics' in response_data:
                metrics_data = response_data['metrics']
                
                if metrics_data and isinstance(metrics_data, list):
                    # Store each metric individually with proper structure
                    for metric in metrics_data:
                        # Store as individual time-series points for charts
                        metric_record = {
                            'timestamp': metric.get('timestamp', time.time()),
                            'iso_time': metric.get('iso_time'),
                            'allowed_count': metric.get('allowed_count', 0),
                            'denied_count': metric.get('denied_count', 0),
                            'total_evaluations': metric.get('total_evaluations', 0),
                            'denial_rate': metric.get('denial_rate', 0.0),
                            'success_rate': metric.get('success_rate', 100.0),
                            'avg_evaluation_time_ms': metric.get('avg_evaluation_time_ms', 0.0),
                            'policies_active': metric.get('policies_active', 0),
                            'unique_requesters': metric.get('unique_requesters', 0)
                        }
                        
                        # Store with metric_type that dashboard expects
                        self.storage.store_metric("policy_count", metric_record)
                        
                        # Also store decision count metrics separately for the dashboard
                        decision_metric = {
                            'timestamp': metric_record['timestamp'],
                            'iso_time': metric_record['iso_time'],
                            'allowed': metric_record['allowed_count'],
                            'denied': metric_record['denied_count'],
                            'total': metric_record['total_evaluations'],
                            'denial_rate': metric_record['denial_rate']
                        }
                        
                        self.storage.store_metric("decision_count", decision_metric)
                    
                    logger.info(f"Successfully stored {len(metrics_data)} policy metrics time-series points")
                else:
                    logger.warning("No metrics array found in policy engine response")
            else:
                logger.warning("Invalid policy metrics response structure from Policy Engine")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error collecting policy metrics: {e}")
        except Exception as e:
            logger.error(f"Unexpected error collecting policy metrics: {e}")