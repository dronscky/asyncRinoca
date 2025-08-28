import uuid
from typing import Any


def is_valid_uuid(val: Any) -> bool:
    try:
        uuid.UUID(str(val))
        return True
    except ValueError:
        return False
