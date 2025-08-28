from src.api.db.db import execute_command
from src.api.gdrive.schema import GReportAttributes


async def create_db_record_about_report(g_rep_attrs: GReportAttributes) -> None:
    sql = """
        insert into ext_reports (form_date, report_id, title, comment)
        values (?, ?, ?, ?)
    """
    await execute_command(sql, g_rep_attrs.form_date, g_rep_attrs.report_id, g_rep_attrs.title, g_rep_attrs.comment)


async def delete_db_record_about_report(g_report_id: str) -> None:
    sql = """
        delete from ext_reports
        where report_id = ?
    """
    await execute_command(sql, g_report_id)
