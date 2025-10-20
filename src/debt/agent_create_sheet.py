import asyncio
from datetime import datetime
from typing import Optional

from src.api.db.db import select_command, executemany_command
from src.debt.gsheet import create_spreadsheet
from src.debt.schema import SubrequestCheckDetails
from src.emails.emails import send_email_to_buhs
from src.log.log import logger


async def _get_check_subrequests() -> Optional[list[SubrequestCheckDetails]]:
    sql = """
        select sent_date, response_date, subrequestguid, fias, address, apartment, 
               persons, account, doc_arm_number, doc_date, case_number, sum_debt, penalty, duty, total
        from details_a
        where is_exp = 0
    """
    if fetch := await select_command(sql):
        return [SubrequestCheckDetails(*row) for row in fetch]
    return None


async def _update_subrequests_status(subrequestsguid: list[tuple[str]]) -> None:
    sql = """
        update details_a set is_exp = 1
        where subrequestguid = ?
    """
    await executemany_command(sql, subrequestsguid)


async def _check_date(date: str):
    q = "select * from holidays where date = ?"
    return await select_command(q, date)


async def its_holiday() -> bool:
    today = datetime.now()
    if today.weekday() in (5, 6) or await _check_date(today.strftime("%Y-%m-%d")):
        return True
    else :
        return False


async def _create_spreadsheet(data: list[SubrequestCheckDetails]) -> None:
    title = f'Отчет на проверку {datetime.now().strftime('%y-%m-%d')}'
    try:
        if await its_holiday():
            return None

        await create_spreadsheet(title, data)
        m = f'Отчет "{title}" сформирован {datetime.now()}'
        logger.info(m)
        send_email_to_buhs(title, m)
    except Exception as e:
        logger.error(e)
        raise


async def handler():
    if rows := await _get_check_subrequests():
        await _create_spreadsheet(rows)
        await _update_subrequests_status([(row.subrequestguid,) for row in rows])
    else:
        logger.info(f'Запросы не найдены для проверки!')


if __name__ == '__main__':
    asyncio.run(handler())
