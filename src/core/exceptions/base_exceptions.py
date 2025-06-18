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