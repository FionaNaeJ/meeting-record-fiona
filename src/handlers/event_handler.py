# src/handlers/event_handler.py
from __future__ import annotations
import threading
from src.services.intent_service import IntentService
from src.services.report_service import ReportService
from src.services.todo_service import TodoService
from src.services.lark_client import LarkClient


class EventHandler:
    def __init__(
        self,
        report_service: ReportService,
        todo_service: TodoService,
        lark_client: LarkClient
    ):
        self.report_service = report_service
        self.todo_service = todo_service
        self.lark = lark_client
        self.intent_service = IntentService()

    def handle_message(self, chat_id: str, user_id: str, message: str, mentions: list[dict] = None) -> str:
        """处理群消息，返回回复内容"""
        # 使用 LLM 识别意图
        intent = self.intent_service.recognize(message)
        print(f"[EventHandler] Intent: {intent.type}")

        if intent.type == "todo":
            # 优先使用 LLM 提取的内容，否则用原始消息
            todo_content = intent.content if intent.content else message
            return self._handle_todo(chat_id, todo_content, user_id, mentions)
        elif intent.type == "send_report":
            return self._handle_send_report()
        elif intent.type == "skip":
            return self._handle_skip()
        elif intent.type == "cancel_skip":
            return self._handle_cancel_skip()
        else:
            # unknown 意图不回复
            return ""

    def _handle_todo(self, chat_id: str, content: str, user_id: str, mentions: list[dict] = None) -> str:
        """处理 todo 意图：保存 todo 并异步同步到周报"""
        if not content:
            return ""

        # 1. 保存 todo
        self.todo_service.add_todo(content, user_id, mentions)

        # 2. 异步创建/更新周报（不发送第二条消息）
        thread = threading.Thread(
            target=self._async_update_report,
            args=(chat_id,),
            daemon=True
        )
        thread.start()

        # 3. 发送卡片确认（直接发送，不通过返回值）
        from src.config import Config
        bitable_url = f"https://bytedance.larkoffice.com/base/{Config.REPORT_BITABLE_APP_TOKEN}?table={Config.REPORT_BITABLE_TABLE_ID}"
        self.lark.send_todo_confirm_card(chat_id, bitable_url)

        return ""  # 返回空，不再发送文本消息

    def _async_update_report(self, chat_id: str):
        """异步更新周报（静默，不发送消息）"""
        try:
            target_date = LarkClient.get_next_wednesday()
            result = self.report_service.get_or_create_weekly_report(target_date)

            if result:
                print(f"[EventHandler] Report updated: {result['doc_url']}")
            else:
                print("[EventHandler] Report update failed")

        except Exception as e:
            print(f"[EventHandler] Error in async update: {e}")
            import traceback
            traceback.print_exc()

    def _handle_send_report(self) -> str:
        """处理发送周报意图"""
        last_report = self.report_service.db.get_last_report()
        if last_report and last_report.doc_url:
            return f"周报链接：{last_report.doc_url}"
        else:
            return "暂无周报记录"

    def _handle_skip(self) -> str:
        """处理跳过周报意图"""
        target_date = LarkClient.get_next_wednesday()
        self.report_service.skip_week(target_date)
        return f"已跳过 {target_date.strftime('%Y-%m-%d')} 的周报"

    def _handle_cancel_skip(self) -> str:
        """处理取消跳过意图"""
        target_date = LarkClient.get_next_wednesday()
        self.report_service.cancel_skip(target_date)
        return f"已恢复 {target_date.strftime('%Y-%m-%d')} 的周报"
