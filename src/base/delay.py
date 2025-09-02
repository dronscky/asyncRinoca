from src.log.log import logger


def get_delay_time(attempt: int) -> int:
    match attempt:
        case 0:
            delay = 30
            logger.info('Пауза 30 сек...')
        case 1:
            delay = 60
            logger.info('Пауза 60 сек...')
        case 2:
            delay = 90
            logger.info('Пауза 90 сек...')
        case _:
            delay = 180
            logger.info('Пауза 180 сек...')
    return delay
