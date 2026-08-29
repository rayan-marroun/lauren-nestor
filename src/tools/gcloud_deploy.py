import subprocess

from .shell import WORKSPACE

SCHEMA = {
    "type": "function",
    "function": {
        "name": "deploy_cloud_run",
        "description": (
            "Deploy a directory in the workspace (must contain a Dockerfile "
            "or be buildpacks-compatible) to Cloud Run. Cheap/free-tier for "
            "low traffic, but not free -- use for things worth deploying, "
            "not every experiment."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "service_name": {"type": "string"},
                "source_dir": {"type": "string", "description": "relative to workspace"},
                "region": {"type": "string", "default": "us-central1"},
                "allow_unauthenticated": {"type": "boolean", "default": True},
            },
            "required": ["service_name", "source_dir"],
        },
    },
}


def deploy_cloud_run(
    service_name: str,
    source_dir: str,
    region: str = "us-central1",
    allow_unauthenticated: bool = True,
) -> str:
    cmd = [
        "gcloud", "run", "deploy", service_name,
        "--source", source_dir,
        "--region", region,
        "--quiet",
    ]
    if allow_unauthenticated:
        cmd.append("--allow-unauthenticated")
    proc = subprocess.run(cmd, cwd=WORKSPACE, capture_output=True, text=True, timeout=600)
    return f"exit={proc.returncode}\n{proc.stdout[-3000:]}\n{proc.stderr[-2000:]}"
