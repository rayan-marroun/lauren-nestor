import json
import os

STATUS_PATH = "/opt/lauren/status.json"


def read_status() -> dict:
    if not os.path.exists(STATUS_PATH):
        return {}
    try:
        with open(STATUS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def write_status(status: dict) -> None:
    tmp = STATUS_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(status, f)
    os.replace(tmp, STATUS_PATH)
