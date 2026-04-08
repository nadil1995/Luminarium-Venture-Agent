"""
SQLite database layer.

Tables:
  processed_submissions  — tracks every submission that has been analyzed
  run_log                — one record per pipeline run
  submission_log         — one record per submission event within a run
"""
import sqlite3
import os
from contextlib import contextmanager
from datetime import datetime
from app.config import config


def _ensure_dirs():
    os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)


@contextmanager
def _conn():
    _ensure_dirs()
    con = sqlite3.connect(config.DB_PATH, check_same_thread=False)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_db():
    with _conn() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS processed_submissions (
            submission_id   TEXT PRIMARY KEY,
            timestamp       TEXT,
            submitter_name  TEXT,
            startup_name    TEXT,
            email           TEXT,
            processed_at    TEXT,
            run_id          TEXT,
            report_path     TEXT,
            s3_url          TEXT
        );

        CREATE TABLE IF NOT EXISTS run_log (
            run_id          TEXT PRIMARY KEY,
            started_at      TEXT,
            finished_at     TEXT,
            trigger         TEXT,       -- 'scheduler' | 'manual' | 'cli'
            status          TEXT,       -- 'running' | 'success' | 'error'
            new_count       INTEGER DEFAULT 0,
            skipped_count   INTEGER DEFAULT 0,
            error_message   TEXT,
            batch_report_path TEXT,
            batch_s3_url    TEXT
        );

        CREATE TABLE IF NOT EXISTS submission_log (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id          TEXT,
            submission_id   TEXT,
            startup_name    TEXT,
            event           TEXT,       -- 'skipped' | 'analyzed' | 'report_generated' | 'error'
            detail          TEXT,
            created_at      TEXT
        );
        """)


# ── processed_submissions ──────────────────────────────────────────────────────

def is_processed(submission_id: str) -> bool:
    with _conn() as con:
        row = con.execute(
            "SELECT 1 FROM processed_submissions WHERE submission_id = ?",
            (submission_id,)
        ).fetchone()
        return row is not None


def mark_processed(
    submission_id: str,
    timestamp: str,
    submitter_name: str,
    startup_name: str,
    email: str,
    run_id: str,
    report_path: str = "",
    s3_url: str = "",
):
    with _conn() as con:
        con.execute("""
            INSERT OR REPLACE INTO processed_submissions
              (submission_id, timestamp, submitter_name, startup_name, email,
               processed_at, run_id, report_path, s3_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            submission_id, timestamp, submitter_name, startup_name, email,
            datetime.utcnow().isoformat(), run_id, report_path, s3_url,
        ))


def get_all_processed(limit: int = 200) -> list[dict]:
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM processed_submissions ORDER BY processed_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


def unmark_processed(submission_id: str):
    """Allow regeneration by removing the processed record."""
    with _conn() as con:
        con.execute(
            "DELETE FROM processed_submissions WHERE submission_id = ?",
            (submission_id,)
        )


# ── run_log ────────────────────────────────────────────────────────────────────

def create_run(run_id: str, trigger: str) -> None:
    with _conn() as con:
        con.execute("""
            INSERT INTO run_log (run_id, started_at, trigger, status)
            VALUES (?, ?, ?, 'running')
        """, (run_id, datetime.utcnow().isoformat(), trigger))


def finish_run(
    run_id: str,
    status: str,
    new_count: int = 0,
    skipped_count: int = 0,
    error_message: str = "",
    batch_report_path: str = "",
    batch_s3_url: str = "",
):
    with _conn() as con:
        con.execute("""
            UPDATE run_log SET
              finished_at = ?, status = ?, new_count = ?,
              skipped_count = ?, error_message = ?,
              batch_report_path = ?, batch_s3_url = ?
            WHERE run_id = ?
        """, (
            datetime.utcnow().isoformat(), status, new_count,
            skipped_count, error_message,
            batch_report_path, batch_s3_url, run_id,
        ))


def get_runs(limit: int = 50) -> list[dict]:
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM run_log ORDER BY started_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_run(run_id: str) -> dict | None:
    with _conn() as con:
        row = con.execute(
            "SELECT * FROM run_log WHERE run_id = ?", (run_id,)
        ).fetchone()
        return dict(row) if row else None


# ── submission_log ─────────────────────────────────────────────────────────────

def log_submission_event(
    run_id: str,
    submission_id: str,
    startup_name: str,
    event: str,
    detail: str = "",
):
    with _conn() as con:
        con.execute("""
            INSERT INTO submission_log
              (run_id, submission_id, startup_name, event, detail, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            run_id, submission_id, startup_name, event, detail,
            datetime.utcnow().isoformat(),
        ))


def get_submission_events(run_id: str | None = None, limit: int = 500) -> list[dict]:
    with _conn() as con:
        if run_id:
            rows = con.execute(
                "SELECT * FROM submission_log WHERE run_id = ? ORDER BY id DESC LIMIT ?",
                (run_id, limit)
            ).fetchall()
        else:
            rows = con.execute(
                "SELECT * FROM submission_log ORDER BY id DESC LIMIT ?",
                (limit,)
            ).fetchall()
        return [dict(r) for r in rows]
