/**
 * Lightstreamer-style adaptive transport negotiator
 * ==================================================
 *
 * Implements the same probe-based detection that Lightstreamer uses:
 *
 *   1. Open an EventSource to /lightstreamer/stream
 *   2. Start a PROBE_TIMEOUT_MS timer
 *   3. Server sends "probe" event IMMEDIATELY on connection
 *      a. Probe received before timeout  → streaming confirmed
 *         → status: CONNECTED:HTTP-STREAMING
 *      b. Timer fires (proxy held the probe in its buffer)
 *         → close EventSource, switch to long-polling loop
 *         → status: CONNECTED:HTTP-POLLING
 *
 * The client always connects to window.location.origin, so the nginx/proxy
 * in front decides the transport — the JS code never changes.
 */

"use strict";

// ── How long to wait for the probe before giving up on streaming ──────────────
const PROBE_TIMEOUT_MS = 3000;

// ── Transport display config ──────────────────────────────────────────────────
const TRANSPORT_INFO = {
  "CONNECTED:HTTP-STREAMING": {
    label: "HTTP Streaming (SSE)",
    color: "#3b82f6",
    cls:   "http-streaming",
    desc:  "Server-Sent Events streaming confirmed. Probe received instantly — " +
           "no buffering proxy in the way. Data flows continuously without polling.",
  },
  "CONNECTED:HTTP-POLLING": {
    label: "HTTP Long Polling",
    color: "#f59e0b",
    cls:   "http-polling",
    desc:  "Long-polling fallback active. The proxy buffered the response — " +
           "the SSE probe never arrived within the timeout. " +
           "Transport switched automatically. No code changed.",
  },
  "CONNECTING": {
    label: "Connecting…",
    color: "#6b7280",
    cls:   "connecting",
    desc:  "Probing transport — waiting for SSE probe event (timeout: 3 s)…",
  },
};

// ── DOM helpers ───────────────────────────────────────────────────────────────

const $ = id => document.getElementById(id);

let feedCount = 0;

function setStatus(key) {
  const info = TRANSPORT_INFO[key] || TRANSPORT_INFO["CONNECTING"];
  $("transport-raw").textContent   = key;
  $("transport-label").textContent = info.label;
  $("transport-desc").textContent  = info.desc;
  $("dot").style.background        = info.color;
  $("transport-card").className    = `transport-card ${info.cls}`;
  if (key.startsWith("CONNECTED")) {
    $("dot").classList.add("pulse");
  } else {
    $("dot").classList.remove("pulse");
  }
}

function flashValue(id, val) {
  const el = $(id);
  if (!el || val == null) return;
  el.textContent = val;
  el.classList.remove("flash");
  void el.offsetWidth;          // force reflow to restart animation
  el.classList.add("flash");
  setTimeout(() => el.classList.remove("flash"), 600);
}

function appendFeedItem(evt) {
  const list = $("feed-list");
  const ph   = list.querySelector(".placeholder");
  if (ph) ph.remove();

  feedCount++;
  $("feed-counter").textContent = `${feedCount} event${feedCount !== 1 ? "s" : ""}`;

  const li = document.createElement("li");
  li.className = "feed-item";
  li.innerHTML = `
    <span class="feed-time">${evt.timestamp  || ""}</span>
    <span class="feed-badge ${evt.event_type || ""}">${evt.event_type || ""}</span>
    <span class="feed-msg">${evt.message    || ""}</span>
  `;
  list.insertBefore(li, list.firstChild);
  while (list.children.length > 30) list.removeChild(list.lastChild);
}

function handleEvent(evt) {
  appendFeedItem(evt);
  if (evt.stats) {
    flashValue("total_questions", evt.stats.total_questions);
    flashValue("total_answers",   evt.stats.total_answers);
    flashValue("online_users",    evt.stats.online_users);
    flashValue("last_update",     evt.timestamp);
  }
}

// ── Scenario banner ───────────────────────────────────────────────────────────

