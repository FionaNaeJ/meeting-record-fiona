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

    def get_source_doc_token(self) -> Optional[str]:
        """获取源文档 token（最后一份周报或模板）"""
        last_report = self.db.get_last_report()
        if last_report and last_report.doc_token:
            return last_report.doc_token
        # 没有历史周报，使用模板
        return Config.TEMPLATE_DOC_TOKEN

    def get_or_create_weekly_report(self, target_date: date) -> Optional[dict]:
        """获取或创建本周周报

        Args:
            target_date: 目标日期（下周三）

        Returns:
            成功返回 {"doc_token": str, "doc_url": str}，失败返回 None
        """
        date_str = target_date.strftime("%Y-%m-%d")

        # 检查是否跳过
        if not self.should_send_report(target_date):
            print(f"[ReportService] Week {date_str} is skipped")
            return None

        # 获取待办事项
        todos = self.todo_service.get_todo_texts()

        # 检查是否已有本周周报
        existing = self.db.get_report_by_week_date(date_str)
        if existing and existing.doc_token and existing.doc_url:
            print(f"[ReportService] Found existing report for {date_str}: {existing.doc_url}")
            return {"doc_token": existing.doc_token, "doc_url": existing.doc_url}

        # 创建新周报
        source_token = self.get_source_doc_token()
        if not source_token:
            print("[ReportService] No source document found")
            return None

        result = self.doc_service.copy_and_create_report(source_token, target_date)
        if not result:
            print("[ReportService] Failed to create report")
            return None

        # 保存到数据库（标记为已创建）
        self.db.mark_report_created(date_str, result["doc_token"], result["doc_url"])
        print(f"[ReportService] Created new report: {result['doc_url']}")

        # 写入多维表格
        if Config.REPORT_BITABLE_APP_TOKEN and Config.REPORT_BITABLE_TABLE_ID:
            title = self.doc_service.generate_new_title(target_date)
            todo_content = "\n".join(todos) if todos else ""

            self.lark.add_report_to_bitable(
                app_token=Config.REPORT_BITABLE_APP_TOKEN,
                table_id=Config.REPORT_BITABLE_TABLE_ID,
                report_date=date_str,
                title=title,
                doc_url=result["doc_url"],
                todo_content=todo_content,
                status="已创建"
            )

        return result

    def send_report_card(self, target_date: date) -> bool:
        """发送周报卡片消息（用于周二定时任务）

        Args:
            target_date: 目标日期（应该是明天，即周三）

        Returns:
            是否发送成功
        """
        date_str = target_date.strftime("%Y-%m-%d")

        # 检查是否跳过
        if not self.should_send_report(target_date):
            print(f"[ReportService] Week {date_str} is skipped, not sending card")
            return False

        # 获取本周周报
        report = self.db.get_report_by_week_date(date_str)
        if not report or not report.doc_url:
            print(f"[ReportService] No report found for {date_str}, not sending card")
            return False

        # 生成标题
        title = self.doc_service.generate_new_title(target_date)

        # 发送卡片
        success = self.lark.send_report_card(
            chat_id=Config.TARGET_CHAT_ID,
            title=title,
            doc_url=report.doc_url
        )

        if success:
            print(f"[ReportService] Report card sent for {date_str}")

            # 标记为已发送
            self.db.mark_report_sent(date_str)

            # 更新周报汇总表状态
            if Config.REPORT_BITABLE_APP_TOKEN and Config.REPORT_BITABLE_TABLE_ID:
                self.lark.add_report_to_bitable(
                    app_token=Config.REPORT_BITABLE_APP_TOKEN,
                    table_id=Config.REPORT_BITABLE_TABLE_ID,
                    report_date=date_str,
                    title=title,
                    doc_url=report.doc_url,
                    status="已发送"
                )

        return success
