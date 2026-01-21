# src/services/lark_client.py
import json
import lark_oapi as lark
from lark_oapi.api.wiki.v2 import *
from lark_oapi.api.docx.v1 import *
from lark_oapi.api.im.v1 import *
from lark_oapi.api.drive.v1 import *
from lark_oapi.api.bitable.v1 import *
from datetime import date, timedelta
from typing import Optional, List
from src.config import Config

class LarkClient:
    def __init__(self):
        self.client = lark.Client.builder() \
            .app_id(Config.LARK_APP_ID) \
            .app_secret(Config.LARK_APP_SECRET) \
            .build()

    @staticmethod
    def format_date_for_title(d: date) -> str:
        """格式化日期为标题格式: 2026.1.21"""
        return f"{d.year}.{d.month}.{d.day}"

    @staticmethod
    def get_next_wednesday(from_date: date = None) -> date:
        """获取下一个周三的日期"""
        if from_date is None:
            from_date = date.today()
        days_until_wednesday = (2 - from_date.weekday()) % 7  # 2 = Wednesday
        if days_until_wednesday == 0 and from_date.weekday() == 2:
            return from_date  # 今天就是周三
        if days_until_wednesday == 0:
            days_until_wednesday = 7
        return from_date + timedelta(days=days_until_wednesday)

    def get_wiki_node(self, token: str) -> Optional[dict]:
        """获取 Wiki 节点信息"""
        request = GetNodeSpaceRequest.builder() \
            .token(token) \
            .build()
        response = self.client.wiki.v2.space.get_node(request)
        if response.success():
            return {
                "node_token": response.data.node.node_token,
                "obj_token": response.data.node.obj_token,
                "obj_type": response.data.node.obj_type,
                "title": response.data.node.title,
                "space_id": response.data.node.space_id,
                "parent_node_token": response.data.node.parent_node_token,
            }
        return None

    def get_document_content(self, doc_id: str) -> Optional[str]:
        """获取文档纯文本内容"""
        request = RawContentDocumentRequest.builder() \
            .document_id(doc_id) \
            .build()
        response = self.client.docx.v1.document.raw_content(request)
        if response.success():
            return response.data.content
        return None

    def copy_wiki_node(self, space_id: str, node_token: str, new_title: str) -> Optional[str]:
        """复制 Wiki 节点，返回新节点的 token"""
        request = CopySpaceNodeRequest.builder() \
            .space_id(space_id) \
            .node_token(node_token) \
            .request_body(CopySpaceNodeRequestBody.builder()
                .target_space_id(space_id)
                .title(new_title)
                .build()) \
            .build()
        response = self.client.wiki.v2.space_node.copy(request)
        if response.success():
            return response.data.node.node_token
        print(f"Copy failed: {response.msg}")
        return None

    def update_document_title(self, doc_id: str, new_title: str) -> bool:
        """更新文档标题"""
        return True  # 复制时已经设置了标题

    def send_message_to_chat(self, chat_id: str, content: str, msg_type: str = "text") -> bool:
        """发送消息到群聊"""
        if msg_type == "text":
            content_json = f'{{"text": "{content}"}}'
        else:
            content_json = content

        request = CreateMessageRequest.builder() \
            .receive_id_type("chat_id") \
            .request_body(CreateMessageRequestBody.builder()
                .receive_id(chat_id)
                .msg_type(msg_type)
                .content(content_json)
                .build()) \
            .build()
        response = self.client.im.v1.message.create(request)
        return response.success()

    def add_report_to_bitable(self, app_token: str, table_id: str, report_date: str, title: str, doc_url: str, status: str = "已发送") -> bool:
        """将周报记录添加到多维表格"""
        request = CreateAppTableRecordRequest.builder() \
            .app_token(app_token) \
            .table_id(table_id) \
            .request_body(AppTableRecord.builder()
                .fields({
                    "周报日期": report_date,
                    "标题": title,
                    "文档链接": {"link": doc_url, "text": title},
                    "状态": status
                })
                .build()) \
            .build()
        response = self.client.bitable.v1.app_table_record.create(request)
        if response.success():
            print(f"Report added to bitable: {title}")
            return True
        print(f"Failed to add report to bitable: {response.msg}")
        return False

    def grant_document_permission(self, doc_token: str, doc_type: str, member_id: str, member_type: str = "openid", perm: str = "full_access") -> bool:
        """给文档添加协作者权限"""
        request = CreatePermissionMemberRequest.builder() \
            .token(doc_token) \
            .type(doc_type) \
            .request_body(PermissionMember.builder()
                .member_type(member_type)
                .member_id(member_id)
                .perm(perm)
                .build()) \
            .build()
        response = self.client.drive.v1.permission_member.create(request)
        if response.success():
            print(f"Permission granted: {member_id} -> {perm}")
            return True
        print(f"Permission grant failed: {response.msg}")
        return False

    def send_report_card(self, chat_id: str, title: str, doc_url: str, todos: List[str]) -> bool:
        """发送周报卡片消息"""
        todo_text = "\\n".join([f"• {t}" for t in todos]) if todos else "暂无新增待办"

        card_content = {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": title},
                "template": "blue"
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {"tag": "lark_md", "content": f"**本周待办:**\\n{todo_text}"}
                },
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "查看周报"},
                            "url": doc_url,
                            "type": "primary"
                        }
                    ]
                }
            ]
        }

        return self.send_message_to_chat(chat_id, json.dumps(card_content), "interactive")
