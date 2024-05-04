import logging
import logging.config
import os

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

log_file_path = "/var/log/fastapi.log"
log_file_max_size = 1024 * 1024 * 3
log_file_backup_count = 5

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": True,
    "formatters": {
        "standard": {"format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"},
    },
    "handlers": {
        "default": {
            "level": "INFO",
            "formatter": "standard",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",  # Default is stderr
        },
        "file": {
            "level": "INFO",
            "formatter": "standard",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": log_file_path,
            "maxBytes": log_file_max_size,
            "backupCount": log_file_backup_count,
            "encoding": "utf8",
        },
    },
    "loggers": {
        "": {  # root logger
            "level": LOG_LEVEL,
            "handlers": ["default", "file"],
            "propagate": False,
        },
        "uvicorn.error": {
            "level": LOG_LEVEL,
            "handlers": ["default", "file"],
        },
    },
}

logging.config.dictConfig(LOGGING_CONFIG)


logger = logging.getLogger(__name__)
