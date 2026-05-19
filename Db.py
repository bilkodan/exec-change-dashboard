import sqlite3

DB_NAME = "exec_changes.db"


def get_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)


def init_db():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS changes (
        id TEXT PRIMARY KEY,

        company TEXT,
        ticker TEXT,

        role TEXT,  -- CEO or CTO

        outgoing TEXT,
        incoming TEXT,

        filed_at TEXT,

        -- classification scores (0–1)
        outgoing_us REAL,
        incoming_indian REAL,
        incoming_asian REAL,

        -- market data
        price REAL,
        price_change_1d REAL,

        -- signal output
        signal_score REAL,
        trade_signal TEXT,
        position_size REAL
    )
    """)

    conn.commit()
    conn.close()


def insert_change(row):
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
    INSERT OR IGNORE INTO changes VALUES (
        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
    )
    """, (
        row.get("id"),
        row.get("company"),
        row.get("ticker"),
        row.get("role"),
        row.get("outgoing"),
        row.get("incoming"),
        row.get("filed_at"),

        row.get("outgoing_us", 0),
        row.get("incoming_indian", 0),
        row.get("incoming_asian", 0),

        row.get("price", 0),
        row.get("price_change_1d", 0),

        row.get("signal_score", 0),
        row.get("trade_signal", "NONE"),
        row.get("position_size", 0)
    ))

    conn.commit()
    conn.close()


def fetch_all():
    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT * FROM changes ORDER BY filed_at DESC")
    rows = c.fetchall()

    conn.close()
    return rows


def init_trump_alerts():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS trump_alerts (
        id TEXT PRIMARY KEY,
        text TEXT,
        post_url TEXT,
        published TEXT,
        companies TEXT,
        alerted_at TEXT
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS trump_seen (
        id TEXT PRIMARY KEY
    )
    """)
    conn.commit()
    conn.close()


def trump_post_seen(post_id: str) -> bool:
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "SELECT 1 FROM trump_alerts WHERE id = ? UNION SELECT 1 FROM trump_seen WHERE id = ?",
        (post_id, post_id),
    )
    result = c.fetchone()
    conn.close()
    return result is not None


def insert_trump_alert(row: dict):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT OR IGNORE INTO trump_alerts VALUES (?, ?, ?, ?, ?, ?)",
        (
            row.get("id"),
            row.get("text"),
            row.get("post_url"),
            row.get("published"),
            row.get("companies"),
            row.get("alerted_at"),
        ),
    )
    conn.commit()
    conn.close()


def mark_trump_seen(post_id: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO trump_seen VALUES (?)", (post_id,))
    conn.commit()
    conn.close()


def fetch_trump_alerts():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM trump_alerts ORDER BY published DESC")
    rows = c.fetchall()
    conn.close()
    return rows
