# tests/test_document_service.py
import pytest
from datetime import date
from src.services.document_service import DocumentService

def test_generate_new_title():
    old_title = "火山引擎PMM&开发者周报2026.1.14"
    new_date = date(2026, 1, 22)
    result = DocumentService.generate_new_title(old_title, new_date)
    assert result == "火山引擎PMM&开发者周报2026.1.22"

def test_generate_new_title_with_space():
    old_title = "火山引擎PMM&开发者周报2026.1.21 "
    new_date = date(2026, 1, 28)
    result = DocumentService.generate_new_title(old_title, new_date)
    assert result == "火山引擎PMM&开发者周报2026.1.28"

def test_generate_todo_section():
    new_todos = ["新任务A @王五", "新任务B @赵六"]
    result = DocumentService.generate_todo_section(new_todos)
    assert "新任务A @王五" in result
    assert "新任务B @赵六" in result

def test_generate_todo_section_empty():
    result = DocumentService.generate_todo_section([])
    assert "暂无待办事项" in result
