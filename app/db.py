from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Iterator

import psycopg2
from psycopg2.extras import RealDictCursor

from app.config import Settings

logger = logging.getLogger(__name__)


@contextmanager
def get_connection(settings: Settings) -> Iterator[psycopg2.extensions.connection]:
    """Open a PostgreSQL connection using kwargs to avoid password-bearing DSNs."""
    conn: psycopg2.extensions.connection | None = None
    try:
        conn = psycopg2.connect(**settings.db_connect_kwargs())
        conn.autocommit = False
        timeout_ms = int(settings.query_timeout_seconds * 1000)
        with conn.cursor() as cur:

            cur.execute("SET statement_timeout = %s", (timeout_ms,))
        conn.commit()
    except Exception as exc:  
        if conn is not None:
            try:
                conn.close()
            except Exception:  
                pass
        logger.error(
            "database connection setup failed db=%s exception=%s",
            settings.safe_db_label(),
            exc.__class__.__name__,
        )
        raise

    try:
        yield conn
    finally:
        conn.close()


def execute_query(
    conn: psycopg2.extensions.connection,
    query: str,
    params: tuple[Any, ...] | None = None,
) -> list[dict[str, Any]]:
    """Execute a query and return rows as dictionaries.

    The rollback on any exception keeps the same connection usable for later queries
    in the same collection cycle.
    """
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params or ())
            rows = cur.fetchall()
        conn.commit()
        return [dict(row) for row in rows]
    except Exception as exc:
        conn.rollback()
        logger.warning("query failed exception=%s", exc.__class__.__name__)
        raise
