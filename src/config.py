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

    # 周报配置 - 使用云空间文档（非知识库）
    TEMPLATE_DOC_TOKEN = os.getenv("TEMPLATE_DOC_TOKEN", "CzQ2dUoAmoI5GXxsVswcjw2YnGh")
    TARGET_CHAT_ID = os.getenv("TARGET_CHAT_ID")  # 发送周报的群 ID

    # 定时任务配置
    REPORT_DAY = 1  # 周二 (0=周一, 1=周二)
    REPORT_HOUR = 11  # 上午 11 点生成并发送
    MEETING_HOUR = 14  # 会议时间 14:00（周三）

    # 数据库
    DATABASE_PATH = os.getenv("DATABASE_PATH", "data/bot.db")

    # 周报汇总表（飞书多维表格）
    REPORT_BITABLE_APP_TOKEN = os.getenv("REPORT_BITABLE_APP_TOKEN", "ATn8bLW6Lashf3susaScmHXhnzc")
    REPORT_BITABLE_TABLE_ID = os.getenv("REPORT_BITABLE_TABLE_ID", "tblbzqmxCApNrFFS")

    # 文档权限配置（创建文档后自动授予管理者权限）
    DOC_PERMISSION_EMAIL = os.getenv("DOC_PERMISSION_EMAIL", "fuqiannan.fionafu@bytedance.com")
    DOC_PERMISSION_OPEN_ID = os.getenv("DOC_PERMISSION_OPEN_ID", "ou_9e5dddb6debcf86715b2d98eb38e519f")
    DOC_PERMISSION_LEVEL = "full_access"  # full_access = 管理者权限

    # 豆包 LLM (ARK API)
    ARK_API_KEY = os.getenv("ARK_API_KEY", "")
    ARK_MODEL_ENDPOINT = os.getenv("ARK_MODEL_ENDPOINT", "")
    ARK_BASE_URL = os.getenv("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
