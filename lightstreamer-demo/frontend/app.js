/**
 * Lightstreamer SSE / Long-Polling Demo – Frontend Logic
 * ========================================================
 *
 * KEY POINT: The LightstreamerClient always connects to window.location.origin.
 * The nginx in front decides whether streaming is allowed or not.
 *
 *   Port 3000  →  nginx-direct  →  no buffering  →  SSE / WebSocket works
 *   Port 9090  →  nginx-proxy   →  buffering on  →  must fall back to polling
 *
 * Zero code changes needed in this file between the two scenarios.
 * Transport negotiation is entirely automatic inside the LS client SDK.
 */

"use strict";

// ── Transport metadata ────────────────────────────────────────────────────────

const TRANSPORTS = {
  "WS-STREAMING": {
    label: "WebSocket Streaming",
    color: "#22c55e",
    cls:   "ws-streaming",
    desc:  "Full-duplex WebSocket streaming. No proxy in the way — data flows in real time over a persistent connection.",
  },
  "HTTP-STREAMING": {
    label: "HTTP Streaming (SSE)",
    color: "#3b82f6",
    cls:   "http-streaming",
    desc:  "Server-Sent Events (HTTP streaming). The proxy supports persistent connections — events are pushed continuously from server to client.",
  },
  "HTTP-POLLING": {
    label: "HTTP Long Polling",
    color: "#f59e0b",
    cls:   "http-polling",
    desc:  "Long Polling fallback. A proxy is buffering the response stream, breaking SSE. Lightstreamer detected the failure and switched automatically — no code change required.",
  },
  "WS-POLLING": {
    label: "WebSocket Polling",
    color: "#f59e0b",
    cls:   "http-polling",
    desc:  "WebSocket in polling mode — short-lived request/response cycles over WS.",
  },
};

// ── DOM helpers ───────────────────────────────────────────────────────────────

const $ = id => document.getElementById(id);

function flashValue(id, newVal) {
  const el = $(id);
  if (!el) return;
  el.textContent = newVal;
  el.classList.remove("flash");
  void el.offsetWidth; // force reflow
  el.classList.add("flash");
  setTimeout(() => el.classList.remove("flash"), 600);
}

let feedCount = 0;

function appendFeedItem(data) {
  const list = $("feed-list");
  const placeholder = list.querySelector(".placeholder");
  if (placeholder) placeholder.remove();

  feedCount++;
  $("feed-counter").textContent = `${feedCount} event${feedCount !== 1 ? "s" : ""}`;

  const li = document.createElement("li");
  li.className = "feed-item";
  li.innerHTML = `
    <span class="feed-time">${data.timestamp || ""}</span>
    <span class="feed-badge ${data.event_type || ""}">${data.event_type || ""}</span>
    <span class="feed-msg">${data.message || ""}</span>
  `;
  list.insertBefore(li, list.firstChild);
  // Keep feed manageable
  while (list.children.length > 30) list.removeChild(list.lastChild);
}

// ── Transport UI ──────────────────────────────────────────────────────────────

function applyTransportUI(rawStatus) {
  $("transport-raw").textContent = rawStatus;

  const key  = Object.keys(TRANSPORTS).find(k => rawStatus.includes(k));
  const card = $("transport-card");
  const dot  = $("dot");

  if (key) {
    const t = TRANSPORTS[key];
    $("transport-label").textContent = t.label;
    $("transport-desc").textContent  = t.desc;
    dot.style.background             = t.color;
    dot.classList.add("pulse");
    card.className = `transport-card ${t.cls}`;

  } else if (rawStatus.startsWith("CONNECTED")) {
    $("transport-label").textContent = rawStatus;
    $("transport-desc").textContent  = "";
    dot.style.background             = "#22c55e";
    dot.classList.add("pulse");
    card.className = "transport-card";

  } else if (rawStatus === "DISCONNECTED" || rawStatus.startsWith("DISCONNECTED")) {
    $("transport-label").textContent = "Disconnected";
    $("transport-desc").textContent  = "Connection lost. Retrying…";
    dot.style.background             = "#ef4444";
    dot.classList.remove("pulse");
    card.className = "transport-card disconnected";

  } else {
    // CONNECTING or any transitional state
    $("transport-label").textContent = rawStatus;
    $("transport-desc").textContent  = "Negotiating transport…";
    dot.style.background             = "#6b7280";
    dot.classList.remove("pulse");
    card.className = "transport-card connecting";
  }
}

