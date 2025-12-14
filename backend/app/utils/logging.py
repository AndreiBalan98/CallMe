"""
Logging configuration for the application.
Uses structured logging with consistent formatting.
"""

import logging
import sys
from typing import Optional

from app.config import settings


# Custom log format
LOG_FORMAT = "%(asctime)s │ %(levelname)-8s │ %(name)s │ %(message)s"
DATE_FORMAT = "%H:%M:%S"


def setup_logging(level: Optional[str] = None) -> None:
    """
    Configure application logging.
    
    Args:
        level: Optional log level override. Defaults to DEBUG if debug mode, else INFO.
    """
    if level is None:
        level = "DEBUG" if settings.debug else "INFO"
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, level),
        format=LOG_FORMAT,
        datefmt=DATE_FORMAT,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Reduce noise from third-party libraries
    logging.getLogger("websockets").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.
    
    Args:
        name: Logger name, typically __name__ of the calling module.
        
    Returns:
        Configured logger instance.
    """
    return logging.getLogger(name)


class CallLogger:
    """
    Specialized logger for tracking call-related events.
    Adds call context to log messages.
    """
    
    def __init__(self, call_id: str):
        self.call_id = call_id
        self.logger = get_logger(f"call.{call_id[:8]}")
    
    def _format_message(self, message: str) -> str:
        return f"[{self.call_id[:8]}] {message}"
    
    def info(self, message: str) -> None:
        self.logger.info(self._format_message(message))
    
    def debug(self, message: str) -> None:
        self.logger.debug(self._format_message(message))
    
    def warning(self, message: str) -> None:
        self.logger.warning(self._format_message(message))
    
    def error(self, message: str) -> None:
        self.logger.error(self._format_message(message))
