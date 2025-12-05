"""
Logging configuration for the bot
"""
import logging
import sys
from datetime import datetime
from config import app_config

def setup_logger(name: str = "ethiostore_bot") -> logging.Logger:
    """
    Setup and configure logger
    
    Args:
        name: Logger name
    
    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(name)
    
    # Set level based on debug mode
    if app_config.DEBUG:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if app_config.DEBUG else logging.INFO)
    
    # Create file handler
    log_filename = f"logs/bot_{datetime.now().strftime('%Y%m%d')}.log"
    try:
        import os
        os.makedirs("logs", exist_ok=True)
        file_handler = logging.FileHandler(log_filename, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
    except:
        file_handler = None
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Add formatter to handlers
    console_handler.setFormatter(formatter)
    if file_handler:
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    logger.addHandler(console_handler)
    
    return logger

# Create default logger instance
logger = setup_logger()



