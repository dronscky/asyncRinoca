import asyncio

from src.debt.mreport.manage_report import get_requests_data, form_curr_worksheet


async def handler():
    report_data = await get_requests_data()
    await form_curr_worksheet(report_data)


if __name__ == '__main__':
    asyncio.run(handler())
