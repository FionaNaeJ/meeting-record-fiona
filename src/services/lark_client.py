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

    def add_report_to_bitable(self, app_token: str, table_id: str, report_date: str, title: str, doc_url: str, todo_content: str = "", status: str = "已创建") -> bool:
        """将周报记录添加到多维表格"""
        fields = {
            "周报日期": report_date,
            "标题": title,
            "文档链接": {"link": doc_url, "text": title},
            "状态": status
        }
        if todo_content:
            fields["Todo内容"] = todo_content

        request = CreateAppTableRecordRequest.builder() \
            .app_token(app_token) \
            .table_id(table_id) \
            .request_body(AppTableRecord.builder()
                .fields(fields)
                .build()) \
            .build()
        response = self.client.bitable.v1.app_table_record.create(request)
        if response.success():
            print(f"[LarkClient] Report added to bitable: {title}")
            return True
        print(f"[LarkClient] Failed to add report to bitable: {response.msg}")
        return False

    def copy_document(self, source_doc_token: str, new_title: str, folder_token: str = "") -> Optional[dict]:
        """复制云空间文档，返回 {doc_token, doc_url}

        Args:
            source_doc_token: 源文档的 token
            new_title: 新文档标题
            folder_token: 目标文件夹 token，空表示根目录
        """
        import httpx

        token = self._get_tenant_access_token()
        if not token:
            print("[LarkClient] Failed to get tenant access token")
            return None

        url = f"https://open.feishu.cn/open-apis/drive/v1/files/{source_doc_token}/copy"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        body = {
            "name": new_title,
            "type": "docx",
            "folder_token": folder_token
        }

        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, headers=headers, json=body)
            print(f"[LarkClient] Copy document response: {resp.status_code} {resp.text[:500]}")

            if resp.status_code != 200:
                print(f"[LarkClient] Copy document failed: {resp.text}")
                return None

            data = resp.json()
            if data.get("code") != 0:
                print(f"[LarkClient] Copy document error: {data.get('msg')}")
                return None

            new_token = data["data"]["file"]["token"]
            doc_url = f"https://bytedance.larkoffice.com/docx/{new_token}"

            return {"doc_token": new_token, "doc_url": doc_url}

    def _get_tenant_access_token(self) -> Optional[str]:
        """获取 tenant access token"""
        import httpx
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        body = {
            "app_id": Config.LARK_APP_ID,
            "app_secret": Config.LARK_APP_SECRET
        }
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, json=body)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == 0:
                    return data.get("tenant_access_token")
        return None

    def grant_document_permission(self, doc_token: str, doc_type: str, member_id: str, member_type: str = "openid", perm: str = "full_access") -> bool:
        """给文档添加协作者权限"""
        request = CreatePermissionMemberRequest.builder() \
            .token(doc_token) \
            .type(doc_type) \
            .request_body(Member.builder()
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
