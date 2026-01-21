# src/scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from src.services.report_service import ReportService
from src.config import Config


class ReportScheduler:
    def __init__(self, report_service: ReportService):
        self.report_service = report_service
        self.scheduler = BackgroundScheduler()

    def start(self):
        """启动定时任务"""
        # 每周二上午 11 点执行
        trigger = CronTrigger(
            day_of_week=Config.REPORT_DAY,  # 周二
            hour=Config.REPORT_HOUR,
            minute=0,
            timezone="Asia/Shanghai"
        )

        self.scheduler.add_job(
            self._send_weekly_report,
            trigger=trigger,
            id="weekly_report",
            replace_existing=True
        )

        self.scheduler.start()
        print(f"Scheduler started: Weekly report at Tuesday {Config.REPORT_HOUR}:00")

    def stop(self):
        """停止定时任务"""
        self.scheduler.shutdown()

    def _send_weekly_report(self):
        """执行周报发送任务"""
        print("Running scheduled weekly report...")
        try:
            success = self.report_service.generate_and_send_report()
            if success:
                print("Weekly report sent successfully")
            else:
                print("Weekly report was skipped or failed")
        except Exception as e:
            print(f"Error sending weekly report: {e}")

    def trigger_now(self):
        """手动触发一次周报发送（用于测试）"""
        self._send_weekly_report()
