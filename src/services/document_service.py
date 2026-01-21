# src/services/document_service.py
import re
from datetime import date
from typing import Optional
from src.services.lark_client import LarkClient
from src.config import Config

class DocumentService:
    def __init__(self, lark_client: LarkClient):
        self.lark = lark_client

    @staticmethod
    def generate_new_title(old_title: str, new_date: date) -> str:
        """根据旧标题生成新标题，替换日期部分"""
        pattern = r'\d{4}\.\d{1,2}\.\d{1,2}'
        new_date_str = LarkClient.format_date_for_title(new_date)
        new_title = re.sub(pattern, new_date_str, old_title.strip())
        return new_title

    @staticmethod
    def generate_todo_section(todos: list[str]) -> str:
        """生成新的 Todo 部分内容"""
        if not todos:
            return "Weekly Todo：\n（暂无待办事项）\n"
        todo_lines = "\n".join(todos)
        return f"Weekly Todo：\n{todo_lines}\n"

    def copy_and_update_report(
        self,
        source_wiki_token: str,
        new_date: date,
        new_todos: list[str]
    ) -> Optional[str]:
        """复制上周周报并更新为本周版本，返回新文档的 wiki token"""
        # 1. 获取源文档信息
        node_info = self.lark.get_wiki_node(source_wiki_token)
        if not node_info:
            return None

        # 2. 生成新标题
        new_title = self.generate_new_title(node_info["title"], new_date)

        # 3. 复制文档
        new_token = self.lark.copy_wiki_node(
            space_id=node_info["space_id"],
            node_token=source_wiki_token,
            new_title=new_title
        )

        if not new_token:
            return None

        # 4. 授予文档管理者权限
        self.lark.grant_document_permission(
            doc_token=new_token,
            doc_type="wiki",
            member_id=Config.DOC_PERMISSION_OPEN_ID,
            member_type="openid",
            perm=Config.DOC_PERMISSION_LEVEL
        )

        return new_token

    def get_document_url(self, wiki_token: str, space_id: str = None) -> str:
        """生成文档的访问 URL"""
        return f"https://bytedance.larkoffice.com/wiki/{wiki_token}"
