import asyncio
from datetime import datetime

from src.api.mobill.api import set_court_status
from src.debt.schema import SubrequestCheckDetails
from src.log.log import logger


async def update_zsp_status(sd: SubrequestCheckDetails, status_name) -> None:

    match status_name:
        case 'Погашена':
            status = 271
        case 'Отмена СП':
            status = 312
        case _:
            raise ValueError(f'Неверный статус: {status_name}')

    data = {
        'identifier': sd.account,
        'exsys': 'OLDBILLING',
        'documenttype' : 41,
        'number': sd.doc_arm_number,
        'datedoc': sd.doc_date,
        'datestart': sd.doc_date,
        'status': status,
        'statusdatetime': datetime.now(),
        'documentidentifier': f'zsp-{sd.doc_arm_number}'
    }
    r = await set_court_status(data)
    if r.get('Status') == 1:
        logger.info(f'Обновлен статус ЗСП №{sd.doc_arm_number} по ЛС {sd.account}')
    else:
        logger.error(f'Ошибка {r}')


async def main():
    print(await update_zsp_status(SubrequestCheckDetails(account='a850343463', doc_arm_number='24199', doc_date='22.12.2022')))


if __name__ == '__main__':
    asyncio.run(main())
