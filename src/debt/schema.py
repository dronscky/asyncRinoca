from dataclasses import dataclass, field


@dataclass(frozen=True)
class RequestPeriod:
    startDate: str
    endDate: str


@dataclass
class DebtPersons:
    """
    Данные должников, где firstName = Имя
                          lastName = Фамилия
                          middleName = Отчество
    """
    lastName: str
    firstName: str
    middleName: str = ''


@dataclass
class FileData:
    name: str
    attachmentGUID: str
    attachmentHASH: str
    desc: str = ''


@dataclass
class ImportData:
    """Формат выходных данных внешней системы"""
    subrequestGUID: str
    persons: list[DebtPersons] = field(default_factory=list)
    files: list[FileData] = field(default_factory=list)
