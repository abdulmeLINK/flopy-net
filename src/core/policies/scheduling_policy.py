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

"""
Scheduling Policy

This module defines policies for scheduling federated learning rounds and client participation.
"""

from abc import abstractmethod
from typing import Dict, Any, List, Optional, Set
import time

from src.core.policies.policy import IPolicy


class ISchedulingPolicy(IPolicy):
    """
    Interface for scheduling policies.
    
    Scheduling policies determine when to initiate federated learning rounds,
    which clients participate, and how to handle timeouts and failures.
    """
    
    @abstractmethod
    def schedule_round(self, client_status: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Schedule a federated learning round.
        
        Args:
            client_status: Status information for all available clients
            context: Additional context for scheduling decisions
            
        Returns:
            Dictionary with scheduling decisions (e.g. start time, participating clients)
        """
        pass
    
    @abstractmethod
    def handle_timeout(self, client_id: str, round_id: int, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Handle a client timeout during a round.
        
        Args:
            client_id: ID of the client that timed out
            round_id: ID of the current round
            context: Additional context
            
        Returns:
            Dictionary with actions to take (e.g. exclude client, retry)
        """
        pass


class PeriodicSchedulingPolicy(ISchedulingPolicy):
    """
    Periodic Scheduling Policy.
    
    This policy schedules federated learning rounds at regular intervals
    and maintains a backoff strategy for handling client timeouts.
    """
    
    def __init__(self, policy_id: str, interval_seconds: int = 3600, 
                 max_concurrent_clients: int = 100, timeout_seconds: int = 600,
                 max_retries: int = 3, backoff_factor: float = 1.5,
                 description: str = "Periodic Scheduling Policy"):
        """
        Initialize the periodic scheduling policy.
        
        Args:
            policy_id: Unique identifier for the policy
            interval_seconds: Time between rounds in seconds
            max_concurrent_clients: Maximum number of clients per round
            timeout_seconds: Client timeout in seconds
            max_retries: Maximum number of retries for a client
            backoff_factor: Factor to increase timeout for each retry
            description: Human-readable description of the policy
        """
        self.policy_id = policy_id
        self.policy_type = "scheduling"
        self.description = description
        self.interval_seconds = interval_seconds
        self.max_concurrent_clients = max_concurrent_clients
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        
        self.parameters = {
            "interval_seconds": interval_seconds,
            "max_concurrent_clients": max_concurrent_clients,
            "timeout_seconds": timeout_seconds,
            "max_retries": max_retries,
            "backoff_factor": backoff_factor
        }
        
        # Track client participation and timeouts
        self.client_retries = {}  # client_id -> retries count
        self.blacklisted_clients = set()  # Set of client_ids to exclude
        self.last_round_time = 0  # Time of last round
    
    def get_id(self) -> str:
        return self.policy_id
    
    def get_type(self) -> str:
        return self.policy_type
    
    def get_description(self) -> str:
        return self.description
    
    def get_parameters(self) -> Dict[str, Any]:
        return self.parameters
    
    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate the policy in the given context.
        
        Args:
            context: Context for policy evaluation
                - client_status: Client status information
                - current_round: Current round number
                - client_timeout: Client timeout event (optional)
                
        Returns:
            Dictionary with scheduling decisions
        """
        client_status = context.get('client_status', {})
        current_round = context.get('current_round', 0)
        
        # Check if there's a timeout to handle
        client_timeout = context.get('client_timeout', None)
        if client_timeout:
            return self.handle_timeout(
                client_timeout.get('client_id', ''),
                current_round,
                context
            )
        
        # Otherwise, schedule next round
        return self.schedule_round(client_status, context)
    
    def schedule_round(self, client_status: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Schedule a federated learning round based on periodic intervals.
        
        Args:
            client_status: Status information for all available clients
            context: Additional context for scheduling decisions
            
        Returns:
            Dictionary with scheduling decisions
        """
        current_time = time.time()
        time_since_last_round = current_time - self.last_round_time
        
        # Determine if it's time for a new round
        should_start_round = (time_since_last_round >= self.interval_seconds) or (self.last_round_time == 0)
        
        if should_start_round:
            self.last_round_time = current_time
            
            # Select available clients (excluding blacklisted ones)
            available_clients = []
            for client_id, status in client_status.items():
                if (client_id not in self.blacklisted_clients and 
                    status.get('available', False) and 
                    status.get('connected', False)):
                    available_clients.append(client_id)
            
            # Limit number of selected clients
            selected_clients = available_clients[:self.max_concurrent_clients]
            
            return {
                'start_round': True,
                'start_time': current_time,
                'selected_clients': selected_clients,
                'timeout_seconds': self.timeout_seconds
            }
        else:
            # Not time for a new round yet
            return {
                'start_round': False,
                'next_round_in_seconds': self.interval_seconds - time_since_last_round
            }
    
    def handle_timeout(self, client_id: str, round_id: int, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Handle a client timeout during a round.
        
        Args:
            client_id: ID of the client that timed out
            round_id: ID of the current round
            context: Additional context
            
        Returns:
            Dictionary with actions to take
        """
        # Initialize retries for this client if not already tracked
        if client_id not in self.client_retries:
            self.client_retries[client_id] = 0
        
        # Increment retry count
        self.client_retries[client_id] += 1
        current_retries = self.client_retries[client_id]
        
        if current_retries > self.max_retries:
            # Client has exceeded max retries, blacklist it
            self.blacklisted_clients.add(client_id)
            return {
                'action': 'exclude',
                'client_id': client_id,
                'reason': f"Exceeded maximum retries ({self.max_retries})"
            }
        else:
            # Calculate timeout with exponential backoff
            adjusted_timeout = int(self.timeout_seconds * (self.backoff_factor ** (current_retries - 1)))
            
            return {
                'action': 'retry',
                'client_id': client_id,
                'retry_count': current_retries,
                'timeout_seconds': adjusted_timeout
            }
    
    def reset_client_status(self, client_id: str = None) -> None:
        """
        Reset status tracking for clients.
        
        Args:
            client_id: Specific client to reset, or None to reset all
        """
        if client_id is None:
            # Reset for all clients
            self.client_retries = {}
            self.blacklisted_clients = set()
        else:
            # Reset for specific client
            if client_id in self.client_retries:
                self.client_retries.pop(client_id)
            if client_id in self.blacklisted_clients:
                self.blacklisted_clients.remove(client_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the policy to a dictionary.
        
        Returns:
            Dictionary representation of the policy
        """
        return {
            'policy_id': self.policy_id,
            'policy_type': self.policy_type,
            'description': self.description,
            'parameters': self.parameters,
            'last_round_time': self.last_round_time,
            'client_retries': self.client_retries,
            'blacklisted_clients': list(self.blacklisted_clients)
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'PeriodicSchedulingPolicy':
        """
        Create a policy from a dictionary.
        
        Args:
            data: Dictionary representation of a policy
            
        Returns:
            PeriodicSchedulingPolicy instance
        """
        params = data.get('parameters', {})
        
        policy = PeriodicSchedulingPolicy(
            policy_id=data['policy_id'],
            interval_seconds=params.get('interval_seconds', 3600),
            max_concurrent_clients=params.get('max_concurrent_clients', 100),
            timeout_seconds=params.get('timeout_seconds', 600),
            max_retries=params.get('max_retries', 3),
            backoff_factor=params.get('backoff_factor', 1.5),
            description=data.get('description', "Periodic Scheduling Policy")
        )
        
        # Restore state
        if 'last_round_time' in data:
            policy.last_round_time = data['last_round_time']
        
        if 'client_retries' in data:
            policy.client_retries = data['client_retries']
        
        if 'blacklisted_clients' in data:
            policy.blacklisted_clients = set(data['blacklisted_clients'])
            
        return policy 