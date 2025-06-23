import base64
from dataclasses import dataclass
from datetime import datetime
import json
import re
from typing import Optional

from src.debt.schema import DebtPersons
from src.log.log import logger


@dataclass
class File:
    filename: str
    file: bytes


@dataclass
class DebtDocs:
    debtors: list[DebtPersons]
    files: list[File]


def split_debtors_names(persons: list[str] | str) -> list[DebtPersons]:
    if isinstance(persons, str):
        return [DebtPersons(*persons.split())]
    return [DebtPersons(*person.split()) for person in persons]


def find_sp_filename(filename: str) -> str:
    patterns = [
        r'^СП-.+\..{2,}',
    ]
    for pattern in patterns:
        if re.findall(pattern, filename):
            return filename
    return ''


def get_debtors_data(mobill_json_response: json) -> Optional[list[DebtDocs]]:
    debt_docs = []
    # Получаем данные лс на адресе
    if accounts := mobill_json_response.get('Data'):
        # Перебираем все лс найденные по адресу на наличие неоплаченных ЗСП ПИР и если на одном лс их несколько,
        # то выбираем самое позднее ЗСП, данные которого будут отправлены в ГИС ЖКХ
        for account in accounts:
            if court_debt := account['CourtDebt']:
                if court_debt['SumDebt'] > 0:
                    if documents := court_debt['Documents']:
                        document_date = last_document = None
                        result: bool = False
                        if len(documents) > 1:
                            for document in documents:
                                case_number = document['DocumentEntry']['CaseNumber']
                                if isinstance(case_number, str) and case_number != '':
                                    if not document_date:
                                        document_date = datetime.strptime(document['DateDoc'], '%d.%m.%Y')
                                        last_document = document
                                    else:
                                        if datetime.strptime(document['DateDoc'], '%d.%m.%Y') > document_date:
                                            document_date = datetime.strptime(document['DateDoc'], '%d.%m.%Y')
                                            last_document = document
                                    result = True
                        else:
                            case_number = documents[0]['DocumentEntry']['CaseNumber']
                            if isinstance(case_number, str) and case_number != '':
                                last_document = documents[0]
                                result = True

                        if result:
                            files = []
                            for file in last_document['File']:
                                if (file_name := find_sp_filename(file['FileName'])) != '':
                                    file_content = ''
                                    for file_chunk in file['FileContent']:
                                        file_content += file_chunk.replace('\n', '')
                                    f = File(
                                        filename=file_name,
                                        file=base64.b64decode(file_content)
                                    )
                                    files.append(f)

                            debt_doc = DebtDocs(
                                debtors=split_debtors_names(
                                    last_document['DocumentEntry']['ContractorAdditionalOwner']),
                                files=files
                            )
                            debt_docs.append(debt_doc)
            else:
                continue
    return debt_docs


# async def main():
#     attrs = {
#         'houseguid': '772A74BC-8D12-49FD-A18D-56DE7E3B9418',
#         'apartment': '39'
#     }
#     response = await get_court_debt(attrs)
#     debt_data = get_debtors_data(response)
#     print(debt_data)
#
#
# if __name__ == '__main__':
#     asyncio.run(main())
