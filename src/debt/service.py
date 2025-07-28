from src.api.gis.api import gis_api_fetch
from src.config import project_config

HOST = project_config.config.get('connect', 'host')
PORT = project_config.config.get('connect', 'port')


async def export_debt_subrequests(xml: str):
    url = f'http://{HOST}:{PORT}/ext-bus-debtreq-service/services/DebtRequestsAsync'
    return await gis_api_fetch(url, 'urn:exportDebtSubrequests', xml)


async def state_request(xml: str):
    url = f'http://{HOST}:{PORT}/ext-bus-debtreq-service/services/DebtRequestsAsync'
    return await gis_api_fetch(url, 'urn:getState', xml)


async def import_debt_responses(xml: str):
    url = f'http://{HOST}:{PORT}/ext-bus-debtreq-service/services/DebtRequestsAsync'
    return await gis_api_fetch(url, 'urn:importResponses', xml)
