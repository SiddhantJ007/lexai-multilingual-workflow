from __future__ import annotations

import os
from datetime import date
from typing import Any

import psycopg
from psycopg.rows import dict_row


def database_url() -> str | None:
    return os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")


def is_configured() -> bool:
    return bool(database_url())


def require_database_url() -> str:
    url = database_url()
    if not url:
        raise RuntimeError("Feedback storage is not configured. Set DATABASE_URL or SUPABASE_DB_URL.")
    return url


def connect() -> psycopg.Connection:
    return psycopg.connect(require_database_url(), autocommit=True, row_factory=dict_row)


def safe_error_message(exc: Exception) -> str:
    msg = " ".join(str(exc).split())
    msg = msg.replace(require_database_url(), "[redacted]") if is_configured() else msg
    msg = msg[:160]
    return msg or exc.__class__.__name__


def ensure_schema() -> None:
    with connect() as con, con.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS feedbacks (
                id BIGSERIAL PRIMARY KEY,
                session_id TEXT NOT NULL,
                original_prompt TEXT NOT NULL,
                translated_text TEXT NOT NULL,
                target_language TEXT NOT NULL,
                feedback TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_feedbacks_session_created
            ON feedbacks (session_id, created_at DESC);
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS session_usage (
                session_id TEXT NOT NULL,
                day DATE NOT NULL,
                chars_used INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (session_id, day)
            );
            """
        )


def ping() -> bool:
    if not is_configured():
        return False
    with connect() as con, con.cursor() as cur:
        cur.execute("SELECT 1;")
        return cur.fetchone() is not None


def check() -> tuple[bool, str | None]:
    if not is_configured():
        return False, None
    try:
        with connect() as con, con.cursor() as cur:
            cur.execute("SELECT 1;")
            cur.fetchone()
        return True, None
    except Exception as exc:
        return False, safe_error_message(exc)


def insert_feedback(
    session_id: str,
    original_prompt: str,
    translated_text: str,
    target_language: str,
    feedback: str,
) -> None:
    with connect() as con, con.cursor() as cur:
        cur.execute(
            """
            INSERT INTO feedbacks (
                session_id, original_prompt, translated_text, target_language, feedback
            ) VALUES (%s, %s, %s, %s, %s);
            """,
            (session_id, original_prompt, translated_text, target_language, feedback),
        )


def list_feedbacks(
    session_id: str,
    *,
    include_variants: bool = True,
    feedback_prefix: str | None = None,
) -> list[dict[str, Any]]:
    with connect() as con, con.cursor() as cur:
        sql = """
            SELECT id, original_prompt, translated_text, target_language, feedback, created_at
            FROM feedbacks
            WHERE session_id = %s
        """
        params: list[Any] = [session_id]
        if feedback_prefix:
            sql += " AND feedback ILIKE %s"
            params.append(f"{feedback_prefix}%")
        if not include_variants:
            sql += " AND feedback NOT ILIKE %s"
            params.append("%(alt)%")
        sql += " ORDER BY created_at DESC, id DESC;"
        cur.execute(sql, params)
        return list(cur.fetchall())


def clear_feedbacks(session_id: str) -> int:
    with connect() as con, con.cursor() as cur:
        cur.execute("DELETE FROM feedbacks WHERE session_id = %s;", (session_id,))
        return cur.rowcount


def get_session_usage(session_id: str, day: date) -> int:
    with connect() as con, con.cursor() as cur:
        cur.execute(
            """
            SELECT chars_used
            FROM session_usage
            WHERE session_id = %s AND day = %s;
            """,
            (session_id, day),
        )
        row = cur.fetchone()
        if not row:
            return 0
        return int(row["chars_used"])


def increment_session_usage(session_id: str, day: date, chars: int) -> int:
    with connect() as con, con.cursor() as cur:
        cur.execute(
            """
            INSERT INTO session_usage (session_id, day, chars_used)
            VALUES (%s, %s, %s)
            ON CONFLICT (session_id, day)
            DO UPDATE SET chars_used = session_usage.chars_used + EXCLUDED.chars_used
            RETURNING chars_used;
            """,
            (session_id, day, chars),
        )
        row = cur.fetchone()
        return int(row["chars_used"]) if row else chars
