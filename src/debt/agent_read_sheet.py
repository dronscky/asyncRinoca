import asyncio
from typing import Optional

from src.api.gdrive.schema import GReportAttributes
from src.api.gdrive.gsheet import delete_spreadsheet_by_id
from src.api.db.db import select_command, execute_command
from src.debt.gsheet import get_worksheet_data, form_curr_worksheet
from src.debt.schema import SubrequestCheckDetails


async def get_spreadsheets_attrs() -> Optional[tuple[GReportAttributes, ...]]:
    sql = """
        SELECT form_date, report_id, title, comment
        FROM ext_reports
        WHERE str_to_date(form_date, '%d-%m-%Y') < CURRENT_DATE()
    """
    if fetch := await select_command(sql):
        return tuple(GReportAttributes(*row) for row in fetch)
    return None


async def update_subrequest_status(subrequestguid: str) -> None:
    sql = """
        update details_a set is_debt = 1
        where subrequestguid = ? 
    """
    await execute_command(sql, subrequestguid)


async def delete_subrequest(subrequestguid: str) -> None:
    sql = """
        delete from details_a 
        where subrequestguid = ? 
    """
    await execute_command(sql, subrequestguid)


async def delete_report(report_id: str) -> None:
    sql = """
        delete from ext_reports
        where report_id = ? 
    """
    await execute_command(sql, report_id)


async def process_report_row(subrequest_details: SubrequestCheckDetails) -> Optional[SubrequestCheckDetails]:
            match subrequest_details.buh:
                case 'Имеется':
                    await update_subrequest_status(subrequest_details.subrequestguid)
                case 'Погашена':
                    await delete_subrequest(subrequest_details.subrequestguid)
                case _:
                    return subrequest_details
            return None


async def handler():
    if spreadsheets := await get_spreadsheets_attrs():
        for ss in spreadsheets:
            ss_data = await get_worksheet_data(ss.report_id)
            if not ss_data:
                await delete_spreadsheet_by_id(ss.report_id)
                await delete_report(ss.report_id)
                continue

            unprocessed_requests = []
            for row in ss_data:
                if subrequest_details := await process_report_row(row):
                    unprocessed_requests.append(subrequest_details)

            if unprocessed_requests:
                await form_curr_worksheet(ss.report_id, unprocessed_requests)
            else:
                await delete_spreadsheet_by_id(ss.report_id)
                await delete_report(ss.report_id)


if __name__ == '__main__':
    asyncio.run(handler())
