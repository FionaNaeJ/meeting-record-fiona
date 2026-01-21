# src/services/report_service.py
from datetime import date
from typing import Optional
from src.models.database import Database
from src.services.lark_client import LarkClient
from src.services.document_service import DocumentService
from src.services.todo_service import TodoService
from src.config import Config

class ReportService:
    def __init__(
        self,
        db: Database,
        lark_client: LarkClient,
        doc_service: DocumentService,
        todo_service: TodoService
    ):
        self.db = db
        self.lark = lark_client
        self.doc_service = doc_service
        self.todo_service = todo_service

    def should_send_report(self, week_date: date) -> bool:
        """检查是否应该发送本周周报"""
        date_str = week_date.strftime("%Y-%m-%d")
        return not self.db.is_week_skipped(date_str)

    def skip_week(self, week_date: date):
        """跳过某周的周报"""
        date_str = week_date.strftime("%Y-%m-%d")
        self.db.skip_week(date_str)

    def cancel_skip(self, week_date: date):
        """取消跳过某周"""
        date_str = week_date.strftime("%Y-%m-%d")
        self.db.cancel_skip(date_str)

    def get_last_report_token(self) -> Optional[str]:
        """获取上一次发送的周报 token"""
        report = self.db.get_last_report()
        if report:
            return report.doc_token
        return Config.TEMPLATE_WIKI_TOKEN

    def generate_and_send_report(self, target_date: date = None) -> bool:
        """生成并发送周报"""
        if target_date is None:
            target_date = LarkClient.get_next_wednesday()

        # 检查是否跳过
        if not self.should_send_report(target_date):
            print(f"Week {target_date} is skipped")
            return False

        # 获取上周周报
        source_token = self.get_last_report_token()
        if not source_token:
            print("No source report found")
            return False

        # 获取待办事项
        todos = self.todo_service.get_todo_texts()

        # 复制并更新周报
        new_token = self.doc_service.copy_and_update_report(
            source_wiki_token=source_token,
            new_date=target_date,
            new_todos=todos
        )

        if not new_token:
            print("Failed to copy report")
            return False

        # 生成标题和 URL
        title = f"火山引擎PMM&开发者周报{LarkClient.format_date_for_title(target_date)}"
        doc_url = self.doc_service.get_document_url(new_token, Config.WIKI_SPACE_ID)

        # 发送卡片消息
        success = self.lark.send_report_card(
            chat_id=Config.TARGET_CHAT_ID,
            title=title,
            doc_url=doc_url,
            todos=todos
        )

        if success:
            self.db.mark_report_sent(target_date.strftime("%Y-%m-%d"), new_token)
            print(f"Report sent successfully: {doc_url}")

            # 添加到周报汇总表
            if Config.REPORT_BITABLE_APP_TOKEN and Config.REPORT_BITABLE_TABLE_ID:
                self.lark.add_report_to_bitable(
                    app_token=Config.REPORT_BITABLE_APP_TOKEN,
                    table_id=Config.REPORT_BITABLE_TABLE_ID,
                    report_date=target_date.strftime("%Y-%m-%d"),
                    title=title,
                    doc_url=doc_url,
                    status="已发送"
                )

        return success
