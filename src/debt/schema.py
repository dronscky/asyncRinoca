from dataclasses import dataclass, field


@dataclass(frozen=True)
class RequestPeriod:
    startDate: str
    endDate: str


@dataclass(frozen=True)
class SubrequestData:
    """
    Данные подзапроса
    """
    subrequestGUID: str
    sentDate: str
    responseDate: str
    fiasHouseGUID: str
    address: str
    apartment: str


@dataclass(frozen=True)
class DebtPersons:
    """
    Данные должников, где firstName = Имя
                          lastName = Фамилия
                          middleName = Отчество
    """
    lastName: str
    firstName: str
    middleName: str = ''


@dataclass(frozen=True)
class FileData:
    name: str
    attachmentGUID: str
    attachmentHASH: str
    desc: str = ' '


@dataclass(frozen=True)
class DebtDocAttrs:
    case_number: str
    sum_debt: float
    penalty: float
    stamp_duty: float
    total: float


@dataclass(frozen=True)
class DebtData:
    persons: list[DebtPersons] = field(default_factory=list)
    files: list[FileData] = field(default_factory=list)
    debt_doc_attrs: DebtDocAttrs = None


@dataclass(frozen=True)
class ImportData:
    """Формат выходных данных внешней системы"""
    subrequestGUID: str
    debtData: list[DebtData] = field(default_factory=list)
