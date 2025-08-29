from configparser import ConfigParser
from pathlib import Path

from src.log.log import logger


class RinocaConfig:
    def __init__(self):
        self.config = ConfigParser()
        self.file = Path(__file__).resolve().parent / 'config.ini'
        self.struct = {
            'crypto': {
                'openssl': '',
                'cert': '',
                'key': ''
            },
            'guid': {
                'org': '',
                'executor': ''
            },
            'connect': {
                'host': '',
                'port': ''
            },
            'mobill': {
                'key': ''
            },
            'email': {
                'sender_email': '',
                'password': '',
                'smtp_server': '',
                'smtp_port': ''
            }
        }
        # Чтение конфигурационного файла
        if self.file.exists():
            self.config.read(self.file)

        else:
            self._create_empty_config()

        # Проверка на наличие необходимых секций
        self._check_integrity_config()

    def _create_empty_config(self):
        """
        Создание пустого дерева параметров конфигурации
        """
        for k, v in self.struct.items():
            self.config[k] = v
        logger.info('Создан пустой конфигурационный файл. Необходимо его заполнить.')
        self._save_config_file()

    def _check_integrity_config(self) -> None:
        """
        Проверка на наличие необходимых параметров конфигурации
        """
        for section, options in self.struct.items():
            if section not in self.config.sections():
                self.config[section] = options
                logger.error(f'Добавлена необходимая секция {section} с пустыми атрибутами в конфигурационный файл')
                self._save_config_file()
                raise
            for k, v in options.items():
                if k not in self.config[section].keys():
                    self.config[section][k] = v
                    self._save_config_file()
                    logger.error(f'Добавлен пустой атрибут {k} в секцию {section} в конфигурационный файл. Пропишите значение')
                    raise
                if self.config[section][k] == '':
                    logger.error(f'Отсутствует значение атрибута {k} в секции {section} в конфигурационный файле')
                    raise


    def _save_config_file(self) -> None:
        with open(self.file ,'w') as f:
            self.config.write(f)


try:
    project_config = RinocaConfig()
except:
    logger.error('Ошибка в конфигурационном файле!')
    raise Exception('Ошибка в конфигурационном файле!')
