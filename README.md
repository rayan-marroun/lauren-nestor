# Lauren Nestor

An experiment: give a self-hosted open-source AI model its own GCP box, a real
(small) budget, and the goal of building a zero-capital micro-business. Filmed
for YouTube.

"Lauren Nestor" — Lauren is an anagram of NEURAL, Nestor is an anagram of
TENSOR. She is not Claude. She runs entirely on an open-weight model served
locally on the VM (Ollama), so the only real cost in this project is GCP
compute — no API bills.

## Why the architecture looks like this

A 14B-class model running on CPU is not reliable enough to be trusted with
"remember to ask permission before doing X" as a prompt-only rule alone — it
will forget or rationalize past it under pressure, the same way a junior
employee under a deadline cuts a corner they were told not to cut. So the
safety-critical behavior in this project is **enforced in code**, not left to
the model's judgment:

- **Budget**: a GCP Billing Budget alert independently force-stops the VM at
  90% of spend, regardless of anything Lauren decides. `budget_guard.py` is a
  *second*, softer check inside the loop itself so she winds down gracefully
  and logs a summary instead of just getting killed mid-thought.
- **Sensitive actions** (spinning up a second VM, publishing something
  publicly, anything touching payments/accounts) are not "tools she's told to
  ask permission for" — the Python functions implementing those actions
  *are* the permission check. `tools/sensitive.py` emails you and blocks on
  an approve/deny link before the underlying action can even run. There is no
  code path where those actions execute without your click.
- **Payments/accounts specifically**: Lauren can never create an account or
  handle a credential — that's not a guardrail she could talk her way around
  even in principle, because `setup_payment_integration()` doesn't do
  anything except email you what needs setting up. There's no function in
  this codebase that touches money.

## Components

| Piece | Where it runs | What it does |
|---|---|---|
| Ollama + Qwen2.5-14B-Instruct | on the VM | the actual model, local inference |
| `src/agent_loop.py` | on the VM, systemd service | the ReAct loop: research → build → deploy → log |
| `deploy/approval_service/` | Cloud Run | receives approval requests, serves Approve/Deny links, persists state in Firestore |
| `deploy/budget_alert_function/` | Cloud Function | triggered by the GCP Budget alert, force-stops the VM |
| Google Drive folder | your Drive | Lauren's knowledge base — lessons learned, business log, decisions |

## Setup order

1. **You**: create the VM (steps below), generate a Gmail App Password,
   share a Drive folder with the service account (steps below). None of this
   can be done on your behalf — account creation and credentials are things
   only you can do.
2. **Me**: deploy the approval service + budget Cloud Function (needs your
   go-ahead since they touch billing).
3. **You**: SSH into the VM, drop the `.env` file in place (secrets only —
   never committed), run the startup script.
4. **Lauren**: takes it from there, within the guardrails above.

## VM creation (do this yourself in the GCP Console or via `gcloud`)

```bash
gcloud compute instances create lauren-nestor-vm \
  --project=lauren-nestor \
  --zone=us-central1-a \
  --machine-type=c2-standard-8 \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=100GB \
  --boot-disk-type=pd-balanced \
  --provisioning-model=SPOT \
  --instance-termination-action=STOP \
  --scopes=cloud-platform
```

`--provisioning-model=SPOT` is what gets you the ~60% discount over
on-demand. `--instance-termination-action=STOP` means if Google reclaims the
spot capacity, the VM just stops (state preserved) instead of being deleted —
you restart it and Lauren picks up where she left off, since the loop's
scratchpad is persisted to disk.

## What's NOT built yet (next steps once you've picked a Gmail identity)

- `deploy/approval_service/` (FastAPI + Firestore, Cloud Run)
- `deploy/budget_alert_function/` (Cloud Function)
- The actual GCP Budget + alert wiring (needs your confirmation before I
  touch billing config)
