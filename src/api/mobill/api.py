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


async def _request(session: aiohttp.ClientSession, url: str, data: dict[str, Any]) -> json:
    try:
        async with session.post(url=url, data=data) as response:
            if response.status == 200:
                json_response = json.loads(await response.text(encoding='utf-8'))
                print(json_response)
                return json_response
            else:
                logger.error(response.status)
                return None
    except Exception as e:
        logger.error(e)
        return None


@connect
async def get_court_debt(session: aiohttp.ClientSession, data: dict[str, Any], getfile: bool = False):
    url = f'http://mobill-tko/csp/eco/api.csp?type=balance&action=getcourtdebt&key={KEY}'

    if getfile:
        url += '&getfile=1'
    return await _request(session, url, data)


@connect
async def set_court_status(session: aiohttp.ClientSession, data: dict[str, Any] | aiohttp.FormData, **kwargs) -> dict[str, Any]:
    params = ''
    if kwargs:
        params = '&' + '&'.join([f'{k}={v}' for k, v in kwargs.items()])

    url = f'http://mobill-tko/csp/eco/api.csp?type=document&action=set&key={KEY}' + params
    return await _request(session, url, data)
