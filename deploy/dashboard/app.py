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
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Lauren Nestor</title>
<style>
  :root {
    color-scheme: dark;
    --bg: #0a0b0d;
    --surface: #111318;
    --surface-2: #16191f;
    --border: #22262e;
    --text: #e8e9ec;
    --text-dim: #8b909b;
    --text-faint: #5a5f6a;
    --accent: #5fa8ff;
    --accent-dim: #5fa8ff33;
    --mono: ui-monospace, "SF Mono", "Cascadia Code", Consolas, monospace;
    --sans: -apple-system, "Segoe UI", system-ui, sans-serif;
  }
  * { box-sizing: border-box; }
  body { background: var(--bg); color: var(--text); font-family: var(--sans); margin: 0; }

  header {
    position: sticky; top: 0; z-index: 10;
    background: color-mix(in srgb, var(--surface) 92%, transparent);
    backdrop-filter: blur(10px);
    border-bottom: 1px solid var(--border);
    padding: 14px 24px;
    display: flex; justify-content: space-between; align-items: center;
  }
  .brand { display: flex; align-items: center; gap: 8px; }
  .brand .dot {
    width: 7px; height: 7px; border-radius: 50%; background: var(--accent);
    box-shadow: 0 0 0 0 var(--accent-dim);
    animation: pulse 2s ease-out infinite;
  }
  @media (prefers-reduced-motion: reduce) { .brand .dot { animation: none; } }
  @keyframes pulse {
    0%   { box-shadow: 0 0 0 0 var(--accent-dim); }
    70%  { box-shadow: 0 0 0 6px transparent; }
    100% { box-shadow: 0 0 0 0 transparent; }
  }
  .brand h1 { font-size: 14px; margin: 0; font-weight: 600; letter-spacing: -0.01em; }

  .budget { text-align: right; }
  .budget .figures { font-family: var(--mono); font-size: 13px; color: var(--text); font-variant-numeric: tabular-nums; }
  .budget .figures .dim { color: var(--text-dim); }
  .budget .bar { width: 140px; height: 3px; background: var(--border); border-radius: 2px; margin-top: 6px; overflow: hidden; }
  .budget .bar-fill { height: 100%; background: var(--accent); border-radius: 2px; transition: width 0.6s ease; width: 0%; }

  .layout {
    max-width: 1020px; margin: 0 auto; padding: 24px 20px 80px;
    display: grid; grid-template-columns: 1fr 260px; gap: 20px; align-items: start;
  }
  @media (max-width: 760px) {
    .layout { grid-template-columns: 1fr; }
    .sidebar { order: -1; }
  }

  .sidebar {
    position: sticky; top: 70px;
    border: 1px solid var(--border); border-radius: 10px; background: var(--surface);
    padding: 14px;
  }
  .sidebar .label {
    font-size: 10.5px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;
    color: var(--text-dim); margin-bottom: 8px;
  }
  .sidebar .headline { font-size: 14px; font-weight: 600; line-height: 1.4; margin-bottom: 4px; }
  .sidebar .detail { font-size: 12.5px; color: var(--text-dim); line-height: 1.45; }
  .sidebar .placeholder { font-size: 12.5px; color: var(--text-faint); font-style: italic; }
  .sidebar .stamp { font-family: var(--mono); font-size: 10.5px; color: var(--text-faint); margin-top: 10px; }

  .entry { margin-bottom: 10px; border-radius: 10px; border: 1px solid var(--border); overflow: hidden; }
  .entry-head {
    display: flex; align-items: baseline; gap: 8px; padding: 10px 14px 0;
  }
  .entry-body {
    padding: 6px 14px 12px; white-space: pre-wrap; word-break: break-word;
    font-size: 13.5px; line-height: 1.55;
  }
  .kind { font-size: 10.5px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; }
  .ts { font-family: var(--mono); font-size: 11px; color: var(--text-faint); }

  .lauren { background: var(--surface); }
  .lauren .kind { color: var(--accent); }
  .lauren .entry-body { color: var(--text); }

  .tool_call { background: var(--surface); }
  .tool_call .kind { color: #7fd99a; }
  .tool_call .entry-body { font-family: var(--mono); font-size: 12px; color: #a7d9b4; }

  .tool_result { background: var(--surface); }
  .tool_result .kind { color: #d2a15a; }
  .tool_result .entry-body { font-family: var(--mono); font-size: 12px; color: #b9ac96; }
  .tool_result .entry-body.collapsed { max-height: 130px; overflow: hidden; position: relative; }
  .tool_result .expand {
    display: block; font-family: var(--sans); font-size: 11.5px; color: var(--text-dim);
    background: var(--surface-2); border: none; border-top: 1px solid var(--border);
    width: 100%; padding: 7px; cursor: pointer; text-align: center;
  }
  .tool_result .expand:hover { color: var(--text); }

  .system { background: transparent; border-style: dashed; }
  .system .kind { color: var(--text-dim); }
  .system .entry-body { color: var(--text-dim); font-size: 12.5px; }
</style>
</head>
<body>
<header>
  <div class="brand"><span class="dot"></span><h1>Lauren Nestor</h1></div>
  <div class="budget">
    <div class="figures" id="figures">connecting<span class="dim">...</span></div>
    <div class="bar"><div class="bar-fill" id="barFill"></div></div>
  </div>
</header>
<div class="layout">
  <div id="feed"></div>
  <aside class="sidebar">
    <div class="label">Currently</div>
    <div id="sidebarBody"><span class="placeholder">No status set yet</span></div>
  </aside>
</div>
<script>
let since = 0;
const feed = document.getElementById('feed');
const figures = document.getElementById('figures');
const barFill = document.getElementById('barFill');
const sidebarBody = document.getElementById('sidebarBody');
const KIND_LABEL = {lauren: 'Lauren', tool_call: 'Tool call', tool_result: 'Tool result', system: 'System'};
const COLLAPSE_THRESHOLD = 600;

function render(entry) {
  const wrap = document.createElement('div');
  wrap.className = 'entry ' + entry.kind;

  const head = document.createElement('div');
  head.className = 'entry-head';
  const kind = document.createElement('span');
  kind.className = 'kind';
  kind.textContent = KIND_LABEL[entry.kind] || entry.kind;
  const ts = document.createElement('span');
  ts.className = 'ts';
  ts.textContent = entry.ts;
  head.appendChild(kind);
  head.appendChild(ts);

  const body = document.createElement('div');
  body.className = 'entry-body';
  body.textContent = entry.text;

  wrap.appendChild(head);
  wrap.appendChild(body);

  if (entry.kind === 'tool_result' && entry.text.length > COLLAPSE_THRESHOLD) {
    body.classList.add('collapsed');
    const btn = document.createElement('button');
    btn.className = 'expand';
    btn.textContent = 'Show full output';
    btn.onclick = () => {
      const collapsed = body.classList.toggle('collapsed');
      btn.textContent = collapsed ? 'Show full output' : 'Collapse';
    };
    wrap.appendChild(btn);
  }

  feed.appendChild(wrap);
}

async function pollLog() {
  try {
    const res = await fetch('/api/log?since=' + since);
    const data = await res.json();
    const nearBottom = window.innerHeight + window.scrollY >= document.body.scrollHeight - 200;
    for (const e of data.entries) render(e);
    if (data.entries.length && nearBottom) window.scrollTo(0, document.body.scrollHeight);
    since = data.total;
  } catch (e) {}
}

async function pollStatus() {
  try {
    const res = await fetch('/api/status');
    const s = await res.json();
    if (s.spent_eur !== undefined) {
      figures.innerHTML = '';
      const spent = document.createElement('span');
      spent.textContent = '€' + s.spent_eur.toFixed(2) + ' / €' + s.cap_eur.toFixed(0);
      const sep = document.createElement('span');
      sep.className = 'dim';
      sep.textContent = '  ' + s.elapsed_hours.toFixed(1) + 'h';
      figures.appendChild(spent);
      figures.appendChild(sep);
      const pct = Math.min(100, (s.spent_eur / s.cap_eur) * 100);
      barFill.style.width = pct + '%';
    }
    if (s.headline) {
      sidebarBody.innerHTML = '';
      const headline = document.createElement('div');
      headline.className = 'headline';
      headline.textContent = s.headline;
      const detail = document.createElement('div');
      detail.className = 'detail';
      detail.textContent = s.detail || '';
      sidebarBody.appendChild(headline);
      sidebarBody.appendChild(detail);
      if (s.status_updated_at) {
        const stamp = document.createElement('div');
        stamp.className = 'stamp';
        stamp.textContent = s.status_updated_at.replace('T', ' ').split('.')[0] + ' UTC';
        sidebarBody.appendChild(stamp);
      }
    }
  } catch (e) {}
}

pollLog(); pollStatus();
setInterval(pollLog, 3000);
setInterval(pollStatus, 10000);
</script>
</body>
</html>"""
