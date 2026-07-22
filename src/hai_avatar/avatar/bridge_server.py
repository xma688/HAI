"""Small local HTTP server for the Prometheus browser bridge."""

from __future__ import annotations

import logging
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

logger = logging.getLogger(__name__)


class _QuietStaticHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:
        logger.debug("Avatar bridge: " + format, *args)


def start_avatar_bridge_server(
    directory: Path,
    host: str = "127.0.0.1",
    port: int = 7861,
) -> ThreadingHTTPServer:
    """Start a daemonized static server and return its handle."""

    directory.mkdir(parents=True, exist_ok=True)
    handler = partial(_QuietStaticHandler, directory=str(directory))
    server = ThreadingHTTPServer((host, port), handler)
    thread = threading.Thread(
        target=server.serve_forever,
        name="hai-avatar-bridge",
        daemon=True,
    )
    thread.start()
    logger.info("Avatar bridge available at http://%s:%s", host, port)
    return server
