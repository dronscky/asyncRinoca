import uuid
from datetime import datetime
from pytz import timezone


def gen_guid() -> uuid:
    return uuid.uuid1()


def get_isotime():
    """
    Получаем время
    """
    return datetime.now(tz=timezone('Asia/Yekaterinburg')).replace(microsecond=0).isoformat()
