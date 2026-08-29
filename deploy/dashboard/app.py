import json
import os
import re
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI()

LOG_PATH = "/opt/lauren/experiment_log.txt"
STATUS_PATH = "/opt/lauren/status.json"

LINE_RE = re.compile(r"^\[(?P<ts>[^\]]+)\]\s(?P<rest>.*)$")
KIND_RE = re.compile(r"^(Lauren|tool_call|tool_result):\s?(.*)$", re.DOTALL)


def parse_log():
    if not os.path.exists(LOG_PATH):
        return []
    entries = []
    with open(LOG_PATH, "r", encoding="utf-8", errors="replace") as f:
        for raw in f:
            raw = raw.rstrip("\n")
            m = LINE_RE.match(raw)
            if m:
                rest = m.group("rest")
                km = KIND_RE.match(rest)
                if km:
                    kind, text = km.group(1), km.group(2)
                    kind = {"Lauren": "lauren", "tool_call": "tool_call", "tool_result": "tool_result"}[kind]
                else:
                    kind, text = "system", rest
                entries.append({"ts": m.group("ts"), "kind": kind, "text": text})
            elif entries:
                entries[-1]["text"] += "\n" + raw
    return entries


@app.get("/api/log")
def api_log(since: int = 0):
    entries = parse_log()
    return JSONResponse({"entries": entries[since:], "total": len(entries)})


@app.get("/api/status")
def api_status():
    if not os.path.exists(STATUS_PATH):
        return JSONResponse({})
    with open(STATUS_PATH, "r", encoding="utf-8") as f:
        return JSONResponse(json.load(f))


@app.get("/", response_class=HTMLResponse)
def index():
    return HTML_PAGE


HTML_PAGE = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Lauren Nestor</title>
<style>
  :root { color-scheme: dark; }
  body { background:#0b0d10; color:#e6e6e6; font-family:-apple-system,Segoe UI,sans-serif; margin:0; }
  header { position:sticky; top:0; background:#14171c; padding:14px 20px; border-bottom:1px solid #262b33;
           display:flex; justify-content:space-between; align-items:center; }
  header h1 { font-size:16px; margin:0; font-weight:600; }
  header .stat { font-size:13px; color:#9aa4b2; }
  header .stat b { color:#e6e6e6; }
  #feed { max-width:820px; margin:0 auto; padding:20px; }
  .entry { margin-bottom:14px; padding:12px 16px; border-radius:10px; white-space:pre-wrap; word-break:break-word; font-size:14px; line-height:1.45; }
  .lauren { background:#161b22; border-left:3px solid #6ea8fe; }
  .tool_call { background:#141a14; border-left:3px solid #7ee787; font-family:ui-monospace,monospace; font-size:12.5px; color:#a6d9ab; }
  .tool_result { background:#141414; border-left:3px solid #d29922; font-family:ui-monospace,monospace; font-size:12.5px; color:#c9b285; max-height:220px; overflow-y:auto; }
  .system { background:#1c1420; border-left:3px solid #d2a8ff; color:#c9a6e6; font-size:13px; }
  .ts { display:block; font-size:11px; color:#666; margin-bottom:4px; }
  .badge { display:inline-block; font-size:10px; text-transform:uppercase; letter-spacing:.04em; padding:1px 6px;
           border-radius:4px; margin-right:6px; background:#262b33; color:#9aa4b2; }
</style>
</head>
<body>
<header>
  <h1>Lauren Nestor</h1>
  <div class="stat" id="stat">connecting...</div>
</header>
<div id="feed"></div>
<script>
let since = 0;
const feed = document.getElementById('feed');
const stat = document.getElementById('stat');

function render(entry) {
  const div = document.createElement('div');
  div.className = 'entry ' + entry.kind;
  const badge = {lauren:'Lauren', tool_call:'Tool call', tool_result:'Tool result', system:'System'}[entry.kind] || entry.kind;
  div.innerHTML = '<span class="ts"><span class="badge">' + badge + '</span>' + entry.ts + '</span>' +
                  document.createTextNode(entry.text).textContent;
  feed.appendChild(div);
}

async function pollLog() {
  try {
    const res = await fetch('/api/log?since=' + since);
    const data = await res.json();
    for (const e of data.entries) render(e);
    if (data.entries.length) window.scrollTo(0, document.body.scrollHeight);
    since = data.total;
  } catch (e) {}
}

async function pollStatus() {
  try {
    const res = await fetch('/api/status');
    const s = await res.json();
    if (s.spent_eur !== undefined) {
      stat.innerHTML = '<b>&euro;' + s.spent_eur.toFixed(2) + '</b> / &euro;' + s.cap_eur.toFixed(0) +
                        ' &middot; <b>' + s.elapsed_hours.toFixed(1) + 'h</b> runtime';
    }
  } catch (e) {}
}

pollLog(); pollStatus();
setInterval(pollLog, 3000);
setInterval(pollStatus, 10000);
</script>
</body>
</html>"""
