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
        """执行周报发送任务（周二 11:00 执行）"""
        from datetime import date, timedelta

        print("[Scheduler] Running scheduled weekly report...")

        try:
            # 计算明天（周三）的日期
            tomorrow = date.today() + timedelta(days=1)

            print(f"[Scheduler] Tomorrow is {tomorrow}")

            # 1. 先确保周报已创建
            result = self.report_service.get_or_create_weekly_report(tomorrow)
            if not result:
                print("[Scheduler] Report creation skipped or failed")
                return

            print(f"[Scheduler] Report ready: {result['doc_url']}")

            # 2. 发送卡片到群
            success = self.report_service.send_report_card(tomorrow)
            if success:
                print("[Scheduler] Weekly report card sent successfully")
            else:
                print("[Scheduler] Weekly report card send failed")

        except Exception as e:
            print(f"[Scheduler] Error sending weekly report: {e}")
            import traceback
            traceback.print_exc()

    def trigger_now(self):
        """手动触发一次周报发送（用于测试）"""
        self._send_weekly_report()
