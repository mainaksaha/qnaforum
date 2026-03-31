# Lightstreamer – SSE / Long-Polling Demo

A self-contained demo showing how **Lightstreamer automatically negotiates**
between HTTP Streaming (SSE) and HTTP Long Polling depending on what the
network/proxy between client and server allows.

---

## Architecture

```
                          ┌─────────────────────────────────────────────┐
                          │            Docker network (ls-net)           │
                          │                                              │
  ┌──────────┐  TCP 6661  │  ┌─────────────┐       ┌────────────────┐   │
  │  Python  │──────────► │  │  LS Server  │ :8080  │ direct-nginx   │ :3000 (host)
  │  Backend │  TCP 6662  │  │  (broker)   │◄──────►│  no buffering  │◄────── Browser
  │  Adapter │──────────► │  │             │        │  SSE works     │   │
  └──────────┘  TCP 6663  │  └─────────────┘        └────────────────┘   │
                          │         :8080            ┌────────────────┐   │
                          │                          │  proxy-nginx   │ :9090 (host)
                          │                          │  HTTP/1.0 +    │◄────── Browser
                          │                          │  buffering ON  │   │
                          │                          │  SSE blocked   │   │
                          │                          └────────────────┘   │
                          └─────────────────────────────────────────────┘
```

### Components

| Service | Role |
|---|---|
| `ls-server` | Lightstreamer Community Edition Server. Listens on port 8080 for clients, and on internal ports 6661/6662/6663 for the Remote Adapter. |
| `backend` | Python service using the `lightstreamer-adapter` SDK. Connects to the LS server as a Remote Data Adapter and pushes simulated live Q&A events every ~2 s. |
| `direct-nginx` (port **3000**) | Reverse proxy with **buffering OFF**. HTTP/1.1 with WebSocket upgrade forwarding. SSE and WebSocket streaming work end-to-end. |
| `proxy-nginx` (port **9090**) | Reverse proxy with **buffering ON**, HTTP/1.0, no WebSocket upgrade. Simulates a legacy enterprise proxy. SSE is silently broken. |

---

## Quick Start

```bash
cd lightstreamer-demo
docker compose up --build
```

The Lightstreamer Server (JVM) takes ~20–30 s to start. The Python adapter
retries automatically until it can connect.

### Watch the demo

| URL | Expected transport |
|---|---|
| http://localhost:3000 | **HTTP-STREAMING** (SSE) or **WS-STREAMING** |
| http://localhost:9090 | **HTTP-POLLING** (automatic fallback) |

Open both URLs side-by-side. Both show the **same live feed** from the same
backend. The transport indicator at the top shows what's actually happening.

---

## The "Remove the Proxy" Demo

This is the key point of the demo:

1. Open http://localhost:9090 — note "HTTP Long Polling" in the transport badge.
2. Switch to http://localhost:3000 — the transport indicator changes to
   "HTTP Streaming" or "WebSocket Streaming" automatically.
3. **No code was changed** in the client (`app.js`) or the server
   (`data_adapter.py`). Only the nginx configuration between them differs.

In a real deployment: when the enterprise proxy is retired and the browser
connects directly to Lightstreamer, the transport upgrades to SSE/WebSocket
automatically on the next reconnect.

---

## How the Automatic Fallback Works

Lightstreamer uses a **probe-based transport detection** mechanism:

1. Client requests a streaming session.
2. LS server sends a tiny **probe** message immediately.
3. Client expects the probe within a few seconds.
4. **If the probe arrives** → streaming is confirmed, session continues.
5. **If the probe is buffered** by a proxy and doesn't arrive in time →
   client marks streaming as broken, downgrades to long polling, reconnects.

The `proxy-nginx` buffers up to 2 MB before forwarding anything, so the probe
never arrives in time. The LS client detects this and falls back to polling
— all automatically, all transparently.

---

## Transport Status Values

| Status string | Meaning |
|---|---|
| `CONNECTED:WS-STREAMING` | WebSocket, full-duplex streaming |
| `CONNECTED:HTTP-STREAMING` | HTTP chunked / SSE-style streaming |
| `CONNECTED:HTTP-POLLING` | Long polling (proxy blocks streaming) |
| `CONNECTING` | Transport negotiation in progress |
| `DISCONNECTED:WILL-RETRY` | Temporary failure, retrying |

---

## Files

```
lightstreamer-demo/
├── docker-compose.yml          — Orchestrates all four services
├── nginx-direct.conf           — No-buffering proxy (port 3000)
├── nginx-proxy.conf            — Buffering proxy (port 9090)
├── ls-server/
│   └── adapters/DEMO/
│       └── adapters.xml        — LS adapter configuration (ROBUST_PROXY)
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt        — lightstreamer-adapter==1.3.0
│   └── data_adapter.py         — Remote Data + Metadata adapters
└── frontend/
    ├── index.html              — Demo UI
    └── app.js                  — LightstreamerClient (same code, both ports)
```

---

## Lightstreamer Free Tier

The `lightstreamer:latest` Docker image is the **Community Edition**, which is
free for development / demo use and supports up to 20 concurrent sessions —
more than enough for this demo.
