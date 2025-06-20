from pathlib import Path

import lxml.etree as ET

from src.base.utils import gen_guid, get_isotime
from src.config import project_config

ORG_GUID = project_config.config.get('guid', 'org')


class ParseXMLMixin:
    tree = None

    def get_namespaces(self):
        """
        Формируем словарь пространств имен xml
        """
        nsmap = dict(ds='http://www.w3.org/2000/09/xmldsig#')
        for ns in self.tree.xpath('//namespace::*'):
            if ns[0]:
                nsmap[ns[0]] = ns[1]
        return nsmap

    def get_elements(self, el_path):
        """
        Поиск всех элементов
        """
        elements = self.tree.xpath(el_path, namespaces=self.get_namespaces())
        return elements

    def get_element(self, el_path):
        """
        Поиск элемента
        """
        if elements := self.get_elements(el_path):
            return elements[0]
        return None

    @staticmethod
    def canonicalizate_tree(element, exc=False):
        """
        Каноникализация
        """
        return ET.tostring(element, method='c14n', exclusive=exc)

    def get_xml(self) -> str:
        return self.canonicalizate_tree(self.tree)


class OperationMixin:
    node = None

    def set_version(self, version):
        """
        Устанавливаем версию запроса
        """
        self.node.set(r'{http://dom.gosuslugi.ru/schema/integration/base/}version', version)


class BaseXML(ParseXMLMixin):
    def __init__(self, template: Path) -> None:
        self.tree = ET.parse(template)
        self._build_header()

    def _build_header(self):
        """
        Заполняем RequestHeader xml-запроса
        """
        header = {
            './/base:Date': get_isotime(),
            './/base:MessageGUID': gen_guid(),
            './/base:orgPPAGUID': ORG_GUID
        }

        for path, value in header.items():
            if (elem := self.get_element(path)) is not None:
                elem.text = value
