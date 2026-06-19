import asyncio

from src.api.db.db import execute_command, select_command
from src.debt.state import check_import_responses_state
from src.emails.emails import send_email_to_admins


async def get_response_requests():
    q = """
        select ack_guid
        from details_a
        where resp_status != 3
    """
    return await select_command(q)


async def delete_sent_subrequest():
    q = """
        delete from details_a where resp_status = 3 returning id
    """
    return await select_command(q)


async def update_status(ack_guid: str, status: int) -> None:
    q = """
        update details_a
        set resp_status = ?
        where ack_guid = ?
    """
    await execute_command(q, status, ack_guid)


async def check_status():
    response_requests = await get_response_requests()

    if response_requests:
        for response_ack in response_requests:
            status = await check_import_responses_state(response_ack[0])
            await update_status(response_ack[0], status)


def calc_deleted_rows(rows: list[tuple[int]]) -> int:
     return len(rows)


async def worker():
    await check_status()
    count_deleted_rows = await delete_sent_subrequest()
    send_email_to_admins('Отправлено положительных ответов', f'{calc_deleted_rows(count_deleted_rows)}')


if __name__ == '__main__':
    asyncio.run(worker())
