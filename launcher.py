"""Start Back Quip on the first available local port, or reuse an existing instance."""
from __future__ import annotations

import json
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser

import uvicorn

HOST = "127.0.0.1"
FIRST_PORT = 8001
LAST_PORT = 8100
CURRENT_VERSION = "1.1.2"


def is_back_quip(port: int) -> bool:
    """Only reuse a service that identifies itself as Back Quip."""
    try:
        with urllib.request.urlopen(
            f"http://{HOST}:{port}/api/status", timeout=0.4
        ) as response:
            if response.status != 200:
                return False
            data = json.load(response)
    except (OSError, ValueError, urllib.error.URLError):
        return False
    if not isinstance(data, dict):
        return False
    # v1.1+ has an explicit app identifier; recognize existing v0.9+/v1.0 too.
    return data.get("application") == "back-quip" or (
        isinstance(data.get("version"), str)
        and isinstance(data.get("connected"), bool)
        and isinstance(data.get("models"), list)
        and isinstance(data.get("install"), dict)
    )


def existing_instance() -> int | None:
    for port in range(FIRST_PORT, LAST_PORT + 1):
        # A TCP probe avoids slow HTTP timeouts on unused ports.
        try:
            with socket.create_connection((HOST, port), timeout=0.08):
                pass
        except OSError:
            continue
        if is_back_quip(port):
            try:
                with urllib.request.urlopen(f"http://{HOST}:{port}/api/status", timeout=0.5) as response:
                    running_version = json.load(response).get("version")
            except (OSError, ValueError):
                running_version = None
            if running_version == CURRENT_VERSION:
                return port
            print(f"[Back Quip] An older version is running on port {port}; starting v{CURRENT_VERSION} separately.", flush=True)
    return None


def reserve_port() -> tuple[socket.socket, int]:
    for port in range(FIRST_PORT, LAST_PORT + 1):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Exclusive binding helps avoid accidentally sharing a Windows port.
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        try:
            sock.bind((HOST, port))
            sock.listen(2048)
            return sock, port
        except OSError:
            sock.close()
    raise RuntimeError(f"No available local port between {FIRST_PORT} and {LAST_PORT}.")


def open_when_ready(port: int) -> None:
    # Avoid opening a stale page if the server fails to start.
    for _ in range(60):
        if is_back_quip(port):
            webbrowser.open(f"http://{HOST}:{port}")
            return
        time.sleep(0.25)


def main() -> int:
    prior = existing_instance()
    if prior is not None:
        url = f"http://{HOST}:{prior}"
        print(f"[Back Quip] Already running at {url}", flush=True)
        webbrowser.open(url)
        return 0
    try:
        server_socket, port = reserve_port()
    except RuntimeError as exc:
        print(f"[Back Quip] {exc}", file=sys.stderr, flush=True)
        return 1
    if port != FIRST_PORT:
        print(f"[Back Quip] Port {FIRST_PORT} is occupied. Using {port}.", flush=True)
    print(f"[Back Quip] Starting at http://{HOST}:{port}", flush=True)
    threading.Thread(target=open_when_ready, args=(port,), daemon=True).start()
    try:
        config = uvicorn.Config("app:app", host=HOST, port=port, log_level="info")
        uvicorn.Server(config).run(sockets=[server_socket])
    finally:
        server_socket.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
