#!/usr/bin/env python3
"""
Lightstreamer-style SSE / Long-Polling backend  (port 8080)
============================================================

Implements the two transport endpoints that the JS client negotiates between:

  GET /lightstreamer/stream  — SSE endpoint
    Sends a "probe" event IMMEDIATELY on connection.
    This is the key to transport detection: a direct connection delivers
    the probe in milliseconds; a buffering proxy holds it back.

  GET /lightstreamer/poll?since=<seq>  — Long-polling endpoint
    Waits up to 20 s for new events, returns JSON, closes connection.
    A buffering proxy can forward complete poll responses (they finish
    within the proxy timeout), so polling always works end-to-end.

  GET /                — Serves the frontend HTML
  GET /app.js          — Serves the frontend JS
"""

import asyncio
import json
import os
import random
import threading
import time

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse

app = FastAPI()

# ── Shared event store ────────────────────────────────────────────────────────

_events: list[dict] = []
_events_lock = threading.Lock()

# ── Demo content ──────────────────────────────────────────────────────────────

QUESTIONS = [
    "How does Python handle memory management?",
    "What is the difference between SSE and WebSockets?",
    "How to implement long polling in FastAPI?",
    "How does Lightstreamer's adaptive streaming work?",
    "How do I scale WebSocket connections horizontally?",
    "What is nginx proxy_buffering and why does it break SSE?",
    "How to deploy a FastAPI service with Docker Compose?",
    "What is the CAP theorem in distributed systems?",
    "How does HTTP/2 server push compare to SSE?",
    "What are Python async/await best practices?",
    "How does chunked transfer encoding work?",
    "What is the difference between push and pull architectures?",
]
AUTHORS    = ["alice", "bob", "charlie", "diana", "eve", "frank", "grace", "hector"]
EVENT_TYPES = ["asked", "answered", "upvoted", "accepted", "commented", "edited"]


def _generate_events() -> None:
    """Background thread: push a new event every ~2 s."""
    seq = 0
    while True:
        time.sleep(random.uniform(1.5, 3.5))
        seq += 1
        q = random.choice(QUESTIONS)
        a = random.choice(AUTHORS)
        et = random.choice(EVENT_TYPES)
        event = {
            "seq":        seq,
            "event_type": et,
            "author":     a,
            "message":    f"{a} {et}: {q[:60]}{'…' if len(q) > 60 else ''}",
            "timestamp":  time.strftime("%H:%M:%S"),
            "stats": {
                "total_questions": random.randint(40, 65),
                "total_answers":   random.randint(120, 170),
                "online_users":    random.randint(3, 18),
            },
        }
        with _events_lock:
            _events.append(event)
            if len(_events) > 500:
                _events.pop(0)


threading.Thread(target=_generate_events, daemon=True, name="event-gen").start()


# ── SSE endpoint ──────────────────────────────────────────────────────────────

@app.get("/lightstreamer/stream")
async def stream_sse():
    """
    SSE streaming endpoint.

    The FIRST thing we send is the 'probe' event.  The JS client starts a
    3-second timer on connect; if the probe arrives before the timer fires,
    streaming is confirmed.  A buffering proxy will hold the probe in its
    buffer — the timer fires, JS closes the EventSource, and starts polling.
    """
    async def generate():
        # ── Probe — must arrive before PROBE_TIMEOUT_MS on the client ────────
        yield "event: probe\ndata: {\"ok\":true}\n\n"

        # ── Initial snapshot (last 5 events) ─────────────────────────────────
        with _events_lock:
            snapshot = list(_events[-5:])

        for evt in snapshot:
            yield f"event: update\ndata: {json.dumps(evt)}\n\n"

        # ── Live stream ───────────────────────────────────────────────────────
        last_count = len(_events)
        while True:
            await asyncio.sleep(0.1)
            with _events_lock:
                new_events   = _events[last_count:]
                last_count   = len(_events)
            for evt in new_events:
                yield f"event: update\ndata: {json.dumps(evt)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":     "no-cache, no-store",
            "X-Accel-Buffering": "no",          # hint to any smart proxy
            "Access-Control-Allow-Origin": "*",
        },
    )


# ── Long-polling endpoint ─────────────────────────────────────────────────────

@app.get("/lightstreamer/poll")
async def poll(since: int = 0):
    """
    Long-polling endpoint.

    Holds the connection open for up to 20 s waiting for new events
    (seq > since).  Returns as soon as events are available, or empty
    after the timeout.  Complete responses pass through buffering proxies
    correctly, so polling always works regardless of proxy settings.
    """
    deadline = time.monotonic() + 20.0
    while time.monotonic() < deadline:
        with _events_lock:
            new = [e for e in _events if e["seq"] > since]
        if new:
            return {"transport": "HTTP-POLLING", "events": new}
        await asyncio.sleep(0.2)
    return {"transport": "HTTP-POLLING", "events": []}


# ── Serve frontend ────────────────────────────────────────────────────────────

_HERE = os.path.dirname(os.path.abspath(__file__))

@app.get("/")
async def index():
    return FileResponse(os.path.join(_HERE, "frontend", "index.html"))

@app.get("/app.js")
async def appjs():
    return FileResponse(os.path.join(_HERE, "frontend", "app.js"))


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n  Backend SSE/poll server  →  http://localhost:8080")
    print("  Open port 3000 or 9090 (via proxy) — not this port directly.\n")
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="warning")
