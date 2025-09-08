import lxml.etree as ET

from src.base.base import ParseXMLMixin
from src.log.log import logger


class ReaderXML(ParseXMLMixin):
    """
        Парсер данных из xml ответа cервера
    """
    def __init__(self, xml: str):
        try:
            self.tree = ET.fromstring(xml.encode('utf-8'))
        except Exception:
            logger.error(f'Ошибка чтения XML: {xml}')
            raise


class ReaderAckRequest(ReaderXML):
    def __init__(self, xml):
        super().__init__(xml)
        self.xml = xml

    def get_ack_request(self):
        if (ack:=self.get_element('//ns4:Ack/ns4:MessageGUID')) is not None:
            return ack.text
        logger.error(f'Некорректный Ack-ответ на запрос: {self.xml}')
        raise


def get_ack_message_guid(ack_xml):
    reader = ReaderAckRequest(ack_xml)
    return reader.get_ack_request()


class ReaderAckImportResponses(ReaderXML):
    def __init__(self, xml):
        super().__init__(xml)
        self.xml = xml

    def get_ack_import_responses(self) -> int | str:
        ack = self.get_element('//ns4:RequestState')
        error_desc = self.get_element('//ns13:importResult/ns4:Error/ns4:Description')
        if error_desc is None:
            return ack.text
        else:
            return error_desc.text


def get_ack_import_responses_state(ack_xml) -> int:
    reader = ReaderAckImportResponses(ack_xml)
    return reader.get_ack_import_responses()
