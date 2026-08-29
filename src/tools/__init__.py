from . import files, shell, web_search, gcloud_deploy, drive_log, sensitive

TOOL_SCHEMAS = [
    web_search.SCHEMA,
    shell.SCHEMA,
    files.READ_SCHEMA,
    files.WRITE_SCHEMA,
    gcloud_deploy.SCHEMA,
    drive_log.SCHEMA,
    sensitive.SPAWN_WORKER_SCHEMA,
    sensitive.PUBLISH_SCHEMA,
    sensitive.PAYMENT_SCHEMA,
]

TOOL_IMPLS = {
    "web_search": web_search.web_search,
    "shell_exec": shell.shell_exec,
    "read_file": files.read_file,
    "write_file": files.write_file,
    "deploy_cloud_run": gcloud_deploy.deploy_cloud_run,
    "log_lesson": drive_log.log_lesson,
    "spawn_worker_node": sensitive.spawn_worker_node,
    "publish_content": sensitive.publish_content,
    "setup_payment_integration": sensitive.setup_payment_integration,
}


def call_tool(name: str, arguments: dict) -> str:
    impl = TOOL_IMPLS.get(name)
    if impl is None:
        return f"error: unknown tool '{name}'"
    try:
        return impl(**arguments)
    except Exception as exc:  # noqa: BLE001 -- tool errors go back to the model, not up
        return f"error: {exc}"
