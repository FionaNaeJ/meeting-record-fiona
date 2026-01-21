# tests/test_integration.py
import pytest
import tempfile
import os
from unittest.mock import Mock, patch
from src.models.database import Database
from src.services.todo_service import TodoService
from src.services.report_service import ReportService
from src.handlers.event_handler import EventHandler

@pytest.fixture
def services():
    fd, path = tempfile.mkstemp()
    db = Database(path)

    lark_client = Mock()
    todo_service = TodoService(db)
    doc_service = Mock()
    report_service = ReportService(db, lark_client, doc_service, todo_service)
    event_handler = EventHandler(report_service, todo_service, lark_client)

    yield {
        "db": db,
        "todo_service": todo_service,
        "report_service": report_service,
        "event_handler": event_handler,
    }

    os.close(fd)
    os.unlink(path)

def test_full_todo_workflow(services):
    handler = services["event_handler"]

    # 添加待办
    reply = handler.handle_message("chat1", "user1", "todo 完成设计文档")
    assert "已接收 todo" in reply

    # 再添加一个
    reply = handler.handle_message("chat1", "user2", "TODO: 代码评审")
    assert "已接收 todo" in reply

    # 检查待办数量
    todos = services["todo_service"].get_pending_todos()
    assert len(todos) == 2

def test_skip_workflow(services):
    handler = services["event_handler"]

    # 跳过本周
    reply = handler.handle_message("chat1", "user1", "跳过本周")
    assert "已跳过" in reply

    # 检查状态
    reply = handler.handle_message("chat1", "user1", "状态")
    assert "已跳过" in reply

    # 取消跳过
    reply = handler.handle_message("chat1", "user1", "取消跳过")
    assert "已恢复" in reply

def test_help_command(services):
    handler = services["event_handler"]
    reply = handler.handle_message("chat1", "user1", "帮助")
    assert "todo" in reply
    assert "跳过" in reply
    assert "状态" in reply

def test_unknown_command_returns_empty(services):
    handler = services["event_handler"]
    reply = handler.handle_message("chat1", "user1", "你好啊")
    assert reply == ""
