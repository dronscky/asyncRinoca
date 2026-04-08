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
from src.log.log import logger

semaphore = asyncio.Semaphore(5)


async def get_debt_requests() -> Optional[list[SubrequestData]]:
    sql = """
        select subrequestguid, sent_date, response_date, fias, address, apartment, resp_status
        from details_a
        where is_debt = 1 and resp_status is NULL
        group by subrequestguid, sent_date, response_date, fias, address, apartment, resp_status
    """
    if fetch := await select_command(sql):
        return [SubrequestData(*row) for row in fetch]
    return None


async def update_response_status(status: int, ack_guid: str, subrequest_guid: str) -> None:
    q = """
        update details_a
        set resp_status = ?, ack_guid = ?
        where subrequestguid = ?
    """
    await execute_command(q, status, ack_guid, subrequest_guid)


class GISResponseHandler:
    REVOKE_DELAY = 2
    SEND_DELAY = 10

    @staticmethod
    async def _send_import_request(xml: str, delay: int) -> str:
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
            return ack_guid
            # return await check_import_responses_state(ack_guid)

        except Exception as e:
            logger.error(f"Ошибка при обработке импорта {e}")
            # logger.error(xml)
            raise e
        
    async def revoke_response(self, subrequest_guid: str) -> str:
        revoke = RevokeImportDebtResponses([subrequest_guid])
        return await self._send_import_request(revoke.get_xml(), GISResponseHandler.REVOKE_DELAY)
    
    async def send_response(self, response_data: GISResponseDataFormat) -> str:
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
        if subrequestdata.resp_status is None:
            if response_data := await formatting_to_gis_response_data(subrequestdata):
                handler = GISResponseHandler()
                ack_revoke_guid = await handler.revoke_response(subrequestdata.subrequestGUID)
                attempt = 0
                while True:
                    status = await check_import_responses_state(ack_revoke_guid)
                    if status == '3' or '(не имеет статус "Ответ отправлен")' in status:
                        await update_response_status(0, ack_revoke_guid, subrequestdata.subrequestGUID)
                        break
                    else:
                        if attempt != 10:
                            logger.info(f'Ожидаем отзыва запроса {subrequestdata.subrequestGUID}')
                            attempt += 1
                            await asyncio.sleep(360)
                        else:
                            logger.error(f'Количество попыток ожидания отзыва запроса {subrequestdata.subrequestGUID} '
                                         f'превышено'
                                         )
                            raise f'Количество попыток ожидания отзыва запроса {subrequestdata.subrequestGUID} превышено'

                ack_debt_guid = await handler.send_response(response_data)
                status_send_response = await check_import_responses_state(ack_debt_guid)
                await update_response_status(status_send_response, ack_debt_guid, subrequestdata.subrequestGUID)
                await _db_insert_subrequest(subrequestdata.subrequestGUID, subrequestdata.sentDate, 'Имеется')


async def worker():
    """
    Точка входа в модуль отправки проверенных запросов на наличие задолженности
    """

    if debt_subrequests := await get_debt_requests():
        tasks = [resend_subrequest_response(debt_subrequest) for debt_subrequest in debt_subrequests]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for res in results:
            if isinstance(res, Exception):
                logger.error(f'Ошибка отправки ответа о задолженности: {res}')
                continue


if __name__ == "__main__":
    asyncio.run(worker())
