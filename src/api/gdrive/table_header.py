class TableHeader:
    """                                                             Шапка таблицы
    |sent_date|response_date|requestguid|address|agent_id|persons|dolg_sum|pen_dolg_sum|gp|saldo|paid|sp_no|buh|comment|
        1           2              3        4       5         6        7       8        9   10    11    12  13    14
    """
    _column_names = [
        'Дата запроса',
        'Срок ответа',
        'requestguid',
        'Адрес',
        'ЛС Агента',
        'Должники',
        'СП задолженность',
        'СП пени',
        'Госпошлина',
        'Исходящее сальдо',
        'Текущий платеж',
        '№ Судебного приказа',
        'Бухгалтерия',
        'Примечание'
        ]
    _column_counts = [str(i + 1) for i in range(len(_column_names))]
    header = [_column_names, _column_counts]
    