# tests/test_command_handler.py
import pytest
from src.handlers.command_handler import CommandHandler

def test_parse_skip_command():
    result = CommandHandler.parse_command("跳过本周")
    assert result == ("skip", None)

def test_parse_skip_with_date():
    result = CommandHandler.parse_command("跳过 2026-01-29")
    assert result == ("skip", "2026-01-29")

def test_parse_cancel_skip():
    result = CommandHandler.parse_command("取消跳过")
    assert result == ("cancel_skip", None)

def test_parse_status():
    result = CommandHandler.parse_command("状态")
    assert result == ("status", None)

def test_parse_todo():
    result = CommandHandler.parse_command("todo 完成开发")
    assert result == ("todo", "完成开发")

def test_parse_unknown():
    result = CommandHandler.parse_command("随便说点什么")
    assert result == (None, None)
