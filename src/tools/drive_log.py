import datetime
import os

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload

SCHEMA = {
    "type": "function",
    "function": {
        "name": "log_lesson",
        "description": (
            "Append a lesson, decision, or dead-end to the persistent "
            "knowledge base on Google Drive. This is your memory across "
            "restarts -- use it whenever you learn something worth not "
            "re-learning."
        ),
        "parameters": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    },
}

LOCAL_LOG = "/opt/lauren/lessons.md"


def _drive_service():
    key_path = os.environ["GDRIVE_SERVICE_ACCOUNT_JSON"]
    creds = service_account.Credentials.from_service_account_file(
        key_path, scopes=["https://www.googleapis.com/auth/drive.file"]
    )
    return build("drive", "v3", credentials=creds)


def _append_local(entry: str) -> None:
    with open(LOCAL_LOG, "a", encoding="utf-8") as f:
        f.write(entry)


def log_lesson(text: str) -> str:
    stamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    entry = f"\n## {stamp}\n{text}\n"
    _append_local(entry)

    folder_id = os.environ.get("GDRIVE_FOLDER_ID")
    if not folder_id:
        return "logged locally only (GDRIVE_FOLDER_ID not set)"

    try:
        service = _drive_service()
        query = f"name='lessons.md' and '{folder_id}' in parents and trashed=false"
        existing = service.files().list(q=query, fields="files(id)").execute().get("files", [])
        with open(LOCAL_LOG, "r", encoding="utf-8") as f:
            full_content = f.read()
        media = MediaInMemoryUpload(full_content.encode("utf-8"), mimetype="text/markdown")
        if existing:
            service.files().update(fileId=existing[0]["id"], media_body=media).execute()
        else:
            metadata = {"name": "lessons.md", "parents": [folder_id]}
            service.files().create(body=metadata, media_body=media).execute()
        return "logged locally and synced to Drive"
    except Exception as exc:  # noqa: BLE001
        return f"logged locally, Drive sync failed: {exc}"
