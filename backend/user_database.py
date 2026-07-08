"""收藏、最近查看與熱門統計的獨立使用者資料庫。"""

import sqlite3


def get_user_connection(db_path):
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 10000")
    return conn


def create_user_database(db_path):
    conn = get_user_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode = WAL")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS favorites (
        client_id TEXT NOT NULL,
        trace_code TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (
            strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
        ),
        PRIMARY KEY (client_id, trace_code)
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS recent_views (
        client_id TEXT NOT NULL,
        trace_code TEXT NOT NULL,
        viewed_at TEXT NOT NULL DEFAULT (
            strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
        ),
        PRIMARY KEY (client_id, trace_code)
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS product_view_counts (
        trace_code TEXT PRIMARY KEY,
        view_count INTEGER NOT NULL DEFAULT 0,
        last_viewed_at TEXT NOT NULL DEFAULT (
            strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
        )
    )
    """)
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_favorites_client_time "
        "ON favorites(client_id, created_at DESC)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_recent_views_client_time "
        "ON recent_views(client_id, viewed_at DESC)"
    )
    conn.commit()
    conn.close()


def record_product_view(db_path, trace_code, client_id=None):
    conn = get_user_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO product_view_counts(trace_code, view_count)
    VALUES (?, 1)
    ON CONFLICT(trace_code) DO UPDATE SET
        view_count = product_view_counts.view_count + 1,
        last_viewed_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
    """, (trace_code,))
    if client_id:
        cursor.execute("""
        INSERT INTO recent_views(client_id, trace_code)
        VALUES (?, ?)
        ON CONFLICT(client_id, trace_code) DO UPDATE SET
            viewed_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
        """, (client_id, trace_code))
    conn.commit()
    conn.close()


def add_favorite(db_path, client_id, trace_code):
    conn = get_user_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO favorites(client_id, trace_code) VALUES (?, ?)",
        (client_id, trace_code),
    )
    created = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return created


def remove_favorite(db_path, client_id, trace_code):
    conn = get_user_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM favorites WHERE client_id = ? AND trace_code = ?",
        (client_id, trace_code),
    )
    removed = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return removed


def is_favorite(db_path, client_id, trace_code):
    conn = get_user_connection(db_path)
    row = conn.execute(
        "SELECT 1 FROM favorites WHERE client_id = ? AND trace_code = ?",
        (client_id, trace_code),
    ).fetchone()
    conn.close()
    return row is not None
