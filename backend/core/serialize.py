from datetime import date, datetime
from uuid import UUID


def serialize_row(row: dict) -> dict:
    out = {}
    for key, val in row.items():
        if isinstance(val, UUID):
            out[key] = str(val)
        elif isinstance(val, (datetime, date)):
            out[key] = val.isoformat()
        elif isinstance(val, list):
            out[key] = list(val)
        else:
            out[key] = val
    return out
