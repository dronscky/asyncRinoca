from src.api.gis.file import File, upload_files


async def upload_debt_file(files: list[File]) -> list[str]:
    url = 'http://127.0.0.1:8080/ext-bus-file-store-service/rest/debtreq/'
    return await upload_files(url, files)
