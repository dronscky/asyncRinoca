from dataclasses import dataclass


@dataclass(frozen=True)
class GReportAttributes:
    form_date: str
    report_id: str
    title: str = 'Report'
    comment: str = ''


@dataclass(frozen=True)
class GData:
    sent_date: str
    response_date: str
    requestguid: str
    persons: str
    sp_no: str
    buh: str
    low: str = ''
    comment: str = ''
