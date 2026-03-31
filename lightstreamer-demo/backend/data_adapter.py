#!/usr/bin/env python3
"""
Lightstreamer Demo – Remote Data Adapter
=========================================
This service is the "producer" side of the demo.

It implements the Lightstreamer Remote Adapter Interface (RAI):
  • MetadataProviderServer  – tells LS which items/fields/modes are valid
  • DataProviderServer      – pushes real-time item updates to LS Server

The LS Server opens three TCP ports (6661 / 6662 / 6663) and this process
connects back to them.  Once connected, every call to
  self._listener.update(item_name, {field: value, …}, is_snapshot)
is forwarded to every subscribed client in real time.

Transports used by clients are completely transparent to this adapter.
"""

import os
import time
import random
import socket
import threading
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

from lightstreamer_adapter.interfaces.data import DataProvider
from lightstreamer_adapter.interfaces.metadata import MetadataProvider
from lightstreamer_adapter.server import DataProviderServer, MetadataProviderServer


# ── Simulated live Q&A content ────────────────────────────────────────────────

QUESTIONS = [
    "How does Python's GIL affect multi-threaded performance?",
    "What is the difference between SSE and WebSockets?",
    "How to implement long polling with FastAPI?",
    "How does Lightstreamer's adaptive transport work?",
    "How do I scale WebSocket connections horizontally?",
    "What is nginx proxy_buffering and why does it break SSE?",
    "How to deploy a FastAPI service with Docker Compose?",
    "What is the CAP theorem in distributed systems?",
    "How does HTTP/2 server push compare to SSE?",
    "What are best practices for Python async/await?",
    "How does Lightstreamer fall back from SSE to long polling?",
    "What is chunked transfer encoding and why does it matter?",
]

AUTHORS = ["alice", "bob", "charlie", "diana", "eve", "frank", "grace", "hector"]
EVENT_TYPES = ["asked", "answered", "upvoted", "accepted", "commented", "edited"]


# ── Data Adapter ──────────────────────────────────────────────────────────────

class DemoDataAdapter(DataProvider):
    """
    Pushes two logical items:

      live_feed  (DISTINCT)  – append-only event log; every update is a new row
      stats      (MERGE)     – counters; each update overwrites previous values
    """

    def __init__(self):
        self._listener = None
        self._subscribed: set = set()
        self._lock = threading.Lock()
        self._worker: threading.Thread | None = None

    # ── DataProvider interface ────────────────────────────────────────────────

    def initialize(self, params, config_file=None):
        log.info("DataAdapter.initialize  params=%s", params)

    def set_listener(self, event_listener):
        self._listener = event_listener
        log.info("DataAdapter: event listener attached")

    def subscribe(self, item_name: str):
        log.info("DataAdapter.subscribe(%s)", item_name)
        with self._lock:
            self._subscribed.add(item_name)
            if self._worker is None:
                self._worker = threading.Thread(
                    target=self._run, daemon=True, name="update-worker"
                )
                self._worker.start()

    def unsubscribe(self, item_name: str):
        log.info("DataAdapter.unsubscribe(%s)", item_name)
        with self._lock:
            self._subscribed.discard(item_name)

    def isSnapshotAvailable(self, item_name: str) -> bool:
        # Provide a snapshot for stats so clients see initial values instantly
        return item_name == "stats"

    # ── Internal update loop ─────────────────────────────────────────────────

    def _push(self, item: str, data: dict, snapshot: bool = False):
        if not self._listener:
            return
        # All field values must be strings for the LS protocol
        payload = {k: str(v) for k, v in data.items()}
        try:
            self._listener.update(item, payload, snapshot)
        except Exception as exc:
            log.warning("update failed: %s", exc)

    def _run(self):
        """Continuously generate simulated live updates."""
        # Send initial snapshot so new subscribers see current stats right away
        self._push(
            "stats",
            {
                "total_questions": 42,
                "total_answers": 128,
                "online_users": 7,
                "last_update": time.strftime("%H:%M:%S"),
            },
            snapshot=True,
        )
        log.info("Snapshot sent; starting live update loop…")

        seq = 0
        while True:
            time.sleep(random.uniform(1.5, 3.5))
            seq += 1

            with self._lock:
                items = set(self._subscribed)

            if not items:
                continue

            author = random.choice(AUTHORS)
            event = random.choice(EVENT_TYPES)
            question = random.choice(QUESTIONS)
            ts = time.strftime("%H:%M:%S")
            short_q = question[:55] + ("…" if len(question) > 55 else "")

            if "live_feed" in items:
                self._push(
                    "live_feed",
                    {
                        "seq": seq,
                        "event_type": event,
                        "author": author,
                        "message": f"{author} {event}: {short_q}",
                        "timestamp": ts,
                    },
                )

            if "stats" in items:
                self._push(
                    "stats",
                    {
                        "total_questions": random.randint(40, 65),
                        "total_answers": random.randint(120, 170),
                        "online_users": random.randint(3, 18),
                        "last_update": ts,
                    },
                )


