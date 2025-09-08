import asyncio

from src.base.delay import get_delay_time
from src.base.reader import get_ack_import_responses_state
from src.base.state import GetStateXML
from src.debt.service import state_request
from src.log.log import logger


async def check_import_responses_state(message_guid: str) -> int:
    state_imp = GetStateXML()
    state_imp.set_message_guid(message_guid)
    attempt_count = 0
    while True:
        ack = await state_request(state_imp.get_xml())
        state = get_ack_import_responses_state(ack)
        if state == '3':
            logger.info('Успешный импорт ответов на запрос')
            return 1
        elif state in ('1', '2'):
            await asyncio.sleep(get_delay_time(attempt_count))
            attempt_count += 1
            if attempt_count == 5:
                logger.error('Количество попыток на проверку состояния превышено!')
                raise
        else:
            logger.error(f'Ошибка обработки: {state}')
            raise
