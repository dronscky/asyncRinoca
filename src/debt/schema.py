from dataclasses import dataclass, field

from src.debt.file import GISFileDataFormat


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
    persons: list[PersonName] = field(default_factory=list)
    files: list[GISFileDataFormat] = field(default_factory=list)


@dataclass(frozen=True)
class GISResponseDataFormat:
    """Формат выходных данных внешней системы"""
    subrequestGUID: str
    debtorsData: list[GISDebtorsData] = field(default_factory=list)
