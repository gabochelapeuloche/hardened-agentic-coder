import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path("telemetry.db")


def init_db(db_path: Path) -> sqlite3.Connection:
    """Initialize the telemetry database and return a connection."""
    con = sqlite3.connect(db_path)
    con.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY NOT NULL,
            feature_tag TEXT,
            project_id TEXT,
            task TEXT,
            prompt_tokens INTEGER,
            completion_tokens INTEGER,
            started_at TIMESTAMP,
            ended_at TIMESTAMP
        )
    """)
    con.commit()
    return con


def log_session(
    session_id: str,
    feature_tag: str,
    project_id: str,
    task: str,
    prompt_tokens: int,
    completion_tokens: int,
    started_at: datetime,
    ended_at: datetime,
) -> None:
    """
    Inject session information into telemetry.db
    """

    con = init_db(DB_PATH)
    cur = con.cursor()
    cur.execute(
        "INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            session_id,
            feature_tag,
            project_id,
            task,
            prompt_tokens,
            completion_tokens,
            started_at,
            ended_at,
        ),
    )
    con.commit()
