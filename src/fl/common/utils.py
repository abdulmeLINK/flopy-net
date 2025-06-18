"""
Utility functions for federated learning.
"""

import logging
import json
import os
import time
from typing import Dict, Any, Optional, Callable, TypeVar, cast

# Type variables for the decorator
T = TypeVar('T')
R = TypeVar('R')

def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None) -> None:
    """
    Setup logging configuration.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (optional)
    """
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {log_level}")
    
    logging_config = {
        'level': numeric_level,
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'datefmt': '%Y-%m-%d %H:%M:%S',
    }
    
    if log_file:
        # Ensure directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        
        logging_config['filename'] = log_file
        logging_config['filemode'] = 'a'
    
    logging.basicConfig(**logging_config)
    
    # Log the configuration
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized with level {log_level}")
    if log_file:
        logger.info(f"Logging to file: {log_file}")

def save_json(data: Dict[str, Any], filepath: str) -> bool:
    """
    Save data to a JSON file.
    
    Args:
        data: Data to save
        filepath: Path to the JSON file
        
    Returns:
        True if successful, False otherwise
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Create directory if it doesn't exist
        directory = os.path.dirname(filepath)
        if directory:
            os.makedirs(directory, exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Data saved to {filepath}")
        return True
    
    except Exception as e:
        logger.error(f"Error saving data to {filepath}: {e}")
        return False

def load_json(filepath: str) -> Optional[Dict[str, Any]]:
    """
    Load data from a JSON file.
    
    Args:
        filepath: Path to the JSON file
        
    Returns:
        Data from the JSON file, or None if an error occurred
    """
    logger = logging.getLogger(__name__)
    
    try:
        if not os.path.exists(filepath):
            logger.error(f"File not found: {filepath}")
            return None
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        logger.info(f"Data loaded from {filepath}")
        return data
    
    except Exception as e:
        logger.error(f"Error loading data from {filepath}: {e}")
        return None

def measure_execution_time(func: Callable[[Any], R]) -> Callable[[Any], R]:
    """
    Decorator to measure the execution time of a function.
    
    Args:
        func: Function to decorate
        
    Returns:
        Decorated function
    """
    def wrapper(*args: Any, **kwargs: Any) -> R:
        logger = logging.getLogger(func.__module__)
        
        logger.info(f"Starting execution of {func.__name__}")
        start_time = time.time()
        
        result = func(*args, **kwargs)
        
        end_time = time.time()
        execution_time = end_time - start_time
        logger.info(f"Execution of {func.__name__} completed in {execution_time:.4f} seconds")
        
        return result
    
    return cast(Callable[[Any], R], wrapper) 