# ── Metadata Adapter ──────────────────────────────────────────────────────────

class DemoMetadataAdapter(MetadataProvider):
    """
    Permissive metadata adapter – allows any authenticated (anonymous) user
    to subscribe to any item in any mode.

    In a production system this is where you'd enforce ACLs, rate limits, etc.
    """

    def initialize(self, params, config_file=None):
        log.info("MetadataAdapter.initialize  params=%s", params)

    def get_items(self, user, session_id, group: str):
        """Map group string → list of item names.
        The JS client sends items separated by spaces."""
        return [i.strip() for i in group.replace(",", " ").split() if i.strip()]

    def get_schema(self, user, session_id, schema: str, group: str):
        """Map schema string → list of field names."""
        return [f.strip() for f in schema.replace(",", " ").split() if f.strip()]

    def ismode_allowed(self, user, item, mode) -> bool:
        return True  # allow MERGE, DISTINCT, COMMAND, RAW

    def get_allowed_max_bandwidth(self, user) -> float:
        return 0.0  # unlimited

    def get_allowed_max_item_frequency(self, user, item) -> float:
        return 0.0  # unlimited

    def get_allowed_buffer_size(self, user, item) -> int:
        return 0  # unlimited

    def get_min_source_frequency(self, item) -> float:
        return 0.0  # no minimum forced

    def get_distinct_snapshot_length(self, item) -> int:
        return 0  # no snapshot for DISTINCT items


# ── Startup helpers ───────────────────────────────────────────────────────────

def wait_for_port(host: str, port: int, retries: int = 30, delay: float = 3.0):
    """Block until the LS server's TCP port is accepting connections."""
    for attempt in range(1, retries + 1):
        try:
            with socket.create_connection((host, port), timeout=2):
                log.info("✓ %s:%d is ready", host, port)
                return
        except (ConnectionRefusedError, OSError):
            log.info("  Waiting for %s:%d  [%d/%d]…", host, port, attempt, retries)
            time.sleep(delay)
    raise RuntimeError(f"Cannot reach {host}:{port} after {retries} attempts")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    LS_HOST = os.getenv("LS_HOST", "ls-server")
    PORT_DATA = int(os.getenv("LS_PORT_DATA", "6661"))
    PORT_NOTIFY = int(os.getenv("LS_PORT_NOTIFY", "6662"))
    PORT_META = int(os.getenv("LS_PORT_METADATA", "6663"))

    # The LS server takes ~10-15 s to start (JVM warm-up + adapter port binding)
    wait_for_port(LS_HOST, PORT_META)
    # Brief extra pause so LS has finished initialising all adapter ports
    time.sleep(2)

    data_adapter = DemoDataAdapter()
    metadata_adapter = DemoMetadataAdapter()

    metadata_server = MetadataProviderServer(
        adapter=metadata_adapter,
        address=(LS_HOST, PORT_META),
    )
    data_server = DataProviderServer(
        adapter=data_adapter,
        address=(LS_HOST, PORT_DATA),
        notify_address=(LS_HOST, PORT_NOTIFY),
    )

    try:
        log.info("Connecting metadata adapter → %s:%d", LS_HOST, PORT_META)
        metadata_server.start()
        log.info("Connecting data adapter     → %s:%d  notify:%d", LS_HOST, PORT_DATA, PORT_NOTIFY)
        data_server.start()
        log.info("=" * 60)
        log.info("Adapters live — pushing events to Lightstreamer Server")
        log.info("=" * 60)
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        log.info("Shutting down…")
        data_server.stop()
        metadata_server.stop()
