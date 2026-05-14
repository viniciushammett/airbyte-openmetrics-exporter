from __future__ import annotations

import json
import logging
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from prometheus_client.exposition import CONTENT_TYPE_LATEST, generate_latest

from app.config import Settings, configure_logging
from app.db import execute_query, get_connection
from app.metrics import METRICS_LOCK, MetricsManager
from app.queries import DB_PING

logger = logging.getLogger(__name__)


class ExporterServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int], handler_class: type[BaseHTTPRequestHandler], settings: Settings) -> None:
        super().__init__(server_address, handler_class)
        self.settings = settings
        self.metrics_manager = MetricsManager(settings)


class ExporterHandler(BaseHTTPRequestHandler):
    server: ExporterServer

    def log_message(self, fmt: str, *args: Any) -> None:
        logger.debug("http %s", fmt % args)

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_text(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]

        if path == "/livez":

            self._send_json(HTTPStatus.OK, {"status": "alive"})
            return

        if path == "/healthz":
            self._handle_healthz()
            return

        if path == "/metrics":
            self._handle_metrics()
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def _handle_healthz(self) -> None:
        try:
            with get_connection(self.server.settings) as conn:
                execute_query(conn, DB_PING)
            self._send_json(HTTPStatus.OK, {"status": "ready"})
        except Exception as exc:
            self._send_json(
                HTTPStatus.SERVICE_UNAVAILABLE,
                {"status": "not_ready", "reason": exc.__class__.__name__},
            )

    def _handle_metrics(self) -> None:
        manager = self.server.metrics_manager
        manager.collect_if_needed()
        with METRICS_LOCK:
            body = generate_latest(manager.registry)
        self._send_text(HTTPStatus.OK, body, CONTENT_TYPE_LATEST)


def main() -> None:
    settings = Settings()
    configure_logging(settings)
    server = ExporterServer((settings.exporter_host, settings.exporter_port), ExporterHandler, settings)
    logger.info(
        "starting airbyte-openmetrics-exporter host=%s port=%s db=%s prefix=%s",
        settings.exporter_host,
        settings.exporter_port,
        settings.safe_db_label(),
        settings.normalized_metrics_prefix,
    )
    server.serve_forever()


if __name__ == "__main__":
    main()
