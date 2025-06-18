import aiohttp

from src.log.log import logger


async def gis_api_fetch(url: str, soap_action: str, xml: str) -> str:
    headers = {
        'SOAPAction': soap_action,
        'Content-Type': 'text/xml'
    }
    async with aiohttp.ClientSession() as s:
        try:
            async with s.post(url=url, headers=headers, data=xml) as response:
                text = await response.text(encoding='utf-8')
                return text
        except aiohttp.ClientResponseError as e:
            logger.error(f'HTTP error occurred {e.status}')
            raise
