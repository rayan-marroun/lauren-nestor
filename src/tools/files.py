import os

WORKSPACE = "/opt/lauren/workspace"

READ_SCHEMA = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "Read a file relative to the workspace directory.",
        "parameters": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
}

WRITE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "write_file",
        "description": "Write (overwrite) a file relative to the workspace directory. Creates parent directories as needed.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        },
    },
}


def _resolve(path: str) -> str:
    full = os.path.normpath(os.path.join(WORKSPACE, path))
    if not full.startswith(os.path.normpath(WORKSPACE)):
        raise ValueError("path escapes workspace")
    return full


def read_file(path: str) -> str:
    full = _resolve(path)
    if not os.path.exists(full):
        return f"error: {path} does not exist"
    with open(full, "r", encoding="utf-8", errors="replace") as f:
        return f.read()[:20000]


def write_file(path: str, content: str) -> str:
    full = _resolve(path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(content)
    return f"wrote {len(content)} bytes to {path}"
