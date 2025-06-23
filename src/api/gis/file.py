import asyncio
from dataclasses import dataclass
from typing import Optional

import aiohttp

from src.config import project_config
from src.api.gis.utils import calc_hash_by_md5, generate_string, get_file_extension
from src.log.log import logger


@dataclass
class File:
    filename: str
    file: bytes


def _split_file(file: bytes, byte_count=5242880) -> list[bytes]:
    """функция разбивки файла на части"""
    return [file[x:x+byte_count] for x in range(0, len(file), byte_count)]


async def _post_request(url: str, headers: dict) -> dict[str, str]:
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url=url, headers=headers) as response:
                await response.text()
                return response.headers
        except aiohttp.ClientResponseError as e:
            logger.error(f'HTTP error occurred {e.status}')
            raise


async def _put_request(url: str, headers: dict, data: bytes) -> dict[str, str]:
    async with aiohttp.ClientSession() as session:
        try:
            async with session.put(url=url, headers=headers, data=data) as response:
                await response.text()
                return response.headers
        except aiohttp.ClientResponseError as e:
            logger.error(f'HTTP error occurred {e.status}')
            raise


async def _head_request(url: str, headers: dict) -> dict[str, str]:
    async with aiohttp.ClientSession() as session:
        try:
            async with session.head(url=url, headers=headers) as response:
                return response.headers
        except aiohttp.ClientResponseError as e:
            logger.error(f'HTTP error occurred {e.status}')
            raise


def _construct_url(base_url: str, upload_id: str = None, completed: bool = False) -> str:
    if upload_id:
        base_url = f"{base_url}/{upload_id}" if base_url[-1] != '/' else f"{base_url}{upload_id}"
    if completed:
        base_url += "?completed"
    elif not upload_id:
        base_url += "/?upload" if base_url[-1] != '/' else "?upload"
    else:
        base_url += "/" if base_url[-1] != '/' else base_url
    return base_url


async def _single_mode_upload(url: str, file_: File) -> Optional[str]:
    """Режим отправки файла размером менее 5Mb"""
    headers = {
    'Content-MD5': calc_hash_by_md5(file_.file),
    'X-Upload-Filename': generate_string() + f'.{get_file_extension(file_.filename)}',
    'X-Upload-Length': str(len(file_.file)),
    'X-Upload-OrgPPAGUID': project_config.config.get('guid', 'org')
    }
    response = await _put_request(_construct_url(url), headers, file_.file)
    if upload_id := response.get('X-Upload-UploadID'):
        return upload_id
    else:
        logger.error(f'Ошибка отправки файла {file_.filename}')
        raise


async def _multi_mode_upload(url: str, file_: File) -> Optional[str]:
    """Режим отправки файла размером более 5Mb"""
    file_chunks = _split_file(file_.file)
    _is_upload_chunks = None

    #  Стадия 1. Инициализация.
    headers = {
        'Content-MD5': calc_hash_by_md5(file_.file),
        'X-Upload-Filename': generate_string() + f'.{get_file_extension(file_.filename)}',
        'X-Upload-Length': str(len(file_.file)),
        'X-Upload-OrgPPAGUID': project_config.config.get('guid', 'org'),
        'X-Upload-Part-count': str(len(file_chunks))
    }

    result = await _post_request(_construct_url(url), headers)
    #  Стадия 2. Отправка.
    if upload_id := result.get('X-Upload-UploadID'):
        for part, chunk in enumerate(file_chunks):
            _is_upload_chunks = False
            headers = {
                'Content-MD5': calc_hash_by_md5(chunk),
                'X-Upload-OrgPPAGUID': project_config.config.get('guid', 'org'),
                'X-Upload-Length': str(len(chunk)),
                'X-Upload-Partnumber': str(part + 1)
            }
            result = await _put_request(_construct_url(url, upload_id), headers, chunk)
            if result:
                _is_upload_chunks = True

        #  Стадия 3. Закрытие сессии.
        if _is_upload_chunks:
            headers = {
                'X-Upload-OrgPPAGUID': project_config.config.get('guid', 'org')
            }
            await _post_request(_construct_url(url, upload_id, completed=True), headers)

            #  Стадия 4. Подтверждение принятия файда
            upload_result = await _head_request(_construct_url(url, upload_id), headers)
            if upload_result.get('X-Upload-Completed'):
                return upload_id

    logger.error(f'Ошибка отправки файла {file_.filename}')
    raise


async def _upload_file(url: str, file_: File) -> str:
    if len(file_.file) > 5242880:
        return await _multi_mode_upload(url, file_)
    return await _single_mode_upload(url, file_)


async def upload_files(url: str, files: list[File]) -> list[str]:
    tasks = [_upload_file(url, file_) for file_ in files]
    results = await asyncio.gather(*tasks)
    #  Проверка на успешность загрузок
    if len(results) == len(files):
        return [*results]

    logger.error('Ошибка загрузки файлов')
    raise
