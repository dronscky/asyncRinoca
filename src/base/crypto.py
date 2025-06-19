import base64
import subprocess
from pathlib import Path

from src.config import project_config
from src.log.log import logger

OPENSSL = project_config.config.get('crypto', 'openssl')


def _run(cmd, input=None):
    """
    Запуск процесса
    """
    procs = subprocess.Popen(cmd,
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             creationflags=subprocess.CREATE_NO_WINDOW)
    return procs.communicate(input=input)


def get_issuer(cert: Path):
    """
    Информация об издателе сертификата
    """
    cmd = [OPENSSL, 'x509', '-in', cert, '-noout', '-issuer', '-nameopt', 'sep_multiline,utf8']
    out, err = _run(cmd)
    if err:
        logger.error(f'Openssl error: {err}')
        raise
    issuer = out.decode('utf-8')[9:]
    props = list(reversed(issuer.split('\r\n')))
    res = []
    for prop in props:
        props_ar = prop.split('=')
        if len(props_ar) > 1:
            prop_name = props_ar[0].lower().strip()
            prop_value = props_ar[1].replace('"', '\\"').replace(',', '\\,')
            res.append(f'{prop_name}={prop_value}')
    return ','.join(res).replace('emailaddress', '1.2.840.113549.1.9.1').replace('ogrn', '1.2.643.100.1')


def get_serial(cert: Path):
    """
    Серийный номер сертификата
    """
    cmd = [OPENSSL, 'x509', '-in', cert, '-noout', '-serial']
    out, err = _run(cmd)
    if err:
        logger.error(f'Openssl error: {err}')
        raise
    serial = out.decode('utf-8').split('=')[1]
    return str(int(serial, 16))


def load_cert(cert: Path):
    """
    Загрузка сертификата
    """
    head = '-----BEGIN CERTIFICATE-----'
    tail = '-----END CERTIFICATE-----'
    with open(cert) as f:
        data = f.read()

    data = data.replace('\r', '').replace('\n', '')
    cert_start = data.find(head)
    cert_end = data.find(tail)
    return data[cert_start + len(head):cert_end]


def get_base64(val):
    """
    Преобразуем в BASE64 и возвращаем в utf-8
    """
    e = base64.b64encode(val)
    return e.decode('utf-8')


def get_digest(text):
    """
    Хэшируем. Вывод в BASE64
    """
    cmd = [OPENSSL, 'dgst', '-engine', 'gost', '-md_gost12_256', '-binary']
    out, err = _run(cmd, input=text)
    if err:
        logger.error(f'Openssl error: {err}')
        raise
    return get_base64(out)


def calculate_upload_file_hash(text):
    """
    Хэшируем
    """
    cmd = [OPENSSL, 'dgst', '-engine', 'gost', '-md_gost94', '-binary']
    out, err = _run(cmd, input=text)
    if err:
        logger.error(f'Openssl error: {err}')
        raise
    return out


def sign(text, private_key):
    """
    Подписываем. Вывод в BASE64
    """
    cmd = [OPENSSL, 'dgst', '-engine', 'gost', '-md_gost12_256', '-binary', '-sign', private_key]
    out, err = _run(cmd, input=text)
    if err:
        logger.error(f'Openssl error: {err}')
        raise
    return get_base64(out)
