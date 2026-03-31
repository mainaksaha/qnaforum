#!/usr/bin/env python3
"""
Single-command launcher for the local (no-Docker) demo.

Usage:
    cd lightstreamer-demo/local
    python start.py

What it starts:
    :8080  backend  — FastAPI SSE + long-polling server
    :3000  direct   — pass-through proxy, SSE works
    :9090  buffering— buffering proxy, SSE breaks → polling fallback

Then open:
    http://localhost:3000  →  CONNECTED:HTTP-STREAMING
    http://localhost:9090  →  CONNECTED:HTTP-POLLING   (automatic fallback)
"""

import os
import subprocess
import sys
import time
import signal
import socket

HERE = os.path.dirname(os.path.abspath(__file__))
PY   = sys.executable


def install_deps() -> None:
    req = os.path.join(HERE, "requirements.txt")
    print("  Installing dependencies…")
    subprocess.check_call(
        [PY, "-m", "pip", "install", "-q", "-r", req],
        stdout=subprocess.DEVNULL,
    )
    print("  Dependencies OK.\n")


def wait_for_port(port: int, timeout: float = 15.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return True
        except OSError:
            time.sleep(0.3)
    return False


def main() -> None:
    os.chdir(HERE)

    print("\n" + "=" * 60)
    print("  Lightstreamer-style SSE / Long-Polling Demo")
    print("=" * 60 + "\n")

    install_deps()

    procs: list[tuple[subprocess.Popen, str]] = []

    def launch(args: list[str], label: str) -> subprocess.Popen:
        p = subprocess.Popen([PY] + args, cwd=HERE)
        procs.append((p, label))
        return p

    def stop_all() -> None:
        print("\n  Stopping all processes…")
        for p, lbl in procs:
            p.terminate()
        for p, lbl in procs:
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()

    # ── Start backend ─────────────────────────────────────────────────────────
    print("  [1/3] Starting backend server on :8080…")
    launch(["server.py"], "backend :8080")

    if not wait_for_port(8080, timeout=20):
        print("  ERROR: backend didn't start in time.")
        stop_all()
        sys.exit(1)
    print("        Backend ready.\n")

    # ── Start direct proxy ────────────────────────────────────────────────────
    print("  [2/3] Starting direct proxy on :3000 (SSE works)…")
    launch(["proxy.py", "--mode", "direct", "--port", "3000"], "direct :3000")

    # ── Start buffering proxy ─────────────────────────────────────────────────
    print("  [3/3] Starting buffering proxy on :9090 (SSE blocked)…")
    launch(["proxy.py", "--mode", "buffering", "--port", "9090"], "buffering :9090")

    time.sleep(1)

    print("\n" + "=" * 60)
    print("  DEMO IS RUNNING")
    print("=" * 60)
    print()
    print("  http://localhost:3000  →  No proxy in the way")
    print("                            Expected: CONNECTED:HTTP-STREAMING")
    print()
    print("  http://localhost:9090  →  Buffering proxy in the way")
    print("                            Expected: CONNECTED:HTTP-POLLING")
    print()
    print("  Open both URLs side-by-side.")
    print("  The transport badge updates automatically — zero code change.")
    print()
    print("  Press Ctrl-C to stop.\n")
    print("=" * 60 + "\n")

    # ── Wait ──────────────────────────────────────────────────────────────────
    def _sig_handler(sig, frame):
        stop_all()
        sys.exit(0)

    signal.signal(signal.SIGINT,  _sig_handler)
    signal.signal(signal.SIGTERM, _sig_handler)

    # Keep main thread alive; exit if any child dies unexpectedly
    while True:
        for p, lbl in procs:
            if p.poll() is not None:
                print(f"\n  Process '{lbl}' exited unexpectedly (code {p.returncode}).")
                stop_all()
                sys.exit(1)
        time.sleep(1)


if __name__ == "__main__":
    main()
