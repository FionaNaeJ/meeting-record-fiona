# src/handlers/event_handler.py
from datetime import date
from src.handlers.command_handler import CommandHandler
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

    def handle_message(self, chat_id: str, user_id: str, message: str, mentions: list[dict] = None) -> str:
        """处理群消息，返回回复内容"""
        command, arg = CommandHandler.parse_command(message)

        if command == "skip":
            return self._handle_skip(arg)
        elif command == "cancel_skip":
            return self._handle_cancel_skip(arg)
        elif command == "status":
            return self._handle_status()
        elif command == "todo":
            return self._handle_todo(arg, user_id, mentions)
        elif command == "help":
            return self._handle_help()
        else:
            return ""  # 不回复无关消息

    def _handle_skip(self, date_str: str = None) -> str:
        if date_str:
            from datetime import datetime
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        else:
            target_date = LarkClient.get_next_wednesday()

        self.report_service.skip_week(target_date)
        return f"已跳过 {target_date.strftime('%Y-%m-%d')} 的周报"

    def _handle_cancel_skip(self, date_str: str = None) -> str:
        if date_str:
            from datetime import datetime
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        else:
            target_date = LarkClient.get_next_wednesday()

        self.report_service.cancel_skip(target_date)
        return f"已恢复 {target_date.strftime('%Y-%m-%d')} 的周报"

    def _handle_status(self) -> str:
        next_wed = LarkClient.get_next_wednesday()
        is_skipped = not self.report_service.should_send_report(next_wed)
        todos = self.todo_service.get_pending_todos()

        status = "已跳过" if is_skipped else "待发送"
        todo_count = len(todos)

        return f"下次周报: {next_wed.strftime('%Y-%m-%d')} ({status})\n待办事项: {todo_count} 项"

    def _handle_todo(self, content: str, user_id: str, mentions: list[dict] = None) -> str:
        self.todo_service.add_todo(content, user_id, mentions)
        return "已接收 todo，将更新至下周周报中"

    def _handle_help(self) -> str:
        return """周报机器人使用帮助:
• todo <内容> - 添加待办事项
• 跳过本周 - 跳过本周周报
• 跳过 2026-01-29 - 跳过指定日期周报
• 取消跳过 - 恢复本周周报
• 状态 - 查看当前状态
• 帮助 - 显示此帮助"""
