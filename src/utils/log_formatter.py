import logging
import os
import sys

# Try to import colorama for Windows color support
try:
    import colorama
    colorama.init()
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False

class ColoredFormatter(logging.Formatter):
    """Custom formatter to add colors to log messages based on level."""

    # Check if colors should be used
    USE_COLORS = os.environ.get('FORCE_COLOR', 'false').lower() in ('true', '1', 'yes')
    
    # Auto-detect color support if not forced
    if not USE_COLORS:
        # Check if we're in a terminal that supports colors
        if hasattr(sys.stdout, 'isatty') and sys.stdout.isatty():
            # Windows may need special handling
            if sys.platform.startswith('win'):
                USE_COLORS = COLORAMA_AVAILABLE
            else:
                USE_COLORS = True
    
    # ANSI color codes
    grey = "\033[38;20m" if USE_COLORS else ""
    yellow = "\033[33;20m" if USE_COLORS else ""
    red = "\033[31;20m" if USE_COLORS else ""
    bold_red = "\033[31;1m" if USE_COLORS else ""
    reset = "\033[0m" if USE_COLORS else ""
    
    # Define format string including timestamp, logger name, level name, and message
    format_str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_line_format_str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"
    
    # Define formats for each log level
    FORMATS = {
        logging.DEBUG: grey + file_line_format_str + reset,
        logging.INFO: grey + format_str + reset,
        logging.WARNING: yellow + format_str + reset,
        logging.ERROR: red + format_str + reset,
        logging.CRITICAL: bold_red + format_str + reset
    }

    def __init__(self, include_file_line=False):
        """
        Initialize the formatter with option to include file/line info.
        
        Args:
            include_file_line: Whether to include file name and line number in logs
        """
        super().__init__()
        self.include_file_line = include_file_line
        if not self.include_file_line:
            # Update formats to use the simpler format string
            for level in self.FORMATS:
                if level != logging.DEBUG:  # Keep debug logs with file/line
                    fmt = self.FORMATS[level]
                    self.FORMATS[level] = fmt.replace(self.file_line_format_str, self.format_str)

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record) 