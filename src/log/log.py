import logging
import logging.config as lc
from pathlib import Path

from src.config import project_config

path_log_info = Path(__file__).resolve().parent.parent.parent / 'log/info.log'
path_log_err = Path(__file__).resolve().parent.parent.parent / 'log/error.log'


class InfoLvlFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelname == 'INFO'


class ErrorLvlFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelname == 'ERROR'


logger_config = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'std_format': {
            'format': '{name} - {asctime} - {levelname} - {module}: {funcName}: {lineno} - {message}',
            'style': '{'
        },
        'email_format': {
            'format': '🚨 ОШИБКА В СИСТЕМЕ 🚨\n\n'
                      '📅 Время: {asctime}\n'
                      '🏷️ Логгер: {name}\n'
                      '🚨 Уровень: {levelname}\n'
                      '📁 Модуль: {module}\n'
                      '🔢 Строка: {lineno}\n'
                      '📝 Сообщение: {message}\n\n'
                      '---\n'
                      'Автоматическое уведомление системы',
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
        },
        'email_handler': {
            '()': 'logging.handlers.SMTPHandler',
            'level': 'ERROR',
            'formatter': 'email_format',
            'filters': ['error_lvl'],
            'mailhost': (project_config.config.get('email', 'smtp_server'),
                         project_config.config.get('email', 'smtp_port')),
            'fromaddr': project_config.config.get('email', 'sender_email'),
            'toaddrs': project_config.config.get('email', 'admin_emails').split(','),
            'subject': '🚨 Ошибка в приложении asyncRinoca12',
            'credentials': (project_config.config.get('email', 'sender_email'),
                            project_config.config.get('email', 'password')),
            'secure': (),
            'timeout': 30
        }
    },
    'loggers': {
        'sys_logger': {
            'level': 'INFO',
            'handlers': ['err_file', 'info_file', 'email_handler'],
            'propagate': False
        }
    },
    'filters': {
        'info_lvl': {
            '()': InfoLvlFilter
        },
        'error_lvl': {
            '()': ErrorLvlFilter
        }
    }
}


lc.dictConfig(logger_config)
logger = logging.getLogger('sys_logger')
