import sqlite3
import pandas as pd
from datetime import datetime
from config import DB_PATH


def _connect() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_db() -> None:
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS wait_times (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                attraction_id   TEXT    NOT NULL,
                attraction_name TEXT    NOT NULL,
                wait_minutes    INTEGER,
                status          TEXT    NOT NULL,
                fetched_at      DATETIME NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_fetched_at    ON wait_times(fetched_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_attraction_id ON wait_times(attraction_id)")


def insert_batch(records: list[dict]) -> None:
    with _connect() as conn:
        conn.executemany(
            """
            INSERT INTO wait_times (attraction_id, attraction_name, wait_minutes, status, fetched_at)
            VALUES (:attraction_id, :attraction_name, :wait_minutes, :status, :fetched_at)
            """,
            records,
        )


def query_latest() -> pd.DataFrame:
    with _connect() as conn:
        return pd.read_sql(
            """
            SELECT w.*
            FROM wait_times w
            INNER JOIN (
                SELECT attraction_id, MAX(fetched_at) AS max_ts
                FROM wait_times
                GROUP BY attraction_id
            ) m ON w.attraction_id = m.attraction_id AND w.fetched_at = m.max_ts
            ORDER BY w.wait_minutes DESC NULLS LAST
            """,
            conn,
            parse_dates=["fetched_at"],
        )


def query_history(attraction_id: str, start: datetime, end: datetime) -> pd.DataFrame:
    with _connect() as conn:
        return pd.read_sql(
            """
            SELECT fetched_at, wait_minutes, status
            FROM wait_times
            WHERE attraction_id = ?
              AND fetched_at BETWEEN ? AND ?
            ORDER BY fetched_at
            """,
            conn,
            params=[attraction_id, start.isoformat(), end.isoformat()],
            parse_dates=["fetched_at"],
        )


def query_all_history(start: datetime, end: datetime) -> pd.DataFrame:
    with _connect() as conn:
        return pd.read_sql(
            """
            SELECT fetched_at, attraction_name, wait_minutes, status
            FROM wait_times
            WHERE fetched_at BETWEEN ? AND ?
            ORDER BY fetched_at
            """,
            conn,
            params=[start.isoformat(), end.isoformat()],
            parse_dates=["fetched_at"],
        )


def query_attraction_list() -> pd.DataFrame:
    with _connect() as conn:
        return pd.read_sql(
            """
            SELECT DISTINCT attraction_id, attraction_name
            FROM wait_times
            ORDER BY attraction_name
            """,
            conn,
        )
