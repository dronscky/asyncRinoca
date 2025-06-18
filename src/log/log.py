import logging
import logging.config as lc
from pathlib import Path

path_log_info = Path(__file__).resolve().parent / 'info.log'
path_log_err = Path(__file__).resolve().parent / 'error.log'


class InfoLvlFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelname == 'INFO'


logger_config = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'std_format': {
            'format': '{name} - {asctime} - {levelname} - {module}: {funcName}: {lineno} - {message}',
            'style': '{'
        }
    },
    'handlers': {
        'err_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'ERROR',
            'filename': path_log_err,
            'formatter': 'std_format',
            'encoding': 'utf-8',
            'maxBytes': 102400,
            'backupCount': 3
        },
        'info_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'INFO',
            'filename': path_log_info,
            'formatter': 'std_format',
            'filters': ['info_lvl'],
            'encoding': 'utf-8',
            'maxBytes': 102400,
            'backupCount': 3
        }
    },
    'loggers': {
        'sys_logger': {
            'level': 'INFO',
            'handlers': ['err_file', 'info_file'],
            'propagate': False
        }
    },
    'filters': {
        'info_lvl': {
            '()': InfoLvlFilter
        }
    }
}


lc.dictConfig(logger_config)
logger = logging.getLogger('sys_logger')
