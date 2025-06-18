"""
Logging Utilities

This module provides standardized logging setup and utilities for the
federated learning system.
"""

import logging
import sys
import os
from datetime import datetime
from typing import Optional


def setup_logger(
    name: str,
    level: int = logging.INFO,
    file_path: Optional[str] = None,
    console: bool = True,
    format_str: Optional[str] = None
) -> logging.Logger:
    """
    Set up a logger with standard configuration.
    
    Args:
        name: Name of the logger
        level: Logging level (default: INFO)
        file_path: Optional path to log file
        console: Whether to log to console (default: True)
        format_str: Custom format string (optional)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Clear existing handlers if any
    if logger.handlers:
        logger.handlers.clear()
    
    # Use default format if none provided
    if format_str is None:
        format_str = '%(asctime)s [%(levelname)s] [%(name)s] - %(message)s'
    
    formatter = logging.Formatter(format_str)
    
    # Add console handler if requested
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # Add file handler if file path provided
    if file_path:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        file_handler = logging.FileHandler(file_path)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_default_logger(name: str) -> logging.Logger:
    """
    Get a logger with default configuration.
    
    Args:
        name: Name of the logger
        
    Returns:
        Logger instance with default configuration
    """
    return setup_logger(name)


def get_file_logger(name: str, directory: str = "./logs") -> logging.Logger:
    """
    Get a logger that logs to both console and a file.
    
    Args:
        name: Name of the logger
        directory: Directory to store log files (default: "./logs")
        
    Returns:
        Logger instance configured for file logging
    """
    # Ensure logs directory exists
    os.makedirs(directory, exist_ok=True)
    
    # Create a log file with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{name}_{timestamp}.log"
    file_path = os.path.join(directory, filename)
    
    return setup_logger(name, file_path=file_path)


class LoggerMixin:
    """
    Mixin class providing logging capabilities to classes.
    
    Classes inheriting from this mixin get a preconfigured logger instance.
    """
    
    @property
    def logger(self) -> logging.Logger:
        """
        Get a logger for the class.
        
        Returns:
            Logger instance named after the class
        """
        if not hasattr(self, '_logger'):
            self._logger = logging.getLogger(self.__class__.__name__)
        return self._logger 