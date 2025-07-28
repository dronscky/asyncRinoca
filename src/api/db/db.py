import os
from functools import wraps
from typing import Any

import aioodbc

from src.log.log import logger


def connect_db(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        dsn = (
            "Driver={MariaDB ODBC 3.2 Driver};"
            "Server=localhost;"
            "Database=Rinoca2;"
            f"UID={os.getenv("gis_uid")};"
            f"PWD={os.getenv("gis_pwd")};"
            "TrustServerCertificate=no;"
        )
        async with aioodbc.connect(dsn=dsn) as conn:
            async with conn.cursor() as cursor:
                try:
                    result = await func(*args, cursor=cursor, **kwargs)
                    await conn.commit()
                    return result
                except Exception as e:
                    if 'duplicate' not in str(e).lower():
                        logger.error(f"Error executing {func.__name__}: {e}")
                        raise
                finally:
                    await conn.rollback()
    return wrapper


@connect_db
async def select_command(command: str, *args, cursor=None):
    await cursor.execute(command, args)
    return await cursor.fetchall()


@connect_db
async def execute_command(command: str, *args, cursor=None):
    await cursor.execute(command, args)


@connect_db
async def executemany_command(command: str, params: list[tuple[Any]], cursor=None):
    await cursor.executemany(command, params)
