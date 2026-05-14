from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, TypedDict

from prometheus_client import CollectorRegistry, Gauge

from app import queries
from app.config import Settings
from app.db import execute_query, get_connection

logger = logging.getLogger(__name__)

METRICS_LOCK = threading.RLock()


class CollectionPayload(TypedDict):
    connection_status: list[dict[str, Any]]
    running_jobs: float
    job_counts: dict[str, float]
    last_sync_stats: list[dict[str, Any]]


@dataclass
class CollectionState:
    last_success_timestamp: float = 0.0
    last_attempt_timestamp: float = 0.0
    last_error: str | None = None
    exporter_up: bool = False
    cache_expires_at: float = 0.0
    last_duration_seconds: float = 0.0
    initialized: bool = False
    labelsets: dict[str, set[tuple[str, ...]]] = field(default_factory=dict)


class MetricsManager:
    """Owns the Prometheus registry and updates metrics from Airbyte PostgreSQL."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.registry = CollectorRegistry(auto_describe=True)
        self.state = CollectionState()
        self.prefix = settings.normalized_metrics_prefix
        self._collect_lock = threading.Lock()
        self._create_metrics()

    def _metric_name(self, suffix: str) -> str:
        return f"{self.prefix}_{suffix}"

    def _create_metrics(self) -> None:
        self.exporter_up = Gauge(
            self._metric_name("exporter_up"),
            "Whether the exporter can query the Airbyte database. 1 means healthy, 0 means unhealthy.",
            registry=self.registry,
        )
        self.exporter_last_success_timestamp = Gauge(
            self._metric_name("exporter_last_success_timestamp_seconds"),
            "Unix timestamp of the last successful collection cycle.",
            registry=self.registry,
        )
        self.exporter_last_collection_duration = Gauge(
            self._metric_name("exporter_last_collection_duration_seconds"),
            "Duration of the last collection cycle in seconds.",
            registry=self.registry,
        )
        self.running_jobs = Gauge(
            self._metric_name("running_jobs"),
            "Number of Airbyte sync jobs currently running or pending.",
            registry=self.registry,
        )
        self.sync_failed_last_1h = Gauge(
            self._metric_name("sync_failed_last_1h"),
            "Number of failed sync jobs in the last hour.",
            registry=self.registry,
        )
        self.sync_failed_last_24h = Gauge(
            self._metric_name("sync_failed_last_24h"),
            "Number of failed sync jobs in the last 24 hours.",
            registry=self.registry,
        )
        self.sync_succeeded_last_24h = Gauge(
            self._metric_name("sync_succeeded_last_24h"),
            "Number of succeeded sync jobs in the last 24 hours.",
            registry=self.registry,
        )
        self.sync_cancelled_last_24h = Gauge(
            self._metric_name("sync_cancelled_last_24h"),
            "Number of cancelled sync jobs in the last 24 hours.",
            registry=self.registry,
        )

        self.connection_info = Gauge(
            self._metric_name("connection_info"),
            "Airbyte connection metadata. Value is always 1.",
            ["connection_id", "connection_name", "source_name", "destination_name"],
            registry=self.registry,
        )
        self.connection_status = Gauge(
            self._metric_name("connection_status"),
            "Airbyte connection status as a labeled gauge. Value is always 1 for the current status label.",
            ["connection_id", "status"],
            registry=self.registry,
        )
        self.sync_last_duration_seconds = Gauge(
            self._metric_name("sync_last_duration_seconds"),
            "Duration in seconds for the latest known sync attempt per connection.",
            ["connection_id"],
            registry=self.registry,
        )
        self.sync_records_committed = Gauge(
            self._metric_name("sync_records_committed"),
            "Records committed by the latest known sync attempt per connection.",
            ["connection_id"],
            registry=self.registry,
        )
        self.sync_records_emitted = Gauge(
            self._metric_name("sync_records_emitted"),
            "Records emitted by the latest known sync attempt per connection.",
            ["connection_id"],
            registry=self.registry,
        )
        self.sync_bytes_committed = Gauge(
            self._metric_name("sync_bytes_committed"),
            "Bytes committed by the latest known sync attempt per connection.",
            ["connection_id"],
            registry=self.registry,
        )
        self.sync_bytes_emitted = Gauge(
            self._metric_name("sync_bytes_emitted"),
            "Bytes emitted by the latest known sync attempt per connection.",
            ["connection_id"],
            registry=self.registry,
        )

    def _remember_labelset(self, metric_key: str, values: tuple[str, ...]) -> None:
        self.state.labelsets.setdefault(metric_key, set()).add(values)

    def _clear_metric(self, metric_key: str, gauge: Gauge) -> None:
        for labels in self.state.labelsets.get(metric_key, set()):
            try:
                gauge.remove(*labels)
            except KeyError:
                pass
        self.state.labelsets[metric_key] = set()

    @staticmethod
    def _label(value: Any) -> str:
        if value is None:
            return "unknown"

        return str(value)[:200]

    @staticmethod
    def _number(value: Any, default: float = 0.0) -> float:
        try:
            if value is None:
                return default
            return float(value)
        except (TypeError, ValueError):
            return default

    def should_use_cache(self) -> bool:
        return self.settings.scrape_cache_ttl_seconds > 0 and time.time() < self.state.cache_expires_at

    def collect_if_needed(self) -> None:
        if self.should_use_cache():
            return

        blocking = not self.state.initialized
        if not self._collect_lock.acquire(blocking=blocking):
            logger.debug("collection already in progress; serving cached/stale metrics")
            return

        try:
            if self.should_use_cache():
                return
            self._collect_and_apply()
        finally:
            self._collect_lock.release()

    def _collect_and_apply(self) -> None:
        start = time.monotonic()
        self.state.last_attempt_timestamp = time.time()
        try:
            payload = self._collect_payload_from_db()
            duration = time.monotonic() - start
            now = time.time()
            with METRICS_LOCK:
                self._apply_payload_locked(payload)
                self.exporter_up.set(1)
                self.exporter_last_success_timestamp.set(now)
                self.exporter_last_collection_duration.set(duration)
                self.state.last_success_timestamp = now
                self.state.last_duration_seconds = duration
                self.state.last_error = None
                self.state.exporter_up = True
                self.state.initialized = True
                self.state.cache_expires_at = now + self.settings.scrape_cache_ttl_seconds
            logger.debug("collection succeeded duration=%.3fs", duration)
        except Exception as exc:  
            duration = time.monotonic() - start
            with METRICS_LOCK:
                self.exporter_up.set(0)
                self.exporter_last_collection_duration.set(duration)
                self.state.last_duration_seconds = duration
                self.state.last_error = exc.__class__.__name__
                self.state.exporter_up = False
                self.state.initialized = True
                self.state.cache_expires_at = time.time() + min(self.settings.scrape_cache_ttl_seconds, 10)
            logger.warning("collection failed exception=%s duration=%.3fs", exc.__class__.__name__, duration)

    def _collect_payload_from_db(self) -> CollectionPayload:
        with get_connection(self.settings) as conn:
            connection_rows = execute_query(conn, queries.CONNECTION_STATUS)
            running_rows = execute_query(conn, queries.RUNNING_JOBS)
            count_rows = execute_query(conn, queries.JOB_COUNTS_24H)
            stats_rows = execute_query(conn, queries.SYNC_LAST_STATS)

        running_jobs = self._number(running_rows[0].get("running_jobs", 0) if running_rows else 0)
        counts = count_rows[0] if count_rows else {}
        return {
            "connection_status": connection_rows,
            "running_jobs": running_jobs,
            "job_counts": {
                "failed_last_1h": self._number(counts.get("failed_last_1h")),
                "failed_last_24h": self._number(counts.get("failed_last_24h")),
                "succeeded_last_24h": self._number(counts.get("succeeded_last_24h")),
                "cancelled_last_24h": self._number(counts.get("cancelled_last_24h")),
            },
            "last_sync_stats": stats_rows,
        }

    def _apply_payload_locked(self, payload: CollectionPayload) -> None:
        """Apply a fully collected payload. Caller must hold METRICS_LOCK."""
        self._apply_connection_status(payload["connection_status"])
        self.running_jobs.set(payload["running_jobs"])
        counts = payload["job_counts"]
        self.sync_failed_last_1h.set(counts["failed_last_1h"])
        self.sync_failed_last_24h.set(counts["failed_last_24h"])
        self.sync_succeeded_last_24h.set(counts["succeeded_last_24h"])
        self.sync_cancelled_last_24h.set(counts["cancelled_last_24h"])
        self._apply_last_sync_stats(payload["last_sync_stats"])

    def _apply_connection_status(self, rows: list[dict[str, Any]]) -> None:
        self._clear_metric("connection_info", self.connection_info)
        self._clear_metric("connection_status", self.connection_status)
        for row in rows:
            info_labels = (
                self._label(row.get("connection_id")),
                self._label(row.get("connection_name")),
                self._label(row.get("source_name")),
                self._label(row.get("destination_name")),
            )
            status_labels = (
                self._label(row.get("connection_id")),
                self._label(row.get("status")),
            )
            self.connection_info.labels(*info_labels).set(1)
            self.connection_status.labels(*status_labels).set(1)
            self._remember_labelset("connection_info", info_labels)
            self._remember_labelset("connection_status", status_labels)

    def _apply_last_sync_stats(self, rows: list[dict[str, Any]]) -> None:
        metric_map = {
            "sync_last_duration_seconds": self.sync_last_duration_seconds,
            "sync_records_committed": self.sync_records_committed,
            "sync_records_emitted": self.sync_records_emitted,
            "sync_bytes_committed": self.sync_bytes_committed,
            "sync_bytes_emitted": self.sync_bytes_emitted,
        }
        for metric_key, gauge in metric_map.items():
            self._clear_metric(metric_key, gauge)

        for row in rows:
            labels = (self._label(row.get("connection_id")),)
            values = {
                "sync_last_duration_seconds": row.get("duration_seconds"),
                "sync_records_committed": row.get("records_committed"),
                "sync_records_emitted": row.get("records_emitted"),
                "sync_bytes_committed": row.get("bytes_committed"),
                "sync_bytes_emitted": row.get("bytes_emitted"),
            }
            for metric_key, gauge in metric_map.items():
                gauge.labels(*labels).set(self._number(values[metric_key]))
                self._remember_labelset(metric_key, labels)
