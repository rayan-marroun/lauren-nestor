import datetime

from status_store import read_status, write_status as _write_status_file

SCHEMA = {
    "type": "function",
    "function": {
        "name": "update_status",
        "description": (
            "Set a short, current status shown on Rayan's dashboard sidebar "
            "-- what you're focused on right now and what you're doing next. "
            "Call this whenever your focus or step changes (finishing "
            "research, starting a build, debugging, etc). Keep both fields "
            "short -- a headline and a next-step, not a restatement of your "
            "full reasoning."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "headline": {"type": "string", "description": "e.g. 'Building sentiment-analysis API'"},
                "detail": {"type": "string", "description": "e.g. 'Debugging local FastAPI run'"},
            },
            "required": ["headline", "detail"],
        },
    },
}


def update_status(headline: str, detail: str) -> str:
    status = read_status()
    status.update({
        "headline": headline,
        "detail": detail,
        "status_updated_at": datetime.datetime.utcnow().isoformat(),
    })
    _write_status_file(status)
    return "status updated"
