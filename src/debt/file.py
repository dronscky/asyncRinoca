from dataclasses import dataclass

from src.api.gis.file import File, upload_files
from src.api.gis.utils import calc_hash_by_gost


@dataclass(frozen=True)
class GISFileDataFormat:
    name: str
    attachmentGUID: str
    attachmentHASH: str
    desc: str = ' '


async def _upload_debt_files(files: list[File]) -> list[str]:
    url = 'http://127.0.0.1:8080/ext-bus-file-store-service/rest/debtreq/'
    return await upload_files(url, files)


async def get_upload_files_data(files: list[File]) -> list[GISFileDataFormat]:
    files_data = []
    upload_ids = await _upload_debt_files([file for file in files])
    for i, file in enumerate(files):
        files_data.append(GISFileDataFormat(name=file.filename,
                                            attachmentGUID=upload_ids[i],
                                            attachmentHASH=calc_hash_by_gost(file.file)
                                            ))
    return files_data
