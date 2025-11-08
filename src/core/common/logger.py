"""
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
Logger Mixin for Federated Learning classes.

This module provides a logger mixin that can be used by classes to get logging functionality.
"""

import logging
import os
import sys
from datetime import datetime
from typing import Optional

# Configure logging
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Configure the root logger
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT,
    datefmt=LOG_DATE_FORMAT,
    stream=sys.stdout
)

class LoggerMixin:
    """
    Mixin class to provide logging capabilities to any class.
    
    This mixin adds a logger property to any class that inherits from it.
    The logger name is automatically derived from the class name and module.
    """
    
    _logger: Optional[logging.Logger] = None
    
    @property
    def logger(self) -> logging.Logger:
        """
        Get a logger for this class.
        
        Returns:
            logging.Logger: A configured logger for this class
        """
        if self._logger is None:
            # Get the class name
            class_name = self.__class__.__name__
            
            # Get the module name
            module_name = self.__class__.__module__
            
            # Create logger name from module and class
            logger_name = f"{module_name}.{class_name}"
            
            # Create and configure logger
            self._logger = logging.getLogger(logger_name)
            
        return self._logger

def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger with the given name.
    
    Args:
        name: Name for the logger
        
    Returns:
        logging.Logger: A configured logger
    """
    return logging.getLogger(name)

def configure_file_logging(log_dir: str = "./logs", filename: Optional[str] = None) -> None:
    """
    Configure logging to write to a file in addition to stdout.
    
    Args:
        log_dir: Directory to write log files to
        filename: Name of the log file (defaults to date-time stamped file)
    """
    # Create log directory if it doesn't exist
    os.makedirs(log_dir, exist_ok=True)
    
    # Create a timestamped filename if none provided
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"federated_learning_{timestamp}.log"
    
    # Full path to log file
    log_path = os.path.join(log_dir, filename)
    
    # Create file handler
    file_handler = logging.FileHandler(log_path)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
    
    # Add file handler to root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)
    
    # Log that file logging has been configured
    root_logger.info(f"File logging configured to: {log_path}") 