from __future__ import annotations

import os
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


def ping() -> bool:
    if not is_configured():
        return False
    with connect() as con, con.cursor() as cur:
        cur.execute("SELECT 1;")
        return cur.fetchone() is not None


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


def list_feedbacks(session_id: str) -> list[dict[str, Any]]:
    with connect() as con, con.cursor() as cur:
        cur.execute(
            """
            SELECT id, original_prompt, translated_text, target_language, feedback, created_at
            FROM feedbacks
            WHERE session_id = %s
            ORDER BY created_at DESC, id DESC;
            """,
            (session_id,),
        )
        return list(cur.fetchall())


def clear_feedbacks(session_id: str) -> int:
    with connect() as con, con.cursor() as cur:
        cur.execute("DELETE FROM feedbacks WHERE session_id = %s;", (session_id,))
        return cur.rowcount
