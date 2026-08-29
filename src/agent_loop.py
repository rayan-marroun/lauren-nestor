import json
import os
import time
import datetime

from dotenv import load_dotenv

load_dotenv("/opt/lauren/.env")

from llm_client import LLMRouter
from budget_guard import BudgetGuard, BudgetExceeded
from tools import TOOL_SCHEMAS, call_tool
from tools.drive_log import log_lesson
from status_store import read_status, write_status

STATE_PATH = "/opt/lauren/state.json"
LOG_PATH = "/opt/lauren/experiment_log.txt"
SYSTEM_PROMPT_PATH = "/opt/lauren/system_prompt.md"

MAX_TOOL_CALLS_PER_TURN = 6


def log(line: str) -> None:
    stamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"[{stamp}] {line}\n")
    print(f"[{stamp}] {line}", flush=True)


def write_budget_status(budget: BudgetGuard) -> None:
    # Merge rather than overwrite -- update_status() (see tools/status.py)
    # writes headline/detail into this same file, and a blind overwrite here
    # would silently wipe that out every iteration.
    status = read_status()
    status.update({
        "spent_eur": budget.estimated_spend_eur(),
        "cap_eur": budget.cap_eur,
        "elapsed_hours": budget.elapsed_hours(),
        "updated_at": datetime.datetime.utcnow().isoformat(),
    })
    write_status(status)


def load_state() -> list:
    with open(SYSTEM_PROMPT_PATH, "r", encoding="utf-8") as f:
        system_prompt = f.read()

    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            messages = json.load(f)
        # Always refresh the system prompt from disk so edits take effect on
        # restart without losing her accumulated conversation/progress.
        messages[0] = {"role": "system", "content": system_prompt}
        return messages

    return [{"role": "system", "content": system_prompt}]


def save_state(messages: list) -> None:
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(messages, f)


def run() -> None:
    os.makedirs("/opt/lauren/workspace", exist_ok=True)
    router = LLMRouter()
    budget = BudgetGuard()
    messages = load_state()
    last_model_used = None

    log(f"Lauren starting up. {budget.status_line()}")

    while True:
        write_budget_status(budget)
        try:
            budget.check()
        except BudgetExceeded as exc:
            log(str(exc))
            log_lesson(f"Session ended: {exc}")
            break

        response, model_used, provider_errors = router.create(
            messages=messages,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
        )
        if provider_errors:
            log("Provider(s) failed before falling through: " + " | ".join(provider_errors))
        if model_used != last_model_used:
            if last_model_used is None:
                log(f"Using {model_used}")
            else:
                log(f"Switched provider: {last_model_used} -> {model_used}")
            last_model_used = model_used

        choice = response.choices[0]
        msg = choice.message
        messages.append(msg.model_dump(exclude_none=True))

        if msg.content:
            log(f"Lauren: {msg.content}")

        tool_calls = msg.tool_calls or []
        if not tool_calls:
            # No tool call this turn -- nudge her to keep working rather
            # than idling silently.
            messages.append({
                "role": "user",
                "content": (
                    f"({budget.status_line()}) Continue working toward the "
                    f"goal. Use a tool, or call log_lesson if you're between "
                    f"steps and want to record where you are."
                ),
            })
            save_state(messages)
            time.sleep(5)
            continue

        for call in tool_calls[:MAX_TOOL_CALLS_PER_TURN]:
            args = json.loads(call.function.arguments or "{}")
            log(f"tool_call: {call.function.name}({args})")
            result = call_tool(call.function.name, args)
            log(f"tool_result: {result[:2000]}")
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": result,
            })

        save_state(messages)

        # Keep context bounded -- CPU inference on a 14B model is slow, and
        # a large context also burns through Groq's free-tier per-minute
        # token budget in a single call. 120 messages was much too generous
        # given how token-heavy tool results can be.
        if len(messages) > 40:
            summary_note = {
                "role": "user",
                "content": "(context trimmed for length -- earlier history summarized via log_lesson entries only)",
            }
            messages = [messages[0], summary_note] + messages[-20:]


if __name__ == "__main__":
    run()
