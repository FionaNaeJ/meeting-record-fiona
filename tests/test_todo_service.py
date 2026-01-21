# tests/test_todo_service.py
import pytest
import tempfile
import os
from src.services.todo_service import TodoService
from src.models.database import Database

@pytest.fixture
def todo_service():
    fd, path = tempfile.mkstemp()
    db = Database(path)
    service = TodoService(db)
    yield service
    os.close(fd)
    os.unlink(path)

def test_parse_todo_from_message():
    message = "todo 完成周报机器人开发"
    result = TodoService.parse_todo_from_message(message)
    assert result == "完成周报机器人开发"

def test_parse_todo_with_colon():
    message = "TODO: 和张三沟通需求"
    result = TodoService.parse_todo_from_message(message)
    assert result == "和张三沟通需求"

def test_parse_not_todo():
    message = "这不是一个待办事项"
    result = TodoService.parse_todo_from_message(message)
    assert result is None

def test_add_and_get_todos(todo_service):
    todo_service.add_todo("任务1", "user1")
    todo_service.add_todo("任务2", "user2")
    todos = todo_service.get_pending_todos()
    assert len(todos) == 2
    assert todos[0].content == "任务1"

def test_get_todo_texts(todo_service):
    todo_service.add_todo("任务A", "user1")
    todo_service.add_todo("任务B", "user2")
    texts = todo_service.get_todo_texts()
    assert texts == ["任务A", "任务B"]
