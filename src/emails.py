import json
from pathlib import Path
from typing import Literal


def get_email_addresses(emails_type: Literal['gmails', 'sah_mails']) -> set:
    """чтение файла с почтовыми адресами
    """
    path = Path(__file__).resolve().parent / 'emails.json'
    with open(path, 'r') as f:
        data = json.load(f)

        emails = []
        emails.extend(data[emails_type])
        return {*emails}
