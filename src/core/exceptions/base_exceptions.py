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
Base Exceptions Module

This module defines the base exceptions for the federated learning system.
"""


class FLBaseException(Exception):
    """
    Base exception for all federated learning system exceptions.
    
    Args:
        message: Error message
        code: Optional error code
    """
    
    def __init__(self, message: str, code: int = None):
        self.message = message
        self.code = code
        super().__init__(self.message)


class FLValueError(FLBaseException):
    """
    Exception raised for invalid input values.
    
    This exception is used when a function receives an argument with
    an inappropriate value.
    """
    pass


class FLRuntimeError(FLBaseException):
    """
    Exception raised for runtime errors.
    
    This exception is used for errors that occur during execution
    that don't fall into other categories.
    """
    pass


class FLConnectionError(FLBaseException):
    """
    Exception raised for connection errors.
    
    This exception is used when there are problems with network
    connections between components.
    """
    pass


class FLDataError(FLBaseException):
    """
    Exception raised for data-related errors.
    
    This exception is used when there are issues with data processing,
    loading, or formatting.
    """
    pass


class FLSecurityError(FLBaseException):
    """
    Exception raised for security-related errors.
    
    This exception is used for security violations, unauthorized access
    attempts, or other security concerns.
    """
    pass 