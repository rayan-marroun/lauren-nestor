"""Cloud Function triggered by the GCP Budget alert's Pub/Sub topic.

This is the real hard stop -- independent of anything Lauren's loop decides.
Deployed with the trigger topic set to the one the Budget alert publishes
to; see the setup command in deploy/README-budget-alert.txt.
"""
import base64
import json
import os

from google.cloud import compute_v1

PROJECT_ID = os.environ["GCP_PROJECT_ID"]
ZONE = os.environ["GCP_ZONE"]
INSTANCE_NAME = os.environ["GCP_INSTANCE_NAME"]
STOP_THRESHOLD_FRACTION = 0.9


def stop_vm_on_budget_alert(event, context):
    data = json.loads(base64.b64decode(event["data"]).decode("utf-8"))
    cost_amount = data.get("costAmount", 0)
    budget_amount = data.get("budgetAmount", 1)

    if budget_amount <= 0:
        return

    fraction = cost_amount / budget_amount
    if fraction < STOP_THRESHOLD_FRACTION:
        print(f"spend at {fraction:.0%} of budget, below stop threshold, no action")
        return

    print(f"spend at {fraction:.0%} of budget -- stopping {INSTANCE_NAME}")
    client = compute_v1.InstancesClient()
    client.stop(project=PROJECT_ID, zone=ZONE, instance=INSTANCE_NAME)
