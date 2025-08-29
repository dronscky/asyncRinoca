import asyncio
import base64
from dataclasses import dataclass, astuple
from datetime import datetime
import json
import re
from typing import Optional

from src.api.db.db import execute_command
from src.log.log import logger
from src.api.gis.file import File
from src.api.mobill.api import get_court_debt_mob_api_response
from src.debt.file import get_upload_files_data
from src.debt.schema import GISDebtorsData, PersonName, GISResponseDataFormat, SubrequestData, SubrequestCheckDetails


class DebtApiResponseFile(File):...


@dataclass(frozen=True)
class DebtApiResponseExtendedParams:
    account: str
    case_number: str
    sum_debt: float
    penalty: float
    duty: float
    total: float


@dataclass(frozen=True)
class DebtApiResponseData:
    persons: list[PersonName]
    files: list[DebtApiResponseFile]
    ext_params: DebtApiResponseExtendedParams = None


def split_debtors_names(persons: list[str] | str) -> list[PersonName]:
    if isinstance(persons, str):
        return [PersonName(*persons.split())]
    return [PersonName(*person.split()) for person in persons]


def find_sp_filename(filename: str) -> str:
    patterns = [
        r'^СП-.+\..{2,}',
    ]
    for pattern in patterns:
        if re.findall(pattern, filename):
            return filename
    return ''


async def get_responses_data(subrequests_data: list[SubrequestData], getfile: bool = False) -> list[GISResponseDataFormat]:
    tasks = [_get_response_format_data(subrequest_data, getfile) for subrequest_data in subrequests_data]
    result = await asyncio.gather(*tasks)
    return [*result]


async def _get_response_format_data(subrequest_data: SubrequestData, getfile: bool) -> GISResponseDataFormat:
    """
        Формируем данные для отправки ответа в ГИС ЖКХ (importRequest).
         - получаем данные по API Mobill о наличии действующей задолженности с файлом судебного приказа
         или без согласно ключу getfile. При getfile=True происходит выгрузка судебного приказа на портал и получение
         необходимых атрибутов для формирования XML importRequest

    """
    debtors_data = []
    if api_response := await _get_court_debt_api_response(subrequest_data.fiasHouseGUID, subrequest_data.apartment, getfile):
        for debt_account in api_response:
            if getfile:
                debtors_data.append(GISDebtorsData(persons=debt_account.persons,
                                                   files=await get_upload_files_data(debt_account.files)))
                await _db_insert_subrequest(subrequest_data.subrequestGUID, subrequest_data.sentDate, 'Имеется')
            else:
                persons = ', '.join([repr(p) for p in debt_account.persons])
                await _db_insert_check_subrequest(SubrequestCheckDetails(sent_date=subrequest_data.sentDate,
                                                                         response_date=subrequest_data.responseDate,
                                                                         subrequestguid=subrequest_data.subrequestGUID,
                                                                         fias=subrequest_data.fiasHouseGUID,
                                                                         address=subrequest_data.address,
                                                                         apartment=subrequest_data.apartment,
                                                                         persons=persons,
                                                                         account=debt_account.ext_params.account,
                                                                         case_number=debt_account.ext_params.case_number,
                                                                         sum_debt=debt_account.ext_params.sum_debt,
                                                                         penalty=debt_account.ext_params.penalty,
                                                                         duty=debt_account.ext_params.duty,
                                                                         total=debt_account.ext_params.total
                                                                         ))
                await _db_insert_subrequest(subrequest_data.subrequestGUID, subrequest_data.sentDate)
    return GISResponseDataFormat(subrequestGUID=subrequest_data.subrequestGUID, debtorsData=debtors_data)


async def _get_court_debt_api_response(house_fias: str, apartment: str, getfile: bool) -> Optional[list[DebtApiResponseData]]:
    params = {
        # перечень ключей словаря параметров для поиска согласно API Mobill для поиска задолженности
        'houseguid': house_fias,
        'apartment': apartment
    }
    json_response = await get_court_debt_mob_api_response(params, getfile)
    return _process_mob_json_response(json_response)


async def _db_insert_check_subrequest(subrequest_details: SubrequestCheckDetails):
    sql = """
        insert into details_a (sent_date, response_date, subrequestguid, fias, address, apartment, 
                               persons, account, case_number, sum_debt, penalty, duty, total)
        values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    try:
        await execute_command(sql, *astuple(subrequest_details)[:-1])
    except Exception as e:
        logger.error(f'Ошибка записи в БД: {subrequest_details}. {e=}')


async def _db_insert_subrequest(subrequestguid: str, sent_date: str, answer: str='Нет задолженности'):
    sql = """
        insert into requests (requestguid, answer, sent_date, answer_time)
        values (?, ?, ?, ?)
    """
    try:
        await execute_command(sql,
                              subrequestguid,
                              answer,
                              sent_date,
                              datetime.now())
    except Exception as e:
        logger.error(f'Ошибка записи в БД: {e=}')


def _process_mob_json_response(mobill_json_response: json) -> Optional[list[DebtApiResponseData]]:
    resp_data = []
    # Получаем данные лс на адресе
    if accounts := mobill_json_response.get('Data'):
        # Перебираем все лс найденные по адресу на наличие неоплаченных ЗСП ПИР и если на одном лс их несколько,
        # то выбираем самое позднее ЗСП, данные которого будут отправлены в ГИС ЖКХ
        for account in accounts:
            court_debt = account.get('CourtDebt', {})
            if court_debt and court_debt['SumDebt'] > 0 and (documents := court_debt.get('Documents')):
                last_document = None

                for document in documents:
                    case_number = document['DocumentEntry'].get('CaseNumber', '')
                    if isinstance(case_number, str) and case_number:
                        document_date = datetime.strptime(document['DateDoc'], '%d.%m.%Y')
                        if last_document is None or document_date > datetime.strptime(last_document['DateDoc'], '%d.%m.%Y'):
                            last_document = document

                if last_document:
                    ext_params = DebtApiResponseExtendedParams(account=account['Identifier'],
                                                               case_number=last_document['DocumentEntry']['CaseNumber'],
                                                               sum_debt=last_document['SumDebt'],
                                                               penalty=last_document['SumDebtPenalty'],
                                                               duty=last_document['SumDebtDuty'],
                                                               total=last_document['SumDebtTotal'])

                    files = []
                    if last_document.get('File'):
                        for file in last_document['File']:
                            if file_name := find_sp_filename(file['FileName']):
                                file_content = ''.join(file_chunk.replace('\n', '') for file_chunk in file['FileContent'])
                                f = DebtApiResponseFile(
                                    filename=file_name,
                                    file=base64.b64decode(file_content)
                                )
                                files.append(f)

                    data = DebtApiResponseData(
                        persons=split_debtors_names(last_document['DocumentEntry']['ContractorAdditionalOwner']),
                        files=files,
                        ext_params=ext_params
                    )
                    resp_data.append(data)
    else:
        logger.info(mobill_json_response)
    return resp_data


async def main():
    # SubrequestData(subrequestGUID='10eef6e0-744f-11f0-ac99-1b3e4c2a9278', sentDate='2025-08-08', responseDate='2025-08-15', fiasHouseGUID='4d866468-6a1a-4d50-b1b4-127d0a429837', address='450049, Респ Башкортостан, г Уфа, ул Баязита Бикбая, д. 29', apartment='10')
    print(await _get_court_debt_api_response('66c35881-1591-49b2-b268-8b2c09e1652f', '35', False))

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
