from dataclasses import dataclass, field

from src.debt.file import GISFileDataFormat


@dataclass
class SubrequestCheckDetails:
    sent_date: str
    response_date: str
    subrequestguid: str
    fias: str
    address: str
    apartment: str
    persons: str
    account: str
    doc_arm_number: str
    doc_date: str
    case_number: str
    sum_debt: float
    penalty: float
    duty: float
    total: float
    buh: str = None

    def __post_init__(self):
        self.sum_debt = float(self.sum_debt)
        self.penalty = float(self.penalty)
        self.duty = float(self.duty)
        self.total = float(self.total)


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
class PersonName:
    """
    Данные должников, где firstName = Имя
                          lastName = Фамилия
                          middleName = Отчество
    """
    lastName: str
    firstName: str
    middleName: str = ''

    def __repr__(self):
        return f'{self.lastName} {self.firstName} {self.middleName}'.strip()


@dataclass(frozen=True)
class GISDebtorsData:
    persons: set[PersonName] = field(default_factory=list)
    files: list[GISFileDataFormat] = field(default_factory=list)


@dataclass(frozen=True)
class GISResponseDataFormat:
    """Формат выходных данных внешней системы"""
    subrequestGUID: str
    debtorsData: list[GISDebtorsData] = field(default_factory=list)
