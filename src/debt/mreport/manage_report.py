import asyncio
from dataclasses import dataclass, astuple
from enum import Enum
from typing import Optional, Any, Literal

from gspread_asyncio import AsyncioGspreadClient, AsyncioGspreadWorksheet
from gspread_formatting import (Border,
                                Borders,
                                CellFormat,
                                Color,
                                format_cell_range,
                                set_column_width,
                                TextFormat,
                                NumberFormat)

from src.api.db.db import select_command
from src.api.gdrive.gsheet import connect_google_api, HeaderMixin, cast_column_to_A1_note


@dataclass
class MonthStat:
    month: str
    total: int
    no_debts: int
    debts: int

    def __post_init__(self):
        self.total = int(self.total)
        self.no_debts = int(self.no_debts)
        self.debts = int(self.debts)


async def get_requests_data() -> Optional[list[MonthStat]]:
    sql = """
                SELECT *
                FROM (
                        SELECT 
                            COALESCE(period, 'ИТОГО') as 'Период',
                            SUM(total) as 'Поступило запросов',
                            SUM(total - debt) as 'Отсутствует задолженность',
                            SUM(debt) as 'Имеется задолженность'
                        FROM (
                                SELECT 
                                   s.period,
                                   s.total,
                                   s.debt
                                FROM statistics s
                                
                                UNION ALL
                                
                                SELECT
                                   DATE_FORMAT(sent_date, '%m.%Y') AS period,
                                   COUNT(*)  as total,
                                   SUM(CASE WHEN answer = 'Имеется' THEN 1 ELSE 0 END) AS debt
                                FROM requests
                                GROUP BY DATE_FORMAT(sent_date, '%m.%Y')
                        ) AS q
                        GROUP BY period WITH ROLLUP
                ) q1
                ORDER BY 
                            CASE WHEN `Период` = 'ИТОГО' THEN 1 ELSE 0 END,
                            STR_TO_DATE(CONCAT('01.', `Период`), '%d.%m.%Y')
    """
    if f := await select_command(sql):
        return [MonthStat(*row) for row in f]
    return []


@connect_google_api('sah')
async def form_curr_worksheet(rows: list[tuple[str, Any,...]], client: AsyncioGspreadClient) -> None:
    ss = await client.open_by_key('1IdZrojSSkSzSjoqKpqHodmtcZUCEUPfWPltMDHi_FI0')
    ws = await ss.get_worksheet_by_id(1476917212)
    await ws.clear()
    await form_worksheet(ws, rows)


class WorksheetHeader(HeaderMixin):
    TITLE_COLUMNS = ['Период', 'Поступило запросов', 'Отсутствует задолженность', 'Имеется задолженность']


async def form_worksheet(ws: AsyncioGspreadWorksheet, rows: list[tuple[str, Any,...]]) -> None:
    wh = WorksheetHeader()

    class LineType(Enum):
        SOLID_THICK = 1
        SOLID = 2

    def _set_style(font_weight: bool, line: LineType, h_alignment: Literal['CENTER', 'RIGHT'] = 'RIGHT'):
        return CellFormat(textFormat=TextFormat(bold=font_weight),
                          horizontalAlignment=h_alignment,
                          numberFormat=NumberFormat(type='NUMBER', pattern='#,##'),
                          borders=Borders(top=Border(line, Color(0,0,0)),
                                          bottom=Border(line, Color(0,0,0)),
                                          left=Border(line, Color(0,0,0)),
                                          right=Border(line, Color(0,0,0))))

    def _set_table_style():
        header_fmt = _set_style(True, 'SOLID', 'CENTER')
        body_fmt = _set_style(False, 'SOLID')
        format_cell_range(ws.ws, f'A1:{cast_column_to_A1_note(wh.COUNT_HEADER_COLUMNS)}{wh.COUNT_HEADER_ROWS}', header_fmt)
        format_cell_range(ws.ws, f'A3:D{len(rows) + 2}', body_fmt)

    await ws.resize(1,1)
    await ws.append_rows([astuple(row) for row in rows])
    await ws.insert_rows(wh.HEADER)

    set_column_width(ws.ws, 'B', 125)
    set_column_width(ws.ws, 'C', 180)
    set_column_width(ws.ws, 'D', 160)
    _set_table_style()
