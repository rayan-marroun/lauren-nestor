import subprocess

SCHEMA = {
    "type": "function",
    "function": {
        "name": "shell_exec",
        "description": (
            "Run a bash command in the workspace directory. Use for git, "
            "docker, running tests, installing deps, etc. Runs on the VM "
            "itself -- there is no sandbox beyond the VM boundary, so this "
            "is powerful. Timeout applies."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "timeout_seconds": {"type": "integer", "default": 120},
            },
            "required": ["command"],
        },
    },
}

WORKSPACE = "/opt/lauren/workspace"


def shell_exec(command: str, timeout_seconds: int = 120) -> str:
    try:
        proc = subprocess.run(
            command,
            shell=True,
            cwd=WORKSPACE,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return f"error: command timed out after {timeout_seconds}s"
    # Kept fairly tight -- this goes straight into her conversation history
    # (not just the dashboard display), and things like pip install spam
    # were routinely pushing a single call's input tokens past 7000, eating
    # most of Groq's free-tier per-minute budget in one request.
    out = proc.stdout[-1500:]
    err = proc.stderr[-800:]
    return f"exit={proc.returncode}\nstdout:\n{out}\nstderr:\n{err}"
