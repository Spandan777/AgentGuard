"""
Persists every agent action to SQLite so we have real trajectory data
for later behavioural analysis and evaluation.
"""
import sqlite3
from datetime import datetime

DB_PATH = "agentguard.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT,
            timestamp TEXT,
            tool TEXT,
            args TEXT,
            risk_score INTEGER,
            risk_level TEXT,
            policy_decision TEXT,
            final_decision TEXT,
            reason TEXT
        )
    """)
    conn.commit()
    conn.close()


def log_action(run_id, tool, args, risk_score, risk_level, policy_decision, final_decision, reason):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO actions (run_id, timestamp, tool, args, risk_score, risk_level, policy_decision, final_decision, reason)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (run_id, datetime.now().isoformat(), tool, str(args), risk_score, risk_level, policy_decision, final_decision, reason))
    conn.commit()
    conn.close()


def get_all_runs():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT DISTINCT run_id FROM actions ORDER BY run_id")
    rows = [r[0] for r in c.fetchall()]
    conn.close()
    return rows


def get_run_actions(run_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT timestamp, tool, args, risk_score, risk_level, policy_decision, final_decision, reason
        FROM actions WHERE run_id = ? ORDER BY id
    """, (run_id,))
    rows = c.fetchall()
    conn.close()
    return rows
