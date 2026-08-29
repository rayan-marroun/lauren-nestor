"""Actions that structurally cannot happen without a human clicking Approve.

The gate is not a rule the model follows -- it's in the function body. There
is no argument or phrasing that skips request_approval() below.
"""
from .approval import request_approval, notify_only

SPAWN_WORKER_SCHEMA = {
    "type": "function",
    "function": {
        "name": "spawn_worker_node",
        "description": (
            "Request a second GCP worker VM. ALWAYS requires human approval "
            "-- calling this only sends the request, it does not create "
            "anything by itself."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {"type": "string", "description": "why a second node is justified"},
                "estimated_hourly_cost_eur": {"type": "number"},
            },
            "required": ["reason", "estimated_hourly_cost_eur"],
        },
    },
}

PUBLISH_SCHEMA = {
    "type": "function",
    "function": {
        "name": "publish_content",
        "description": (
            "Publish something publicly -- a directory listing, forum post, "
            "GitHub repo README, social post, etc. ALWAYS requires human "
            "approval first."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "platform": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["platform", "content"],
        },
    },
}

PAYMENT_SCHEMA = {
    "type": "function",
    "function": {
        "name": "setup_payment_integration",
        "description": (
            "You cannot create payment accounts or handle credentials. "
            "Calling this only emails Rayan a description of what needs "
            "setting up (e.g. 'a Stripe account for product X'). It never "
            "executes anything."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "description": {"type": "string", "description": "what needs to be set up and why"},
            },
            "required": ["description"],
        },
    },
}


def spawn_worker_node(reason: str, estimated_hourly_cost_eur: float) -> str:
    decision = request_approval(
        title="Spawn a second worker node",
        body=f"Reason given: {reason}\nEstimated cost: EUR{estimated_hourly_cost_eur}/hr",
    )
    if decision != "approved":
        return f"denied/not approved ({decision}) -- no second node was created"
    return (
        "approved by Rayan, but node creation is not automated in this "
        "harness -- log this in log_lesson and wait for Rayan to spin it up "
        "manually, or ask him directly."
    )


def publish_content(platform: str, content: str) -> str:
    decision = request_approval(
        title=f"Publish to {platform}",
        body=content,
    )
    if decision != "approved":
        return f"denied/not approved ({decision}) -- nothing was published"
    return (
        "approved by Rayan, but posting is not automated in this harness -- "
        "this tool only got you sign-off. Actually posting requires either "
        "a specific integration you don't have, or Rayan doing it by hand."
    )


def setup_payment_integration(description: str) -> str:
    notify_only(
        title="Payment/account setup needed",
        body=description,
    )
    return "emailed Rayan -- this is not something you or this harness can do"
