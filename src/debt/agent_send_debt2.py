import asyncio
import sys
import os
from typing import Optional

sys.path.append(os.getcwd())

from src.api.db.db import execute_command, select_command
from src.api.mobill.api import get_court_debt
from src.base.reader import get_ack_message_guid
from src.debt.debt_xml import RevokeImportDebtResponses, SendImportDebtResponses
from src.debt.file import upload_debt_files
from src.debt.mobill import _process_mob_json_response, _db_insert_subrequest, DebtApiResponseData
from src.debt.schema import GISResponseDataFormat, GISDebtorsData, SubrequestData
from src.debt.service import import_debt_responses
from src.debt.state import check_import_responses_state
from src.emails.emails import send_email_to_admins
from src.log.log import logger
from src.utils import counter

semaphore = asyncio.Semaphore(5)


async def get_debt_requests() -> Optional[list[SubrequestData]]:
    sql = """
        select subrequestguid, sent_date, response_date, fias, address, apartment
        from details_a
        where is_debt = 1
        group by subrequestguid, sent_date, response_date, fias, address, apartment
    """
    if fetch := await select_command(sql):
        return [SubrequestData(*row) for row in fetch]
    return None


async def delete_sent_subrequest(subrequest_guid: str) -> None:
    sql = """
        delete from details_a
        where subrequestguid = ?
    """
    await execute_command(sql, subrequest_guid)


class GISResponseHandler:
    REVOKE_DELAY = 2
    SEND_DELAY = 10

    @staticmethod
    async def _send_import_request(xml: str, delay: int):
        """
        Общая логика отправки XML запроса и проверки статуса.
        
        Args:
            xml: XML данные для отправки
            delay: Задержка перед проверкой статуса
            
        Returns:
            Результат проверки статуса
            
        Raises:
            Exception: При ошибках сетевого взаимодействия
        """
        try:
            ack_xml = await import_debt_responses(xml)
            ack_guid = get_ack_message_guid(ack_xml)
             
            await asyncio.sleep(delay)
            return await check_import_responses_state(ack_guid)

        except Exception as e:
            logger.error(f"Ошибка при обработке импорта {e}")
            logger.error(xml)
            raise Exception
        
    async def revoke_response(self, subrequest_guid: str) -> int:
        revoke = RevokeImportDebtResponses([subrequest_guid])
        return await self._send_import_request(revoke.get_xml(), GISResponseHandler.REVOKE_DELAY)
    
    async def send_response(self, response_data: GISResponseDataFormat) -> int:
        debt = SendImportDebtResponses([response_data])
        return await self._send_import_request(debt.get_xml(), GISResponseHandler.SEND_DELAY)


async def get_contracts_api_response_data(subrequestdata: SubrequestData) -> Optional[list[DebtApiResponseData]]:
    """
    Получаем данные ЛС на запрос ГИС ЖКХ
    """
    def _build_request_parameters() -> dict[str, str]:
        """
        Формируем параметры запроса к API Мобилл
        """
        
        if subrequestdata.fiasHouseGUID:
            params = {
                'houseguid': subrequestdata.fiasHouseGUID,
                'apartment': subrequestdata.apartment
            }
        else:
            formatted_address = f'{subrequestdata.address}, кв. {subrequestdata.apartment}' if subrequestdata.apartment else subrequestdata.address
            params = {'address': formatted_address}
        return params

    api_response = await get_court_debt(_build_request_parameters(), getfile=True)

    if api_response.get('ERROR'):
        logger.info(f'На запрос {subrequestdata} ответ Мобилл: {api_response}')
        return None
    return _process_mob_json_response(api_response)
    

async def formatting_to_gis_response_data(subrequestdata: SubrequestData) -> Optional[GISResponseDataFormat]:
    if contracts_data := await get_contracts_api_response_data(subrequestdata):
        contract = contracts_data[0]
        upload_files_attrs = await upload_debt_files(contract.files)
        return GISResponseDataFormat(subrequestGUID=subrequestdata.subrequestGUID, debtorsData=[GISDebtorsData(persons=contract.persons, files=upload_files_attrs)])
    return None


async def resend_subrequest_response(subrequestdata: SubrequestData) -> None:
    async with semaphore:
        if response_data := await formatting_to_gis_response_data(subrequestdata):
            handler = GISResponseHandler()
            if await handler.revoke_response(subrequestdata.subrequestGUID) == 1:
                if await handler.send_response(response_data) == 1:
                    await delete_sent_subrequest(subrequestdata.subrequestGUID)
                    await _db_insert_subrequest(subrequestdata.subrequestGUID, subrequestdata.sentDate, 'Имеется')
                    counter.increment_debtor_subrequest()
        else:
            await delete_sent_subrequest(subrequestdata.subrequestGUID)


async def worker():
    """
    Точка входа в модуль отправки проверенных запросов на наличие задолженности

    """
    if debt_subrequests := await get_debt_requests():
        tasks = [resend_subrequest_response(debt_subrequest) for debt_subrequest in debt_subrequests]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for res in results:
            if isinstance(res, Exception):
                logger.error(f"Ошибка отправки положительного ответа: {res}")
                continue

        send_email_to_admins('Отправлено положительных ответов', f'{counter.get_debtor_subrequests()}')


if __name__ == "__main__":
    asyncio.run(worker())
