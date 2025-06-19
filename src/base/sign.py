import base64
from pathlib import Path

import lxml.etree as ET

from src.base.utils import gen_guid, get_isotime
from src.base.base import ParseXMLMixin
from src.base.crypto import get_issuer, get_serial, load_cert, get_digest, sign
from src.log.log import logger


class SignedXML(ParseXMLMixin):
    def __init__(self, tree, cert, private_key) -> None:
        self.tree = tree
        self.cert = cert
        self.private_key = private_key
        self.sign_data = {
            'signature_id': gen_guid(),
            'signing_time': get_isotime(),
            'key_info_id': gen_guid(),
            'x509_issuer_name': get_issuer(self.cert),
            'x509_sn': get_serial(self.cert),
            'x509_cert': load_cert(self.cert),
        }
        self.sign_data['x509_cert_digest'] = get_digest(base64.b64decode(self.sign_data['x509_cert']))
        self.xades = self._get_xades()
        self._sign()

    def _get_xades(self):
        xades_template = Path(__file__).resolve().parent / 'templates/signature.xml'
        if xades_template.exists():
            with open(xades_template) as f:
                tmpl = f.read()
        else:
            logger.error(f'Не найден необходимый XML для создания XADES подписи')
            raise
        return tmpl.format(**self.sign_data)

    def _sign(self):
        """
        Процесс подписания
        """
        # берем ноду для подписи
        node = self.get_element('//*[@Id="signed-data-container"]')

        signing_request_canonic = self.canonicalizate_tree(node, exc=True)

        # получаем хэш запроса
        request_digest = get_digest(signing_request_canonic)

        # подмешиваем xades в xml
        node.insert(0, ET.fromstring(self.xades))

        # заносим хэш запроса
        digest_value1 = self.get_element('.//ds:DigestValue')
        digest_value1.text = request_digest

        # хэш SignProperties
        sign_prop = self.get_element(f'//*[@Id="xmldsig-{self.sign_data['signature_id']}-signedprops"]')
        sign_prop_canonic = self.canonicalizate_tree(sign_prop, exc=True)
        sign_prop_digest = get_digest(sign_prop_canonic)
        digest_value2 = self.get_element(f'//ds:SignedInfo/ds:Reference[@URI="#xmldsig-{self.sign_data['signature_id']}-signedprops"]/ds:DigestValue')
        digest_value2.text = sign_prop_digest

        # подпись SignedInfo
        signed_info = self.get_element('//ds:SignedInfo')
        signed_info_canonic = self.canonicalizate_tree(signed_info, exc=True)
        signed_info_sign = sign(signed_info_canonic, self.private_key)
        signature_value = self.get_element('//ds:SignatureValue')
        signature_value.text = signed_info_sign
