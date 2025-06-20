from pathlib import Path

from src.base.base import BaseXML
from src.base.utils import get_isotime


class GetStateXML(BaseXML):
    """
    Формирование XML для получения статуса отправленного запроса
    """
    TEMPLATE = Path(__file__).resolve().parent / 'templates/getState.xml'
    def __init__(self) -> None:
        super().__init__(self.TEMPLATE)

    def set_message_guid(self, message_guid):
        self.get_element('//base:Date').text = get_isotime()
        elem = self.get_element('//base:getStateRequest/base:MessageGUID')
        elem.text = message_guid
