import asyncio
from functools import wraps
from pathlib import Path
from typing import Iterable, Optional

from google.oauth2.service_account import Credentials
from gspread import exceptions
from gspread_asyncio import (AsyncioGspreadClientManager,
                             AsyncioGspreadWorksheet,
                             AsyncioGspreadClient)

from src.log.log import logger


def cast_column_to_A1_note(col_num: int) -> str:
    """каст в А1 нотификацию"""
    return chr(ord('A') + col_num - 1)


class GoogleAsyncAPI:
    """Google Sheets API"""

    def __init__(self, gc: AsyncioGspreadClient) -> None:
        if isinstance(gc, AsyncioGspreadClient):
            self._gc = gc
        else:
            logger.error(f'Неверно проинициализирован экземпляр класса {super()}')
            raise

    @classmethod
    async def create(cls):
        def _get_creds():
            conf_path = Path(__file__).resolve().parent.parent.parent.parent / 'conf/creds.json'
            creds = Credentials.from_service_account_file(str(conf_path))
            scoped = creds.with_scopes([
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
            ])
            return scoped

        agcm = AsyncioGspreadClientManager(_get_creds)
        agc = await agcm.authorize()
        return cls(agc)

    @property
    def client(self):
        return self._gc


def connect_google_api(f):
    @wraps(f)
    async def wrapper(*args, **kwargs):
        con = await GoogleAsyncAPI.create()
        gc = con.client
        res = await f(*args, client=gc, **kwargs)
        return res
    return wrapper


@connect_google_api
async def delete_spreadsheets_by_title(title: str, client: AsyncioGspreadClient):
    count = 0
    while True:
        try:
            s = await client.open(title)
            await client.del_spreadsheet(s.id)
            count += 1
        except exceptions.SpreadsheetNotFound:
            logger.info(f'Удалено {count} файлов с названием: "{title}"')
            break


@connect_google_api
async def delete_spreadsheet_by_id(spreadsheet_id: str, client: AsyncioGspreadClient):
    """Удалить таблицу"""
    await client.del_spreadsheet(spreadsheet_id)


async def share_spreadsheet(gc: AsyncioGspreadClient, ss_id: str, emails: Iterable[str]):
    """Предоставление доступа к отчету"""
    tasks = [gc.insert_permission(ss_id, email, perm_type='user', role='writer', notify=False) for email in emails]
    await asyncio.gather(*tasks)


async def get_ws_size(ws: AsyncioGspreadWorksheet):
    column_count = len(await ws.row_values(1))
    row_count = len(await ws.col_values(1))
    return row_count, column_count


class HeaderMixin:
    TITLE_COLUMNS = []
    def __init__(self):
        self.COUNT_HEADER_COLUMNS = len(self.TITLE_COLUMNS)
        self.HEADER = [self.TITLE_COLUMNS, [str(i + 1) for i in range(len(self.TITLE_COLUMNS))]]
        self.COUNT_HEADER_ROWS = len(self.HEADER)

    def get_col_letter_by_title(self, title: str) -> Optional[str]:
        for i, v in enumerate(self.TITLE_COLUMNS):
            if v == title:
                return cast_column_to_A1_note(i + 1)
        return None
