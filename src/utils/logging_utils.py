"""
Logging utilities for the federated learning system.

This module provides the logging functionality for the federated learning system,
including console, file, and dashboard logging capabilities.
"""

import os
import sys
import logging
import datetime
import traceback
from logging.handlers import RotatingFileHandler
from typing import Dict, List, Optional, Any

# --- Import ColoredFormatter --- 
from .log_formatter import ColoredFormatter

# Global log storage for dashboard access
system_logs = {
    "info": [],
    "warning": [],
    "error": [],
    "debug": []
}

# Maximum number of log entries to keep in memory
MAX_LOG_ENTRIES = 1000

class DashboardLogHandler(logging.Handler):
    """
    Custom log handler to store logs for dashboard access.
    """
    def emit(self, record):
        try:
            # Format the log message
            log_entry = self.format(record)
            
            # Store log by level
            level = record.levelname.lower()
            if level in system_logs:
                # Add timestamp, level, and message
                system_logs[level].append({
                    'timestamp': datetime.datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S'),
                    'message': log_entry,
                    'module': record.module,
                    'function': record.funcName,
                    'line': record.lineno
                })
                
                # Trim log if it gets too long
                if len(system_logs[level]) > MAX_LOG_ENTRIES:
                    system_logs[level] = system_logs[level][-MAX_LOG_ENTRIES:]
        except Exception as e:
            print(f"Error in dashboard log handler: {str(e)}")


def setup_logging(
    log_level: str = "INFO",
    log_to_file: bool = True,
    log_dir: str = "logs",
    log_to_dashboard: bool = True,
    app_name: str = "federated-learning"
) -> logging.Logger:
    """
    Set up logging for the application.
    
    Args:
        log_level: The logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Whether to log to a file
        log_dir: Directory to store log files
        log_to_dashboard: Whether to store logs for dashboard access
        app_name: Name of the application for the logger
        
    Returns:
        Logger instance
    """
    # Convert string log level to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create logger
    logger = logging.getLogger(app_name)
    logger.setLevel(numeric_level)
    
    # Clear any existing handlers
    if logger.handlers:
        logger.handlers.clear()
    
    # Use ColoredFormatter for console, and a standard one for file/dashboard
    # The ColoredFormatter can include file/line for DEBUG, so we can simplify the standard_formatter
    console_formatter = ColoredFormatter(include_file_line=True) # Shows file/line for DEBUG by default
    standard_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)', 
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(console_formatter) # Use ColoredFormatter
    logger.addHandler(console_handler)
    
    # File handler
    if log_to_file:
        try:
            # Create log directory if it doesn't exist
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            # Create timestamped log file
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            log_file = os.path.join(log_dir, f"{app_name}_{timestamp}.log")
            
            # Set up rotating file handler (10MB max size, keep 5 backups)
            file_handler = RotatingFileHandler(
                log_file, 
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5
            )
            file_handler.setLevel(numeric_level)
            file_handler.setFormatter(standard_formatter) # Use standard_formatter for files
            logger.addHandler(file_handler)
            
            logger.info(f"Log file created at {log_file}")
        except Exception as e:
            logger.error(f"Failed to set up file logging: {str(e)}")
    
    # Dashboard handler
    if log_to_dashboard:
        try:
            dashboard_handler = DashboardLogHandler()
            dashboard_handler.setLevel(numeric_level)
            # Dashboard logs might be better with simpler format or specific one
            dashboard_handler.setFormatter(simple_formatter) # Use simple_formatter for dashboard
            logger.addHandler(dashboard_handler)
            
            logger.info("Dashboard logging enabled")
        except Exception as e:
            logger.error(f"Failed to set up dashboard logging: {str(e)}")
    
    return logger


def get_logs(
    level: Optional[str] = None,
    limit: int = 100,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    module: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get logs from the system log storage.
    
    Args:
        level: Log level to filter by (info, warning, error, debug)
        limit: Maximum number of log entries to return
        start_time: Filter logs after this time (format: YYYY-MM-DD HH:MM:SS)
        end_time: Filter logs before this time (format: YYYY-MM-DD HH:MM:SS)
        module: Filter logs by module name
        
    Returns:
        List of log entries
    """
    all_logs = []
    
    # Collect logs from all levels or specified level
    if level and level.lower() in system_logs:
        logs_to_process = {level.lower(): system_logs[level.lower()]}
    else:
        logs_to_process = system_logs
    
    # Process logs
    for log_level, logs in logs_to_process.items():
        for log in logs:
            log_with_level = log.copy()
            log_with_level['level'] = log_level
            all_logs.append(log_with_level)
    
    # Filter by time range
    if start_time:
        try:
            start_dt = datetime.datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
            all_logs = [
                log for log in all_logs 
                if datetime.datetime.strptime(log['timestamp'], '%Y-%m-%d %H:%M:%S') >= start_dt
            ]
        except Exception as e:
            print(f"Error parsing start_time: {e}")
    
    if end_time:
        try:
            end_dt = datetime.datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
            all_logs = [
                log for log in all_logs 
                if datetime.datetime.strptime(log['timestamp'], '%Y-%m-%d %H:%M:%S') <= end_dt
            ]
        except Exception as e:
            print(f"Error parsing end_time: {e}")
    
    # Filter by module
    if module:
        all_logs = [log for log in all_logs if module.lower() in log.get('module', '').lower()]
    
    # Sort by timestamp (newest first)
    all_logs.sort(key=lambda x: x['timestamp'], reverse=True)
    
    # Apply limit
    return all_logs[:limit]


def clear_logs(level: Optional[str] = None) -> None:
    """
    Clear logs from the system log storage.
    
    Args:
        level: Log level to clear (if None, clears all logs)
    """
    if level and level.lower() in system_logs:
        system_logs[level.lower()] = []
    elif level is None:
        for key in system_logs:
            system_logs[key] = []


def log_exception(
    logger: logging.Logger,
    exception: Exception,
    message: str = "An exception occurred",
    include_traceback: bool = True
) -> None:
    """
    Log an exception with optional traceback.
    
    Args:
        logger: Logger instance
        exception: The exception to log
        message: Message to include with the exception
        include_traceback: Whether to include the full traceback
    """
    if include_traceback:
        tb_str = ''.join(traceback.format_exception(type(exception), exception, exception.__traceback__))
        logger.error(f"{message}: {str(exception)}\n{tb_str}")
    else:
        logger.error(f"{message}: {str(exception)}") 