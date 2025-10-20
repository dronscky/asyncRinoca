from abc import abstractmethod
import copy
from datetime import datetime, timedelta
from pathlib import Path

from src.base.base import BaseXML, OperationMixin
from src.base.utils import gen_guid
from src.debt.schema import GISResponseDataFormat, RequestPeriod
from src.base.sign import SignedXML
from src.config import project_config
from src.log.log import logger

CERT = project_config.config.get('crypto', 'cert')
PRIVATE_KEY = project_config.config.get('crypto', 'key')
EXEC_GUID = project_config.config.get('guid', 'executor')


def get_period() -> RequestPeriod:
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
    return RequestPeriod(startDate=start_date, endDate=end_date)


class ExportDebtSubrequests(BaseXML, OperationMixin):
    """
    Формирование xml для запроса к порталу ГИС ЖКХ
    """
    TEMPLATE = Path(__file__).resolve().parent / 'templates/exportDebtSubrequests.xml'

    def __init__(self, sub) -> None:
        super().__init__(self.TEMPLATE)
        self.node = self.get_element('//*[@Id="signed-data-container"]')
        self.set_version('13.1.10.1')
        period = get_period()
        self.start = period.startDate
        self.end = period.endDate
        self.sub = sub
        self._build_body()

    def _set_period_of_sending_request(self):
        """
        Вносим период запроса
        """
        period_elements = {
            './/base:startDate': self.start,
            './/base:endDate': self.end
        }
        for path, value in period_elements.items():
            elem = self.get_element(path)
            elem.text = value

    def _build_body(self):
        """
        Формируем основное тело XML
        """
        self._set_period_of_sending_request()
        sub_request_guid = self.get_element('//drs:exportSubrequestGUID')
        if self.sub is None:
            self.node.remove(sub_request_guid)
        else:
            sub_request_guid.text = self.sub
        SignedXML(self.tree, CERT, PRIVATE_KEY)


class ImportDebtResponses(BaseXML, OperationMixin):
    """
    Формирование xml запроса с ответами к порталу ГИС ЖКХ
    """
    TEMPLATE = Path(__file__).resolve().parent / 'templates/importDebtResponses.xml'

    def __init__(self) -> None:
        super().__init__(self.TEMPLATE)
        self.node = self.get_element('//*[@Id="signed-data-container"]')
        self.set_version('14.0.0.0')

        resp_data = self.get_element('//drs:responseData')

        self.debt_info = self.get_element('//drs:debtInfo')

        self.attachment_file = self.get_element('//drs:document')
        self.debt_info.remove(self.attachment_file)

        resp_data.remove(self.debt_info)

        self.action = self.get_element('//drs:action')
        self.node.remove(self.action)

    @abstractmethod
    def _build_body(self):
        raise NotImplementedError


class SendImportDebtResponses(ImportDebtResponses):
    """
    Формирование xml запроса с ответами к порталу ГИС ЖКХ
    """

    def __init__(self, data: list[GISResponseDataFormat]) -> None:
        super().__init__()
        if len(data) > 100:
            logger.error(f'Ошибочный размер списка входного списка: {data}')
            raise TypeError
        self.data = data
        self._build_body()

    def _build_body(self):
        """
        Формируем блок action
        data - словарь с ключом subrequestGUID
        """
        ns = self.get_namespaces()

        for item in self.data:
            clone = copy.deepcopy(self.action)
            clone.find('base:TransportGUID', namespaces=ns).text = gen_guid()
            clone.find('drs:subrequestGUID', namespaces=ns).text = item.subrequestGUID
            clone.find('drs:actionType', namespaces=ns).text = 'Send'
            clone.find('drs:responseData/drs:description', namespaces=ns).text = ' '
            clone.find('drs:responseData/drs:executorGUID', namespaces=ns).text = EXEC_GUID
            if not item.debtorsData:
                clone.find('drs:responseData/drs:hasDebt', namespaces=ns).text = 'false'
            else:
                for debtors in item.debtorsData:
                    for name in debtors.persons:
                        clone.find('drs:responseData/drs:hasDebt', namespaces=ns).text = 'true'
                        # находим узел ResponseData для добавления информации о должниках
                        resp_data_node = clone.find('drs:responseData', namespaces=ns)
                        # клонируем узел debtInfo для каждого должника
                        debt_info_clone = copy.deepcopy(self.debt_info)
                        debt_info_clone.find('drs:person/drs:firstName', namespaces=ns).text = name.firstName
                        debt_info_clone.find('drs:person/drs:lastName', namespaces=ns).text = name.lastName
                        debt_info_clone.find('drs:person/drs:middleName', namespaces=ns).text = name.middleName

                        if files := debtors.files:
                            for file in files:
                                # клонируем узел attachmentFile для каждого файла
                                attachment_file_clone = copy.deepcopy(self.attachment_file)
                                attachment_file_clone.find('drs:attachment/base:Name',
                                                           namespaces=ns).text = file.name
                                attachment_file_clone.find('drs:attachment/base:Description',
                                                           namespaces=ns).text = file.desc
                                attachment_file_clone.find('drs:attachment/base:Attachment/base:AttachmentGUID',
                                                           namespaces=ns).text = file.attachmentGUID
                                attachment_file_clone.find('drs:attachment/base:AttachmentHASH',
                                                           namespaces=ns).text = file.attachmentHASH
                                debt_info_clone.append(attachment_file_clone)

                        # вставляем
                        resp_data_node.append(debt_info_clone)
            self.node.append(clone)
        SignedXML(self.tree, CERT, PRIVATE_KEY)


class RevokeImportDebtResponses(ImportDebtResponses):
    """
    Формирование xml запроса для отзыва отправленных ответов к порталу ГИС ЖКХ
    """

    def __init__(self, subrequests_guid: list[str]) -> None:
        super().__init__()
        if len(subrequests_guid) > 100:
            logger.error(f'Ошибочный размер списка входного списка: {subrequests_guid}')
            raise TypeError
        self.subrequests_guid = subrequests_guid
        self._build_body()

    def _build_body(self):
        """
        Формируем блок action
        data - словарь с ключом subrequestGUID
        """
        ns = self.get_namespaces()
        for subrequest_guid in self.subrequests_guid:
            clone = copy.deepcopy(self.action)
            clone.find('base:TransportGUID', namespaces=ns).text = gen_guid()
            clone.find('drs:subrequestGUID', namespaces=ns).text = subrequest_guid
            clone.find('drs:actionType', namespaces=ns).text = 'Revoke'
            clone.remove(clone.find('drs:responseData', namespaces=ns))
            self.node.append(clone)
        SignedXML(self.tree, CERT, PRIVATE_KEY)
