# src/config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # 飞书应用配置
    LARK_APP_ID = os.getenv("LARK_APP_ID")
    LARK_APP_SECRET = os.getenv("LARK_APP_SECRET")
    LARK_VERIFICATION_TOKEN = os.getenv("LARK_VERIFICATION_TOKEN")
    LARK_ENCRYPT_KEY = os.getenv("LARK_ENCRYPT_KEY", "")

    # 周报配置
    TEMPLATE_WIKI_TOKEN = os.getenv("TEMPLATE_WIKI_TOKEN", "DciwwNkHUiX03pkof4tck789nQd")
    TARGET_CHAT_ID = os.getenv("TARGET_CHAT_ID")  # 发送周报的群 ID
    WIKI_SPACE_ID = os.getenv("WIKI_SPACE_ID", "7559591204279631874")

    # 定时任务配置
    REPORT_DAY = 1  # 周二 (0=周一, 1=周二)
    REPORT_HOUR = 11  # 上午 11 点生成并发送
    MEETING_HOUR = 14  # 会议时间 14:00（周三）

    # 数据库
    DATABASE_PATH = os.getenv("DATABASE_PATH", "data/bot.db")

    # 周报汇总表（飞书多维表格）
    REPORT_BITABLE_APP_TOKEN = os.getenv("REPORT_BITABLE_APP_TOKEN", "")
    REPORT_BITABLE_TABLE_ID = os.getenv("REPORT_BITABLE_TABLE_ID", "")

    # 文档权限配置（创建文档后自动授予管理者权限）
    DOC_PERMISSION_EMAIL = os.getenv("DOC_PERMISSION_EMAIL", "fuqiannan.fionafu@bytedance.com")
    DOC_PERMISSION_OPEN_ID = os.getenv("DOC_PERMISSION_OPEN_ID", "ou_9e5dddb6debcf86715b2d98eb38e519f")
    DOC_PERMISSION_LEVEL = "full_access"  # full_access = 管理者权限
