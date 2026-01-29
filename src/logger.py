import logging
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON-like format"""
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }
        
        # Add extra fields if present
        if hasattr(record, 'action'):
            log_data['action'] = record.action
        if hasattr(record, 'order_id'):
            log_data['order_id'] = record.order_id
        if hasattr(record, 'symbol'):
            log_data['symbol'] = record.symbol
        if hasattr(record, 'side'):
            log_data['side'] = record.side
        if hasattr(record, 'quantity'):
            log_data['quantity'] = record.quantity
        if hasattr(record, 'price'):
            log_data['price'] = record.price
        if hasattr(record, 'error_code'):
            log_data['error_code'] = record.error_code
        
        # Format as readable structured log
        parts = [f"[{log_data['timestamp']}]", f"{log_data['level']}"]
        
        if 'action' in log_data:
            parts.append(f"ACTION={log_data['action']}")
        
        if 'symbol' in log_data:
            parts.append(f"SYMBOL={log_data['symbol']}")
        
        if 'order_id' in log_data:
            parts.append(f"ORDER_ID={log_data['order_id']}")
        
        if 'side' in log_data:
            parts.append(f"SIDE={log_data['side']}")
        
        if 'quantity' in log_data:
            parts.append(f"QTY={log_data['quantity']}")
        
        if 'price' in log_data:
            parts.append(f"PRICE={log_data['price']}")
        
        if 'error_code' in log_data:
            parts.append(f"ERROR_CODE={log_data['error_code']}")
        
        parts.append(f"MSG={log_data['message']}")
        
        return " | ".join(parts)

def setup_logger(name: str = "binance_bot", log_level: int = logging.INFO):
    """
    Setup structured logging with file and console output
    
    Args:
        name: Logger name
        log_level: Logging level (default: INFO)
    
    Returns:
        Configured logger instance
    """
    
    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Create log file with date
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = log_dir / f"bot_{today}.log"
    
    # Configure logger
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # Clear existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    # File handler with structured format
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(log_level)
    file_formatter = StructuredFormatter()
    file_handler.setFormatter(file_formatter)
    
    # Console handler with simpler format
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_formatter = logging.Formatter(
        '%(levelname)s: %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    
    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def log_order_action(logger: logging.Logger, action: str, **kwargs):
    """
    Helper function to log order actions with structured data
    
    Args:
        logger: Logger instance
        action: Action type (e.g., 'ORDER_PLACED', 'ORDER_EXECUTED', 'ORDER_FAILED')
        **kwargs: Additional fields to log (order_id, symbol, side, quantity, price, msg, etc.)
    """
    # Extract message separately (use 'msg' to avoid conflict with LogRecord.message)
    msg = kwargs.pop('message', kwargs.pop('msg', f"{action}"))
    
    # Build extra dict, avoiding reserved LogRecord attributes
    reserved_attrs = {'name', 'msg', 'args', 'created', 'filename', 'funcName', 
                     'levelname', 'levelno', 'lineno', 'module', 'msecs', 'message',
                     'pathname', 'process', 'processName', 'relativeCreated', 'thread',
                     'threadName', 'exc_info', 'exc_text', 'stack_info'}
    
    extra = {'action': action}
    for key, value in kwargs.items():
        if key not in reserved_attrs:
            extra[key] = value
    
    logger.info(f"{action}: {msg}", extra=extra)

# Global logger instance
logger = setup_logger()