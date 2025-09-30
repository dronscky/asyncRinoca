from src.api.gis.file import File, upload_files, GISFileDataFormat


async def upload_debt_files(files: list[File]) -> list[GISFileDataFormat]:
    url = 'http://127.0.0.1:8080/ext-bus-file-store-service/rest/debtreq/'
    return await upload_files(url, files)
