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
