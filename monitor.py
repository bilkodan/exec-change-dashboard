import os
import time
import requests
import sqlite3

SEC_API_KEY = os.getenv("SEC_API_KEY")

def init_db():
    conn = sqlite3.connect("exec_changes.db")
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS changes (
        id TEXT PRIMARY KEY,
        company TEXT,
        role TEXT,
        incoming TEXT,
        outgoing TEXT,
        incoming_indian REAL,
        incoming_asian REAL,
        outgoing_us REAL,
        filed_at TEXT
    )
    """)
    conn.commit()
    conn.close()

def run_worker():
    while True:
        print("Polling SEC...")

        # placeholder (you plug in your SEC logic here)
        time.sleep(60)

if __name__ == "__main__":
    init_db()
    run_worker()
