# src/models/database.py
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import os

@dataclass
class Todo:
    id: Optional[int]
    content: str
    created_by: str
    created_at: datetime
    completed: bool
    completed_at: Optional[datetime] = None
    mentions: Optional[str] = None  # JSON 存储 @ 人信息

@dataclass
class WeeklyReport:
    id: Optional[int]
    week_date: str  # 格式: 2026-01-22
    doc_token: Optional[str]
    status: str  # pending, sent, skipped
    created_at: datetime

class Database:
    def __init__(self, db_path: str):
        os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_tables()

    def _init_tables(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                created_by TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed BOOLEAN DEFAULT FALSE,
                completed_at TIMESTAMP,
                mentions TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS weekly_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                week_date TEXT UNIQUE NOT NULL,
                doc_token TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

    def add_todo(self, content: str, created_by: str, mentions: str = None) -> Todo:
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO todos (content, created_by, mentions) VALUES (?, ?, ?)",
            (content, created_by, mentions)
        )
        self.conn.commit()
        return Todo(
            id=cursor.lastrowid,
            content=content,
            created_by=created_by,
            created_at=datetime.now(),
            completed=False,
            mentions=mentions
        )

    def get_pending_todos(self) -> list[Todo]:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id, content, created_by, created_at, completed, completed_at, mentions FROM todos WHERE completed = FALSE"
        )
        rows = cursor.fetchall()
        return [Todo(id=r[0], content=r[1], created_by=r[2], created_at=r[3], completed=r[4], completed_at=r[5], mentions=r[6]) for r in rows]

    def complete_todo(self, todo_id: int):
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE todos SET completed = TRUE, completed_at = CURRENT_TIMESTAMP WHERE id = ?",
            (todo_id,)
        )
        self.conn.commit()

    def clear_completed_todos(self):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM todos WHERE completed = TRUE")
        self.conn.commit()

    def skip_week(self, week_date: str):
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO weekly_reports (week_date, status) VALUES (?, 'skipped')",
            (week_date,)
        )
        self.conn.commit()

    def cancel_skip(self, week_date: str):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM weekly_reports WHERE week_date = ? AND status = 'skipped'", (week_date,))
        self.conn.commit()

    def is_week_skipped(self, week_date: str) -> bool:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT status FROM weekly_reports WHERE week_date = ?",
            (week_date,)
        )
        row = cursor.fetchone()
        return row is not None and row[0] == "skipped"

    def mark_report_sent(self, week_date: str, doc_token: str):
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO weekly_reports (week_date, doc_token, status) VALUES (?, ?, 'sent')",
            (week_date, doc_token)
        )
        self.conn.commit()

    def get_last_report(self) -> Optional[WeeklyReport]:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id, week_date, doc_token, status, created_at FROM weekly_reports WHERE status = 'sent' ORDER BY week_date DESC LIMIT 1"
        )
        row = cursor.fetchone()
        if row:
            return WeeklyReport(id=row[0], week_date=row[1], doc_token=row[2], status=row[3], created_at=row[4])
        return None
