# src/services/todo_service.py
import re
from typing import Optional
from src.models.database import Database, Todo

class TodoService:
    def __init__(self, db: Database):
        self.db = db

    @staticmethod
    def parse_todo_from_message(message: str) -> Optional[str]:
        """从消息中解析 todo 内容"""
        patterns = [
            r'^[Tt][Oo][Dd][Oo][:\s：]\s*(.+)$',
            r'^[Tt][Oo][Dd][Oo]\s+(.+)$',
            r'^待办[:\s：]\s*(.+)$',
            r'^待办\s+(.+)$',
        ]
        message = message.strip()
        for pattern in patterns:
            match = re.match(pattern, message)
            if match:
                return match.group(1).strip()
        return None

    def add_todo(self, content: str, created_by: str, mentions: list[dict] = None) -> Todo:
        """添加新的待办事项"""
        import json
        mentions_json = json.dumps(mentions) if mentions else None
        return self.db.add_todo(content, created_by, mentions_json)

    def get_pending_todos(self) -> list[Todo]:
        """获取所有未完成的待办事项"""
        return self.db.get_pending_todos()

    def get_todo_texts(self) -> list[str]:
        """获取待办事项的文本列表（用于周报）"""
        todos = self.get_pending_todos()
        return [todo.content for todo in todos]

    def complete_todo(self, todo_id: int):
        """标记待办事项为已完成"""
        self.db.complete_todo(todo_id)

    def mark_todos_as_reported(self):
        """周报发送后，将当前待办标记为已报告"""
        pass
