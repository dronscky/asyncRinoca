from datetime import datetime
from pathlib import Path

import gspread
from gspread_formatting import BooleanCondition, CellFormat, DataValidationRule, format_cell_range, \
    set_data_validation_for_cell_range, set_column_widths, set_frozen
from oauth2client.service_account import ServiceAccountCredentials

from src.api.gdrive.db import *
from src.api.gdrive.schema import GData, GReportAttributes
from src.emails import get_email_addresses
from src.log.log import logger


class GoogleSpreadSheetAPI:
    """Подключение к Google Sheets API"""

    def __init__(self) -> None:
        conf_path = Path(__file__).resolve().parent / 'creds.json'
        creds = ServiceAccountCredentials.from_json_keyfile_name(conf_path)
        self.client = gspread.authorize(creds)

    @staticmethod
    def _get_column_letter(col_num: int) -> str:
        """каст в А1 нотификацию"""
        return chr(ord('A') + col_num - 1)


class OpenGoogleSpreadSheet(GoogleSpreadSheetAPI):
    """Открытие таблицы"""

    def __init__(self, id) -> None:
        """
        :param id - файла
        """
        super().__init__()
        self.id = id
        self.spreadsheet = self.client.open_by_key(self.id)
        self.sheet = self.spreadsheet.sheet1

    def get_data(self) -> list[GData]:
        """
        Получить данные необходимых полей
        """
        result_data = []
        if self.sheet is not None:
            sheet_data = [SheetOutData(*x[:17]) for x in self.sheet.get_values()]

            for row in sheet_data[2:]:
                result_data.append(GData(row.sent_date,
                                         row.response_date,
                                         row.requestguid,
                                         row.persons,
                                         row.sp_no,
                                         row.buh,
                                         row.comment))
            return result_data
        else:
            raise ConnectionError('Страница не создана!')

    def delete_spreadsheet(self):
        """Удалить таблицу"""
        self.client.del_spreadsheet(self.id)
        delete_db_record_about_report(self.id)


class NewGoogleSpreadSheet(GoogleSpreadSheetAPI, TableHeader):
    """Новая Google таблица"""

    def __init__(self, title: str) -> None:
        """
        :param title - Имя таблицы
        """
        super().__init__()
        self.title = title
        self.spreadsheet = self.client.create(self.title)
        self.sheet = self.spreadsheet.sheet1

    def _fill_spreadsheet(self, data: list[SheetInData]):
        """Заполнить таблицу"""
        # добавляем основные данные
        self.sheet.append_rows([[], [], *data])
        self.sheet.insert_cols([[], [], []], 14)
        # добавляем шапку с номерами столбцов
        self.sheet.insert_rows(self.header)
        # номера столбцов центрируем
        fmt = CellFormat(horizontalAlignment='CENTER')
        format_cell_range(self.sheet, 'A2:N2', fmt)
        # фиксируем 2 первые строки
        set_frozen(self.sheet, 2)
        # определяем количество строк и колонок в документе
        self.rows_count, self.columns_count = self._get_table_size()
        # устанавливаем ячейки с валидацией
        self._set_validation()
        # фиксируем ширину столбцов 4х колонок: Адрес, Должники, судебный участок, № приказа
        set_column_widths(self.sheet, [(self._get_column_letter(5), 450),
                                       (self._get_column_letter(7), 250),
                                       (self._get_column_letter(13), 180),
                                       (self._get_column_letter(17), 450)])
        # сортировка по колонке 'Судебный участок'
        sort_range = f'A3:{self._get_column_letter(self.columns_count)}{self.rows_count}'
        self._sort_sheet(17, sort_range)
        # скрываем колонки с технической информацией
        self.sheet.hide_columns(2, 4)
        # защищаем лист от изменений за исключением последних двух колонок
        self._protect_cells()

    def _share_spreadsheet(self, emails: set):
        """Предоствление доступа к отчету"""
        for email in emails:
            self.spreadsheet.share(email, perm_type='user', role='writer', notify=False)

    def _set_validation(self):
        """Создание Data Validation ячеек
            :param range в нотации А1, т.е. 'C1:C3'
        """
        buh_rule = DataValidationRule(BooleanCondition('ONE_OF_LIST', ['Имеется', 'Погашена', 'Неизвестно']),
                                      showCustomUi=True)
        low_rule = DataValidationRule(BooleanCondition('ONE_OF_LIST', ['Наличие', 'Отменён', 'Неизвестно']),
                                      showCustomUi=True)
        buh_column = self._get_column_letter(14)
        low_column = self._get_column_letter(15)
        buh_range = f'{buh_column}{3}:{buh_column}:{self.rows_count}'
        low_range = f'{low_column}{3}:{low_column}:{self.rows_count}'

        set_data_validation_for_cell_range(self.sheet, buh_range, buh_rule)
        set_data_validation_for_cell_range(self.sheet, low_range, low_rule)

    def _protect_cells(self):
        """Защита области ячеек"""
        all_protect_column = self._get_column_letter(13)
        all_protect_range = f'A3:{all_protect_column}{self.rows_count}'
        self.sheet.add_protected_range(all_protect_range, None)

        buh_protect_column = self._get_column_letter(14)
        buh_protect_range = f'{buh_protect_column}3:{buh_protect_column}{self.rows_count}'
        self.sheet.add_protected_range(buh_protect_range,
                                       get_email_addresses('configurations/emails.json', 'gmails', 'buh'))
        low_protect_column = self._get_column_letter(15)
        low_protect_range = f'{low_protect_column}3:{low_protect_column}{self.rows_count}'
        self.sheet.add_protected_range(low_protect_range,
                                       get_email_addresses('configurations/emails.json', 'gmails', 'lowyer'))

    def _get_table_size(self):
        """Получаем количество строк и колонок в таблице"""
        column_count = len(self.sheet.row_values(1))
        row_count = len(self.sheet.col_values(1))
        return row_count, column_count

    def _sort_sheet(self, col_num: int, range):
        """Сортировка по определенному столбцу
        :param col_num - номер столбца
        """
        self.sheet.sort((1, 'asc'), (col_num, 'asc'), range=range)

    def generate(self, data: list[SheetInData]) -> None:
        """Создание документа в облаке, доступ
        """
        emails = get_email_addresses('gmails')
        self._fill_spreadsheet(data)
        self._share_spreadsheet(emails)

        # запись в БД информации о файле отчета
        date = datetime.now().strftime('%d-%m-%Y')
        create_db_record_about_report(GReportAttributes(date, self.spreadsheet.id, self.title))
