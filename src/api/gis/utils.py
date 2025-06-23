import base64
import random
import string
from binascii import hexlify
from hashlib import md5

from src.base.crypto import calc_hash_by_gost94


def calc_hash_by_md5(obj: bytes):
    """Получение хэша в md5"""
    hash_obj = md5(obj)
    e = base64.b64encode(hash_obj.digest())
    return e.decode('utf-8')


def calc_hash_by_gost(obj: bytes) -> str:
    """Получение хэша по Гост в виде binhex"""
    return hexlify(calc_hash_by_gost94(obj)).decode('utf-8')


def generate_string() -> str:
    """
    Генерируем произвольный набор символов из букв и цифр
    """
    characters = string.ascii_lowercase + string.digits
    return ''.join(random.choice(characters) for _ in range(6))


def get_file_extension(filename: str):
    return filename.split('.')[-1]
