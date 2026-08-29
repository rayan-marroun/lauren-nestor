import json
import os
import time
import datetime

from dotenv import load_dotenv

load_dotenv("/opt/lauren/.env")

from llm_client import get_client, get_model
from budget_guard import BudgetGuard, BudgetExceeded
from tools import TOOL_SCHEMAS, call_tool
from tools.drive_log import log_lesson

STATE_PATH = "/opt/lauren/state.json"
LOG_PATH = "/opt/lauren/experiment_log.txt"
SYSTEM_PROMPT_PATH = "/opt/lauren/system_prompt.md"

MAX_TOOL_CALLS_PER_TURN = 6


def log(line: str) -> None:
    stamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"[{stamp}] {line}\n")
    print(f"[{stamp}] {line}", flush=True)


def load_state() -> list:
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    with open(SYSTEM_PROMPT_PATH, "r", encoding="utf-8") as f:
        system_prompt = f.read()
    return [{"role": "system", "content": system_prompt}]


def save_state(messages: list) -> None:
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(messages, f)


def run() -> None:
    os.makedirs("/opt/lauren/workspace", exist_ok=True)
    client = get_client()
    model = get_model()
    budget = BudgetGuard()
    messages = load_state()

    log(f"Lauren starting up. {budget.status_line()}")

    while True:
        try:
            budget.check()
        except BudgetExceeded as exc:
            log(str(exc))
            log_lesson(f"Session ended: {exc}")
            break

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
        )
        choice = response.choices[0]
        msg = choice.message
        messages.append(msg.model_dump(exclude_none=True))

        if msg.content:
            log(f"Lauren: {msg.content[:500]}")

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
            log(f"tool_result: {result[:500]}")
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": result,
            })

        save_state(messages)

        # keep context bounded -- CPU inference on a 14B model is slow, and
        # a runaway context makes every turn slower still
        if len(messages) > 120:
            summary_note = {
                "role": "user",
                "content": "(context trimmed for length -- earlier history summarized via log_lesson entries only)",
            }
            messages = [messages[0], summary_note] + messages[-60:]


if __name__ == "__main__":
    run()
