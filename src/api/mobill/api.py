import json
from functools import wraps
from typing import Any

import aiohttp

from src.log.log import logger
from src.config import project_config

KEY = project_config.config.get('mobill', 'key')


def connect(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        async with aiohttp.ClientSession() as session:
            return await func(session, *args, **kwargs)
    return wrapper


@connect
async def get_court_debt(session: aiohttp.ClientSession, data: dict[str, Any], getfile: bool = False):
    url = f'http://mobill-tko/csp/eco/api.csp?type=balance&action=getcourtdebt&key={KEY}'

    if getfile:
        url += '&getfile=1'

    try:
        async with session.post(url=url, data=data) as response:
            if response.status == 200:
                json_response = json.loads(await response.text(encoding='utf-8'))
                return json_response
            else:
                logger.error(response.status)
                return None
    except Exception as e:
        logger.error(e)
        return None
