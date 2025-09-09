from dataclasses import astuple
from datetime import datetime
from typing import Optional

from gspread_asyncio import (AsyncioGspreadClient,
                             AsyncioGspreadWorksheet)
from gspread_formatting import (BooleanCondition,
                                CellFormat,
                                DataValidationRule,
                                format_cell_range,
                                set_data_validation_for_cell_range,
                                set_column_widths,
                                set_frozen)

from src.api.gdrive.db import create_db_record_about_report
from src.api.gdrive.gsheet import (HeaderMixin,
                                   connect_google_api,
                                   cast_column_to_A1_note,
                                   share_spreadsheet)
from src.api.gdrive.schema import GReportAttributes
from src.emails.emails import get_email_addresses
from src.debt.schema import SubrequestCheckDetails
from src.log.log import logger


COLS_WIDTH = {
    'Адрес': 400,
    'Должники': 400
}


class WorksheetHeader(HeaderMixin):
    TITLE_COLUMNS = ['Дата запроса', 'Срок ответа', 'requestguid', 'ФИАС', 'Адрес', 'Помещение', 'Должники',
                     'Первичный лс', 'ЗСП номер', 'Дата ЗСП', '№ Судебного приказа', 'СП задолженность', 'СП пени', 'Госпошлина', 'Всего',
                     'Бухгалтерия']


@connect_google_api('rinoca')
async def create_spreadsheet(title: str, rows: list[SubrequestCheckDetails], client: AsyncioGspreadClient) -> None:
    ss = await client.create(title)
    ws = await ss.get_worksheet(0)
    await form_worksheet(ws, rows)
    emails = get_email_addresses('gmails')
    await share_spreadsheet(client, ss.id, emails)
    logger.info(f'Документ ID "{ss.id}" и названием "{title}" создан!')
    # запись в БД информации о файле отчета
    date = datetime.now().strftime('%d-%m-%Y')
    await create_db_record_about_report(GReportAttributes(date, ss.id, title))


async def form_worksheet(ws: AsyncioGspreadWorksheet, rows: list[SubrequestCheckDetails]) -> None:
    wh = WorksheetHeader()

    async def _protect_cells(far_cell: str):
        """Защита области ячеек"""
        protect_range = f'A1:{far_cell}'
        await ws.add_protected_range(protect_range, None)

    async def _set_validation(col_name: str, values: list[str]):
        """Создание Data Validation ячеек
            :param range в нотации А1, т.е. 'C1:C3'
        """
        _rule = DataValidationRule(BooleanCondition('ONE_OF_LIST', values),
                                   showCustomUi=True)
        col = wh.get_col_letter_by_title(col_name)
        _range = f'{col}{3}:{col}{len(rows) + wh.COUNT_HEADER_ROWS}'
        set_data_validation_for_cell_range(ws.ws, _range, _rule)

    await ws.append_rows([astuple(row) for row in rows])
    await ws.insert_cols([[]], wh.COUNT_HEADER_COLUMNS)
    await ws.insert_rows(wh.HEADER)

    fmt = CellFormat(horizontalAlignment='CENTER')
    format_cell_range(ws.ws, f'A{wh.COUNT_HEADER_ROWS}:{cast_column_to_A1_note(wh.COUNT_HEADER_COLUMNS)}{wh.COUNT_HEADER_ROWS}', fmt)
    # фиксируем 2 первые строки
    set_frozen(ws.ws, wh.COUNT_HEADER_ROWS)
    # устанавливаем ячейки с валидацией
    await _set_validation('Бухгалтерия', ['Имеется', 'Погашена'])
    # фиксируем ширину столбцов из COLS_WIDTH
    set_column_widths(ws.ws, [(wh.get_col_letter_by_title(k), v) for k, v in COLS_WIDTH.items()])
    # скрываем колонки с технической информацией
    await ws.hide_columns(2, 4)
    # защищаем лист от изменений за исключением последней колонки
    await _protect_cells(f'{cast_column_to_A1_note(wh.COUNT_HEADER_COLUMNS - 1)}{len(rows) + wh.COUNT_HEADER_ROWS}')


@connect_google_api('rinoca')
async def get_worksheet_data(ss_id: str, client: AsyncioGspreadClient) -> Optional[list[SubrequestCheckDetails]]:
    ss = await client.open_by_key(ss_id)
    ws = await ss.get_worksheet(0)
    wh = WorksheetHeader()
    values = await ws.get_values()
    return [SubrequestCheckDetails(*row) for row in values[wh.COUNT_HEADER_ROWS:]]


@connect_google_api('rinoca')
async def form_curr_worksheet(ss_id: str, rows: list[SubrequestCheckDetails], client: AsyncioGspreadClient) -> None:
    ss = await client.open_by_key(ss_id)
    ws = await ss.get_worksheet(0)
    await ws.clear()
    await form_worksheet(ws, rows)
