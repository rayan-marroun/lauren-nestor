import datetime

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from google.cloud import firestore

app = FastAPI()
db = firestore.Client()
COLLECTION = "approvals"


def _page(message: str) -> HTMLResponse:
    return HTMLResponse(f"<html><body style='font-family:sans-serif;padding:2rem'>"
                         f"<h2>{message}</h2><p>You can close this tab.</p></body></html>")


@app.post("/request")
def create_request(payload: dict):
    doc = {
        "title": payload["title"],
        "body": payload["body"],
        "status": "pending",
        "created_at": datetime.datetime.utcnow().isoformat(),
    }
    db.collection(COLLECTION).document(payload["id"]).set(doc)
    return {"ok": True}


@app.get("/approve/{action_id}")
def approve(action_id: str):
    ref = db.collection(COLLECTION).document(action_id)
    if not ref.get().exists:
        return _page("Unknown or expired request.")
    ref.update({"status": "approved", "decided_at": datetime.datetime.utcnow().isoformat()})
    return _page("Approved.")


@app.get("/deny/{action_id}")
def deny(action_id: str):
    ref = db.collection(COLLECTION).document(action_id)
    if not ref.get().exists:
        return _page("Unknown or expired request.")
    ref.update({"status": "denied", "decided_at": datetime.datetime.utcnow().isoformat()})
    return _page("Denied.")


@app.get("/status/{action_id}")
def status(action_id: str):
    snap = db.collection(COLLECTION).document(action_id).get()
    if not snap.exists:
        return {"status": "unknown"}
    return {"status": snap.to_dict().get("status", "unknown")}