// ── Scenario banner ───────────────────────────────────────────────────────────

function renderScenarioBanner() {
  const port    = window.location.port;
  const banner  = $("scenario-banner");
  const isDirect = (port === "3000" || port === "");

  if (isDirect) {
    banner.className   = "scenario-banner direct";
    banner.innerHTML   =
      "<strong>Scenario A — No proxy.</strong>  " +
      "You are connected directly to the Lightstreamer Server via the streaming-friendly nginx. " +
      "Expect <strong>WS-STREAMING</strong> or <strong>HTTP-STREAMING</strong>. " +
      "Switch to <a href='http://" + location.hostname + ":9090' style='color:#86efac'>port 9090</a> to see the proxy scenario.";
  } else {
    banner.className   = "scenario-banner proxy";
    banner.innerHTML   =
      "<strong>Scenario B — Dumb proxy in the way.</strong>  " +
      "The nginx at port 9090 buffers responses and strips WebSocket headers, " +
      "simulating a legacy enterprise proxy. " +
      "Lightstreamer will automatically fall back to <strong>HTTP-POLLING</strong>. " +
      "Switch to <a href='http://" + location.hostname + ":3000' style='color:#fcd34d'>port 3000</a> for direct streaming.";
  }
}

// ── Lightstreamer client ──────────────────────────────────────────────────────

function startClient() {
  renderScenarioBanner();

  /**
   * Always connect to window.location.origin so the request goes through
   * whichever nginx is serving this page.  That nginx decides whether to
   * stream or buffer — the client code never needs to change.
   */
  const client = new LightstreamerClient(window.location.origin, "DEMO");

  // ── Connection listener ──────────────────────────────────────────────────
  client.addListener({
    onStatusChange(status) {
      console.log("[LS] status →", status);
      applyTransportUI(status);
    },
    onServerError(code, message) {
      console.error("[LS] server error", code, message);
      applyTransportUI("SERVER ERROR " + code + ": " + message);
    },
  });

  // ── Live feed subscription (DISTINCT = each update is a new distinct event)
  const feedSub = new Subscription(
    "DISTINCT",
    ["live_feed"],
    ["seq", "event_type", "author", "message", "timestamp"],
  );
  feedSub.setRequestedMaxFrequency("unlimited");
  feedSub.addListener({
    onItemUpdate(info) {
      appendFeedItem({
        seq:        info.getValue("seq"),
        event_type: info.getValue("event_type"),
        author:     info.getValue("author"),
        message:    info.getValue("message"),
        timestamp:  info.getValue("timestamp"),
      });
    },
    onSubscriptionError(code, msg) {
      console.error("[LS] feed subscription error", code, msg);
    },
  });

  // ── Stats subscription (MERGE = latest value per field)
  const statsSub = new Subscription(
    "MERGE",
    ["stats"],
    ["total_questions", "total_answers", "online_users", "last_update"],
  );
  statsSub.addListener({
    onItemUpdate(info) {
      ["total_questions", "total_answers", "online_users", "last_update"].forEach(f => {
        const v = info.getValue(f);
        if (v !== null) flashValue(f, v);
      });
    },
  });

  client.subscribe(feedSub);
  client.subscribe(statsSub);
  client.connect();
}

// ── Boot ──────────────────────────────────────────────────────────────────────
window.addEventListener("load", startClient);
