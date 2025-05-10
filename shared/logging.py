import logging
from typing import Optional
from pathlib import Path


class Logger:
    def __init__(self, name: str, level: str = 'INFO'):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level.upper())
        
        # Create console handler
        ch = logging.StreamHandler()
        ch.setLevel(level.upper())
        
        # Create formatter and add it to the handler
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        ch.setFormatter(formatter)
        
        # Add handler to logger
        self.logger.addHandler(ch)

    def get_logger(self) -> logging.Logger:
        return self.logger
