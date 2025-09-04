from dataclasses import dataclass
from typing import Optional

from src.base.reader import ReaderXML
from src.debt.schema import SubrequestData
from src.log.log import logger


def remove_tz(date: str) -> str:
    """
    Преобразование типа даты с часовым поясом ('2023-07-01+03:00') на тип даты ('2023-07-01')
    """
    return date.split('+')[0]


def num_apartment(val: str | None) -> str:
    """
    Получаем номер квартиры
    """
    # val = val.strip()
    if val:
        if 'кв.' in val:
            return val.replace('кв.', '').strip()
        elif  'кв' in val:
            return val.replace('кв', '').strip()
        else:
            return val
    else:
        return ''


@dataclass(frozen=True)
class ExportDSRsData:
    """
    Ответ портала с перечнем подзапросов
    """
    next: str
    messageGUID: str
    subrequests: list[SubrequestData]


class ReaderExportDSRsResult(ReaderXML):
    def __init__(self, xml: str):
        super().__init__(xml)
        self.xml = xml
        self.ns = self.get_namespaces()

    def get_exportDSRsData(self) -> Optional[ExportDSRsData] | str:
        if (request_state := self.get_element('//ns4:RequestState')) is not None:
            request_state_val = request_state.text
            if request_state_val == '3':
                message_guid = self.get_element('//ns4:MessageGUID').text
                error_desc = self.get_element('//ns4:ErrorMessage/ns4:Description')
                if error_desc is None:
                    last_page = self.get_element('//ns13:lastPage')
                    if last_page is not None:
                        next_sub = 'last'
                    else:
                        next_guid = self.get_element('//ns13:nextSubrequestGUID')
                        next_sub = next_guid.text

                    subrequests = self.get_elements('//ns13:subrequestData')
                    subrequests_data = []
                    for subrequest in subrequests:
                        subrequest_guid = subrequest.find('ns13:subrequestGUID',namespaces=self.ns).text
                        if (sent_date_elem := subrequest.find('.//ns13:sentDate', namespaces=self.ns)) is not None:
                            sent_date = remove_tz(sent_date_elem.text)
                        else:
                            sent_date = None

                        if (response_date_elem := subrequest.find('.//ns13:responseDate', namespaces=self.ns)) is not None:
                            response_date = response_date_elem.text
                        else:
                            response_date = None

                        if (fias_house_elem := subrequest.find('.//ns13:fiasHouseGUID', namespaces=self.ns)) is not None:
                            fias_house = fias_house_elem.text
                        else:
                            fias_house = None

                        if (address_elem := subrequest.find('.//ns13:address', namespaces=self.ns)) is not None:
                            address = address_elem.text
                        else:
                            address = ''

                        if (apartment_elem := subrequest.find('.//ns13:addressDetails', namespaces=self.ns)) is not None:
                            apartment = num_apartment(apartment_elem.text)
                        else:
                            apartment = ''

                        subrequests_data.append(SubrequestData(subrequestGUID=subrequest_guid,
                                                               sentDate=sent_date,
                                                               responseDate=response_date,
                                                               fiasHouseGUID=fias_house,
                                                               address=address,
                                                               apartment=apartment))

                    return ExportDSRsData(next=next_sub, messageGUID=message_guid, subrequests=subrequests_data)
                else:
                    if error_desc.text != 'Нет объектов для экспорта':
                        logger.error(error_desc.text)
                        raise ValueError(error_desc.text)
                    return None
            else:
                return 'wait'
        else:
            logger.error(f'Неверный XML документ: {self.xml}')
            raise


def get_exportDSRsData(export_state_xml: str) -> Optional[ExportDSRsData] | str:
    reader = ReaderExportDSRsResult(export_state_xml)
    return reader.get_exportDSRsData()
