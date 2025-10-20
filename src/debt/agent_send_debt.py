import asyncio

from typing import Optional

from src.api.db.db import select_command, executemany_command, execute_command

from src.base.reader import get_ack_message_guid

from src.debt.debt_xml import RevokeImportDebtResponses, SendImportDebtResponses
from src.debt.mobill import get_responses_data
from src.debt.schema import GISResponseDataFormat, SubrequestData
from src.debt.service import import_debt_responses
from src.debt.state import check_import_responses_state
from src.log.log import logger
from src.emails.emails import send_email_to_admins
from src.utils import counter


async def get_debt_requests() -> Optional[list[SubrequestData]]:
    sql = """
        select subrequestguid, sent_date, response_date, fias, address, apartment
        from details_a
        where is_debt = 1
        group by subrequestguid, sent_date, response_date, fias, address, apartment
    """
    if fetch := await select_command(sql):
        return [SubrequestData(*row) for row in fetch]
    return None


async def delete_responses(requests: list[SubrequestData] | SubrequestData) -> None:
    sql = """
        delete from details_a
        where subrequestguid = ?
    """
    if isinstance(requests, list):
        await executemany_command(sql, [(request.subrequestGUID,) for request in requests])
    else:
        await execute_command(sql, requests.subrequestGUID)


async def worker() -> None:
    batch_size = 100
    tasks = []

    if debt_requests := await get_debt_requests():
        for i in range(0, len(debt_requests), batch_size):
            batch = debt_requests[i:i + batch_size]
            tasks.append(_response_handler(batch))

    await asyncio.gather(*tasks, return_exceptions=True)
    send_email_to_admins('Отправлено положительных ответов', f'{counter.get_debtor_subrequests()}')


async def _response_handler(requests: list[SubrequestData]) -> None:
    if await _revoke_responses(requests):
        response_data = await get_responses_data(requests, getfile=True)
        if await _send_debt_responses(response_data):
            await delete_responses(requests)


async def _revoke_responses(requests: list[SubrequestData]):
    """
    Отзыв ответов отправленных на портал
    :param requests: длина списка не должна превышать 100, согласно ограничениям ГИС ЖКХ
    :return:
    """
    revoke = RevokeImportDebtResponses([request.subrequestGUID for request in requests])
    ack = await import_debt_responses(revoke.get_xml())
    ack_guid = get_ack_message_guid(ack)
    return await check_import_responses_state(ack_guid)


async def _send_debt_responses(responses_data: list[GISResponseDataFormat]):
    """
    Отправка положительных ответов на портал
    :param responses_data: длина списка не должна превышать 100, согласно ограничениям ГИС ЖКХ
    :return:
    """
    debt = SendImportDebtResponses(responses_data)
    ack = await import_debt_responses(debt.get_xml())
    ack_guid = get_ack_message_guid(ack)
    await asyncio.sleep(10)
    return await check_import_responses_state(ack_guid)


if __name__ == '__main__':
    asyncio.run(worker())
