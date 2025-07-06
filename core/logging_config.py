
import logging
from logging.config import dictConfig
from logging.handlers import RotatingFileHandler

from pythonjsonlogger import jsonlogger

class PrettyJsonFormatter(jsonlogger.JsonFormatter):
    def process_log_record(self, log_record):
        import json
        return json.dumps(log_record, indent=4)  # <-- Pretty printing

LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s"

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,  # Keep default loggers
    "formatters": {
        "default": {
            "format": LOG_FORMAT,
        },
         "json": {
            "()": "core.logging_config.PrettyJsonFormatter",  # Reference custom class
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
        },

        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "logs/app.log",       # Log file path
            "maxBytes": 1024 * 1024 * 5,  # 5MB
            "backupCount": 3,             # Keep 3 old files        
            "formatter": "json",              # Use the default formatter
        },

    },
    "loggers": {
        "uvicorn": {
            "handlers": ["console"],
            "level": "INFO",
        },
        "uvicorn.access": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "my_app": {  # your app-level logger
            "handlers": ["console", "file"],
            "level": "DEBUG",  # Set to DEBUG for development
        },
    },
}
