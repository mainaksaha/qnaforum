#!/usr/bin/env python3
"""
Transport-demo proxy  (pure Python, no nginx needed)
=====================================================

Two modes selected by --mode:

  direct    (--port 3000)
  ──────────────────────
  Forwards response bytes chunk-by-chunk as they arrive from the backend.
  The SSE "probe" event reaches the browser in milliseconds.
  → Browser sees probe within timeout → CONNECTED:HTTP-STREAMING

  buffering  (--port 9090)
  ────────────────────────
  Accumulates the entire response body before forwarding.
  The probe is held in the buffer; the JS probe-timeout fires first.
  JS closes the EventSource and falls back to long polling.
  Poll responses complete in ≤ 20 s → within BUFFER_TIMEOUT → forwarded OK.
  → Browser falls back to → CONNECTED:HTTP-POLLING

Both proxies also serve the frontend HTML/JS by forwarding GET / and GET /app.js
to the backend, so the client always connects to window.location.origin.
"""

import argparse
import asyncio
import sys

import aiohttp
from aiohttp import web

BACKEND = "http://localhost:8080"

# Buffering timeout (seconds).  Must be:
#   > long-poll max wait (20 s)  so polls complete and get forwarded
#   < "forever"                  so streaming connections eventually fail
# We set it comfortably above 20 s:
BUFFER_TIMEOUT = 25


# ── Handlers ──────────────────────────────────────────────────────────────────

async def direct_handler(request: web.Request) -> web.StreamResponse:
    """Pass-through: stream every chunk immediately as it arrives."""
    url = BACKEND + request.path_qs
    conn = aiohttp.TCPConnector()
    timeout = aiohttp.ClientTimeout(total=3600)

    async with aiohttp.ClientSession(connector=conn, timeout=timeout) as session:
        try:
            fwd_headers = {
                k: v for k, v in request.headers.items()
                if k.lower() not in ("host", "content-length", "connection")
            }
            body = await request.read() if request.method in ("POST", "PUT", "PATCH") else None

            async with session.request(
                request.method, url, headers=fwd_headers, data=body
            ) as resp:
                resp_headers = {
                    k: v for k, v in resp.headers.items()
                    if k.lower() not in ("transfer-encoding", "content-length",
                                         "connection", "keep-alive")
                }
                response = web.StreamResponse(status=resp.status, headers=resp_headers)
                await response.prepare(request)

                # !! Forward every chunk without delay — SSE works
                async for chunk in resp.content.iter_any():
                    await response.write(chunk)

                return response

        except aiohttp.ClientError as exc:
            return web.Response(status=502, text=f"Upstream error: {exc}")


async def buffering_handler(request: web.Request) -> web.Response:
    """
    Buffer mode: accumulate the full body before replying.

    SSE streams never finish → asyncio.wait_for times out → 504 returned.
    The JS probe-timeout (3 s) fires well before the buffer timeout (25 s),
    so the client has already switched to polling before the 504 arrives.

    Poll responses complete within 0–20 s → forwarded intact.
    """
    url = BACKEND + request.path_qs
    timeout = aiohttp.ClientTimeout(total=BUFFER_TIMEOUT + 5)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            fwd_headers = {
                k: v for k, v in request.headers.items()
                if k.lower() not in ("host", "content-length", "connection")
            }
            body = await request.read() if request.method in ("POST", "PUT", "PATCH") else None

            async with session.request(
                request.method, url, headers=fwd_headers, data=body
            ) as resp:
                resp_headers = {
                    k: v for k, v in resp.headers.items()
                    if k.lower() not in ("transfer-encoding", "content-length",
                                         "connection", "keep-alive")
                }
                try:
                    # !! Buffer entire body — SSE probe is held here, never forwarded
                    full_body = await asyncio.wait_for(resp.read(), timeout=BUFFER_TIMEOUT)
                    return web.Response(
                        status=resp.status,
                        headers=resp_headers,
                        body=full_body,
                    )
                except asyncio.TimeoutError:
                    # Streaming response timed out in the buffer → kill it
                    # (By this point the JS has already fallen back to polling)
                    return web.Response(
                        status=504,
                        text="Gateway Timeout — simulated buffering proxy killed the stream",
                    )

        except aiohttp.ServerDisconnectedError:
            return web.Response(status=502, text="Backend disconnected")
        except aiohttp.ClientError as exc:
            return web.Response(status=502, text=f"Upstream error: {exc}")


# ── App factory ───────────────────────────────────────────────────────────────

def build_app(mode: str) -> web.Application:
    handler = direct_handler if mode == "direct" else buffering_handler
    app = web.Application()
    # Catch-all route
    app.router.add_route("*", "/{path_info:.*}", handler)
    return app


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Transport-demo proxy")
    parser.add_argument(
        "--mode", choices=["direct", "buffering"], required=True,
        help="direct = pass-through (SSE works); buffering = simulate dumb proxy (SSE breaks)"
    )
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()

    labels = {
        "direct":    "pass-through, no buffering  →  SSE / streaming WORKS",
        "buffering": f"response buffering (timeout {BUFFER_TIMEOUT}s)  →  SSE BLOCKED, polling fallback",
    }
    print(f"\n  [{args.mode.upper()}] :{args.port}  —  {labels[args.mode]}\n")

    web.run_app(build_app(args.mode), host="0.0.0.0", port=args.port, print=False)
