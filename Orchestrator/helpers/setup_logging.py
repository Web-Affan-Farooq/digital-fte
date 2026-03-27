import logging
import sys
from datetime import datetime

def SetupLogging(self) -> logging.Logger:
    """
    Configure logging for the orchestrator.
    
    Args:
        self: Orchestrator instance
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger('Orchestrator')
    logger.setLevel(logging.INFO)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)

    # File handler
    log_file = self.logs / f'orchestrator_{datetime.now().strftime("%Y-%m-%d")}.log'
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)

    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    # Avoid duplicate handlers
    if not logger.handlers:
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

    return logger
