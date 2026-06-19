import asyncio

from src.base.delay import get_delay_time
from src.debt.state import check_import_responses_state
from src.emails.emails import send_email_to_admins
from src.base.state import GetStateXML
from src.base.reader import get_ack_message_guid
from src.debt.debt_xml import ExportDebtSubrequests, SendImportDebtResponses
from src.debt.mobill import get_responses_data
from src.debt.reader import get_exportDSRsData
from src.debt.service import export_debt_subrequests, import_debt_responses, state_request
from src.log.log import logger
from src.utils import counter


async def worker():
    sub = None
    is_over = False
    srv_request_count = 0

    while True:
        # 1.  Формируем и отправляем XML на наличие задолженности
        export_subrequests = ExportDebtSubrequests(sub)
        try:
            st1_ack = await export_debt_subrequests(export_subrequests.get_xml())
            await asyncio.sleep(2.0)
        except Exception:
            logger.error('Ошибка отправки запроса о наличии задолженности')
            raise
        # 2. Формируем и отправляем XML на получение ответа на ранее отправленный запрос на шаге 1

        state_exp = GetStateXML()
        state_exp.set_message_guid(get_ack_message_guid(st1_ack))

        while True:
            try:
                st2_ack = await state_request(state_exp.get_xml())
                #
            except Exception:
                logger.error('Ошибка отправки запроса на получение ответа на запрос о наличии задолженности')
                raise

            if data := get_exportDSRsData(st2_ack):
                if data == 'wait':
                    await asyncio.sleep(get_delay_time(srv_request_count))
                    srv_request_count += 1
                else:
                    srv_request_count = 0
                    break
            else:
                break
        del state_exp

        #  Обрабатываем ответ на запрос о наличии задолженности
        # if data:
        #     if data == 'wait':
        #         await asyncio.sleep(get_delay_time(srv_request_count))
        #         srv_request_count += 1
        #     else:
        #         srv_request_count = 0
        if data:
            if data.next == 'last':
                is_over = True
            else:
                sub = data.next

            #  В случае, когда не требуется выгрузка для проверки бухгалтерами, то сразу getfile=True,
            # иначе False
            #   1.
            for i in range(0, len(data.subrequests), 100):
                response_data = await get_responses_data(data.subrequests[i:i+100], getfile=False)
                #  2. Отправка ответов

            # for i in range(0, len(response_data), 100):
                import_responses = SendImportDebtResponses(response_data)
                try:
                    st3_ack = await import_debt_responses(import_responses.get_xml())
                    # Проверка на состояние отправки занимает время. Данный процесс лучше в отдельный поток
                    # или запускать отдельно
                    # res = await check_import_responses_state(get_ack_message_guid(st3_ack))
                except Exception:
                    logger.error('Ошибка отправки ответа на запрос о наличии задолженности')
                    raise
        else:
            #  Отсутствуют запросы о наличии задолженности
            is_over = True

        if is_over:
            message = f'Отвечено на {counter.get_total_subrequests()} запросов - на проверку {counter.get_check_subrequests()}'
            send_email_to_admins('Количество отправленных запросов', message)
            logger.info(message)
            break


# async def main():
#     export_subrequests = ExportDebtSubrequests(sub=None)
#     st1_ack = await export_debt_subrequests(export_subrequests.get_xml())
#     print(st1_ack)
#     await asyncio.sleep(2.0)
#     state_exp = GetStateXML()
#     state_exp.set_message_guid(get_ack_message_guid(st1_ack))
#     st2_ack = await state_request(state_exp.get_xml())
#     print(get_exportDSRsData(st2_ack))


if __name__ == '__main__':
    asyncio.run(worker())
    # asyncio.run(main())