function renderScenarioBanner() {
  const port   = window.location.port;
  const banner = $("scenario-banner");
  const isDirect = (port === "3000" || port === "");

  if (isDirect) {
    banner.className = "scenario-banner direct";
    banner.innerHTML =
      "<strong>Scenario A — Direct (port 3000).</strong> " +
      "Pass-through proxy: chunks forwarded immediately. " +
      "SSE probe arrives in &lt;50 ms → streaming confirmed. " +
      "Switch to <a href='http://" + location.hostname + ":9090' " +
        "style='color:#86efac'>port 9090</a> to see the proxy scenario.";
  } else {
    banner.className = "scenario-banner proxy";
    banner.innerHTML =
      "<strong>Scenario B — Buffering proxy (port 9090).</strong> " +
      "Response body is buffered before forwarding. " +
      "SSE probe is held; probe timeout fires → automatic polling fallback. " +
      "Switch to <a href='http://" + location.hostname + ":3000' " +
        "style='color:#fcd34d'>port 3000</a> for streaming.";
  }
}

// ── Transport Negotiator ──────────────────────────────────────────────────────

class TransportNegotiator {
  constructor() {
    this._sse        = null;
    this._probeTimer = null;
    this._polling    = false;
    this._lastSeq    = 0;
  }

  start() {
    renderScenarioBanner();
    setStatus("CONNECTING");
    this._tryStreaming();
  }

  // ── Step 1: Try SSE ─────────────────────────────────────────────────────────

  _tryStreaming() {
    let probeReceived = false;

    // !! The probe timer is the core of Lightstreamer-style transport detection.
    //    If the probe SSE event isn't received within PROBE_TIMEOUT_MS, we assume
    //    a proxy is buffering the stream and fall back to long polling.
    this._probeTimer = setTimeout(() => {
      if (!probeReceived) {
        console.log(
          `[transport] Probe not received after ${PROBE_TIMEOUT_MS} ms` +
          " — proxy is buffering → switching to long polling"
        );
        this._closeSSE();
        this._startPolling();
      }
    }, PROBE_TIMEOUT_MS);

    this._sse = new EventSource("/lightstreamer/stream");

    // "probe" event: server sends this the moment the connection is accepted.
    this._sse.addEventListener("probe", () => {
      if (probeReceived) return;   // guard against duplicates
      probeReceived = true;
      clearTimeout(this._probeTimer);
      console.log("[transport] Probe received → HTTP-STREAMING confirmed");
      setStatus("CONNECTED:HTTP-STREAMING");
    });

    // "update" event: live data
    this._sse.addEventListener("update", (e) => {
      try { handleEvent(JSON.parse(e.data)); } catch (_) { /* ignore */ }
    });

    // Connection error before probe → fall back to polling
    this._sse.onerror = () => {
      if (!probeReceived) {
        clearTimeout(this._probeTimer);
        this._closeSSE();
        console.log("[transport] EventSource error before probe → polling fallback");
        this._startPolling();
      }
    };
  }

  _closeSSE() {
    if (this._sse) { this._sse.close(); this._sse = null; }
  }

  // ── Step 2: Long-polling loop ───────────────────────────────────────────────

  _startPolling() {
    if (this._polling) return;
    this._polling = true;
    setStatus("CONNECTED:HTTP-POLLING");
    console.log("[transport] Long-polling loop started");
    this._poll();
  }

  async _poll() {
    if (!this._polling) return;
    try {
      // Send since= so the server only returns events we haven't seen yet.
      // The server holds the response open up to 20 s (long-poll style),
      // then returns — even through a buffering proxy that waits for the
      // full response body.
      const res = await fetch(`/lightstreamer/poll?since=${this._lastSeq}`);
      if (res.ok) {
        const data = await res.json();
        for (const evt of (data.events || [])) {
          this._lastSeq = Math.max(this._lastSeq, evt.seq || 0);
          handleEvent(evt);
        }
      }
    } catch (err) {
      console.warn("[transport] Poll error:", err);
      // Back off briefly on network error
      await new Promise(r => setTimeout(r, 2000));
    }
    // Restart immediately — the server already does the long-hold,
    // so this tight loop is fine (no hot-spinning).
    setTimeout(() => this._poll(), 50);
  }
}

// ── Boot ──────────────────────────────────────────────────────────────────────
window.addEventListener("load", () => new TransportNegotiator().start());
