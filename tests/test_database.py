# tests/test_database.py
import pytest
import os
import tempfile
from src.models.database import Database, Todo, WeeklyReport

@pytest.fixture
def db():
    fd, path = tempfile.mkstemp()
    database = Database(path)
    yield database
    os.close(fd)
    os.unlink(path)

def test_add_todo(db):
    todo = db.add_todo("完成周报机器人开发", "ou_user123")
    assert todo.id is not None
    assert todo.content == "完成周报机器人开发"
    assert todo.completed is False

def test_get_pending_todos(db):
    db.add_todo("任务1", "user1")
    db.add_todo("任务2", "user2")
    todos = db.get_pending_todos()
    assert len(todos) == 2

def test_complete_todo(db):
    todo = db.add_todo("测试任务", "user1")
    db.complete_todo(todo.id)
    todos = db.get_pending_todos()
    assert len(todos) == 0

def test_skip_week(db):
    db.skip_week("2026-01-22")
    assert db.is_week_skipped("2026-01-22") is True
    assert db.is_week_skipped("2026-01-29") is False

def test_cancel_skip(db):
    db.skip_week("2026-01-22")
    db.cancel_skip("2026-01-22")
    assert db.is_week_skipped("2026-01-22") is False
