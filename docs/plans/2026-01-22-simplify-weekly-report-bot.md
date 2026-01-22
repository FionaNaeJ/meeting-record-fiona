# 简化周报机器人 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 大幅简化周报机器人，移除 LLM 和 Todo 功能，只保留：定时创建周报、跳过/取消跳过、查看周报链接。

**Architecture:**
- 删除 LLM 意图识别（IntentService）
- 删除 Todo 服务（TodoService）
- 删除文档编辑功能（delete_completed_todos, add_todos_to_document）
- 简化消息处理为关键词匹配
- 保留定时任务和文档复制功能
- 给群授权而非单个用户

**Tech Stack:** Python, Feishu Open API, httpx, APScheduler

---

## 简化后的功能

| 功能 | 触发方式 | 实现方式 |
|------|----------|----------|
| 创建周报 | 定时任务（周一 11:00） | 复制文档 → 改标题日期 → 授权给群 |
| 发送提醒 | 定时任务（周二 11:00） | 发卡片到群里提醒大家写周报 |
| 跳过本周 | @机器人 "跳过" | 关键词匹配 |
| 取消跳过 | @机器人 "取消跳过/恢复" | 关键词匹配 |
| 查看周报 | @机器人 "周报/链接" | 关键词匹配 |

---

## 要删除的文件/代码

| 文件 | 删除内容 |
|------|----------|
| `src/services/intent_service.py` | 整个文件删除 |
| `src/services/todo_service.py` | 整个文件删除 |
| `src/services/lark_client.py` | `delete_completed_todos()`, `add_todos_to_document()` |
| `src/services/document_service.py` | todos 参数及相关调用 |
| `src/services/report_service.py` | todo 相关逻辑 |
| `src/handlers/event_handler.py` | 重写为关键词匹配 |
| `src/models/database.py` | todos 表（可选保留 weekly_reports 表） |

---

### Task 1: 删除 IntentService

**Files:**
- Delete: `src/services/intent_service.py`

**Step 1: 删除文件**

```bash
rm src/services/intent_service.py
```

**Step 2: Commit**

```bash
git add -A
git commit -m "refactor: remove IntentService (LLM intent recognition)"
```

---

### Task 2: 删除 TodoService

**Files:**
- Delete: `src/services/todo_service.py`

**Step 1: 删除文件**

```bash
rm src/services/todo_service.py
```

**Step 2: Commit**

```bash
git add -A
git commit -m "refactor: remove TodoService"
```

---

### Task 3: 简化 lark_client.py

**Files:**
- Modify: `src/services/lark_client.py`

**Step 1: 删除 delete_completed_todos 方法**

删除整个 `delete_completed_todos` 方法（约 65 行）。

**Step 2: 删除 add_todos_to_document 方法**

删除整个 `add_todos_to_document` 方法（约 100 行）。

**Step 3: 修改 send_report_card 方法**

将 `send_report_card` 方法简化，移除 todos 参数：

```python
def send_report_card(self, chat_id: str, title: str, doc_url: str) -> bool:
    """发送周报卡片消息"""
    card_content = {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": title},
            "template": "blue"
        },
        "elements": [
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": "新一期周报已创建，请及时填写本周工作内容。"}
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
```

**Step 4: 添加给群授权的方法**

修改 `grant_document_permission` 支持给群授权：

```python
def grant_document_permission_to_chat(self, doc_token: str, doc_type: str, chat_id: str, perm: str = "full_access") -> bool:
    """给群聊授予文档权限"""
    request = CreatePermissionMemberRequest.builder() \
        .token(doc_token) \
        .type(doc_type) \
        .request_body(Member.builder()
            .member_type("openchat")
            .member_id(chat_id)
            .perm(perm)
            .build()) \
        .build()
    response = self.client.drive.v1.permission_member.create(request)
    if response.success():
        print(f"[LarkClient] Permission granted to chat: {chat_id} -> {perm}")
        return True
    print(f"[LarkClient] Permission grant to chat failed: {response.msg}")
    return False
```

**Step 5: Commit**

```bash
git add src/services/lark_client.py
git commit -m "refactor: simplify lark_client, remove todo editing, add chat permission"
```

---

### Task 4: 简化 document_service.py

**Files:**
- Modify: `src/services/document_service.py`

**Step 1: 重写文件**

```python
# src/services/document_service.py
from __future__ import annotations
from datetime import date
from typing import Optional
from src.services.lark_client import LarkClient
from src.config import Config


class DocumentService:
    def __init__(self, lark_client: LarkClient):
        self.lark = lark_client

    @staticmethod
    def format_date_for_title(d: date) -> str:
        """格式化日期为标题格式: 2026.1.29"""
        return f"{d.year}.{d.month}.{d.day}"

    @staticmethod
    def generate_new_title(target_date: date) -> str:
        """生成新周报标题"""
        date_str = DocumentService.format_date_for_title(target_date)
        return f"火山引擎PMM&开发者周报{date_str}"

    def copy_and_create_report(
        self,
        source_doc_token: str,
        target_date: date
    ) -> Optional[dict]:
        """复制源文档创建新周报

        Args:
            source_doc_token: 源文档 token（最后一份周报或模板）
            target_date: 目标日期（下周三）

        Returns:
            成功返回 {"doc_token": str, "doc_url": str}，失败返回 None
        """
        new_title = self.generate_new_title(target_date)

        result = self.lark.copy_document(source_doc_token, new_title)
        if not result:
            print(f"[DocumentService] Failed to copy document from {source_doc_token}")
            return None

        doc_token = result["doc_token"]
        doc_url = result["doc_url"]
        print(f"[DocumentService] Created new report: {doc_url}")

        # 授予群聊编辑权限
        self.lark.grant_document_permission_to_chat(
            doc_token=doc_token,
            doc_type="docx",
            chat_id=Config.TARGET_CHAT_ID,
            perm="full_access"
        )

        # 也给 Fiona 单独授权（备份）
        if Config.DOC_PERMISSION_OPEN_ID:
            self.lark.grant_document_permission(
                doc_token=doc_token,
                doc_type="docx",
                member_id=Config.DOC_PERMISSION_OPEN_ID,
                member_type="openid",
                perm=Config.DOC_PERMISSION_LEVEL
            )

        return {"doc_token": doc_token, "doc_url": doc_url}

    def get_document_url(self, doc_token: str) -> str:
        """生成文档的访问 URL"""
        return f"https://bytedance.larkoffice.com/docx/{doc_token}"
```

**Step 2: Commit**

```bash
git add src/services/document_service.py
git commit -m "refactor: simplify document_service, add chat permission"
```

---

### Task 5: 简化 report_service.py

**Files:**
- Modify: `src/services/report_service.py`

**Step 1: 重写文件**

```python
# src/services/report_service.py
from datetime import date
from typing import Optional
from src.models.database import Database
from src.services.lark_client import LarkClient
from src.services.document_service import DocumentService
from src.config import Config


class ReportService:
    def __init__(
        self,
        db: Database,
        lark_client: LarkClient,
        doc_service: DocumentService
    ):
        self.db = db
        self.lark = lark_client
        self.doc_service = doc_service

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
        return Config.TEMPLATE_DOC_TOKEN

    def get_latest_report_url(self) -> Optional[str]:
        """获取最新周报的 URL"""
        last_report = self.db.get_last_report()
        if last_report and last_report.doc_url:
            return last_report.doc_url
        return None

    def create_weekly_report(self, target_date: date) -> Optional[dict]:
        """创建本周周报

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

        # 检查是否已有本周周报
        existing = self.db.get_report_by_week_date(date_str)
        if existing and existing.doc_token and existing.doc_url:
            print(f"[ReportService] Report already exists for {date_str}: {existing.doc_url}")
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

        # 保存到数据库
        self.db.mark_report_sent(date_str, result["doc_token"], result["doc_url"])
        print(f"[ReportService] Created new report: {result['doc_url']}")

        # 写入多维表格
        if Config.REPORT_BITABLE_APP_TOKEN and Config.REPORT_BITABLE_TABLE_ID:
            title = self.doc_service.generate_new_title(target_date)
            self.lark.add_report_to_bitable(
                app_token=Config.REPORT_BITABLE_APP_TOKEN,
                table_id=Config.REPORT_BITABLE_TABLE_ID,
                report_date=date_str,
                title=title,
                doc_url=result["doc_url"],
                status="已创建"
            )

        return result

    def send_report_card(self, target_date: date) -> bool:
        """发送周报卡片消息

        Args:
            target_date: 目标日期（周三）

        Returns:
            是否发送成功
        """
        date_str = target_date.strftime("%Y-%m-%d")

        # 检查是否跳过
        if not self.should_send_report(target_date):
            print(f"[ReportService] Week {date_str} is skipped, not sending card")
            return False

        # 先创建周报（如果还没创建）
        report = self.create_weekly_report(target_date)
        if not report:
            print(f"[ReportService] Failed to get/create report for {date_str}")
            return False

        # 生成标题
        title = self.doc_service.generate_new_title(target_date)

        # 发送卡片
        success = self.lark.send_report_card(
            chat_id=Config.TARGET_CHAT_ID,
            title=title,
            doc_url=report["doc_url"]
        )

        if success:
            print(f"[ReportService] Report card sent for {date_str}")

        return success
```

**Step 2: Commit**

```bash
git add src/services/report_service.py
git commit -m "refactor: simplify report_service, remove todo logic"
```

---

### Task 6: 重写 event_handler.py（关键词匹配）

**Files:**
- Modify: `src/handlers/event_handler.py`

**Step 1: 重写文件**

```python
# src/handlers/event_handler.py
from datetime import date, timedelta
from src.services.report_service import ReportService
from src.services.lark_client import LarkClient


class EventHandler:
    def __init__(self, report_service: ReportService, lark_client: LarkClient):
        self.report_service = report_service
        self.lark = lark_client

    def handle_message(self, chat_id: str, user_id: str, message: str) -> str:
        """处理消息，使用关键词匹配"""
        message_lower = message.lower().strip()

        # 跳过本周
        if "跳过" in message and "取消" not in message:
            return self._handle_skip()

        # 取消跳过
        if "取消跳过" in message or "恢复" in message:
            return self._handle_cancel_skip()

        # 查看周报
        if "周报" in message or "链接" in message:
            return self._handle_get_report()

        # 帮助
        if "帮助" in message or "help" in message_lower:
            return self._handle_help()

        # 未识别的消息
        return "我可以帮你：\n• 查看周报 - 获取最新周报链接\n• 跳过本周 - 跳过本周周报\n• 取消跳过 - 恢复本周周报"

    def _handle_skip(self) -> str:
        """跳过本周周报"""
        next_wednesday = self._get_next_wednesday()
        self.report_service.skip_week(next_wednesday)
        date_str = next_wednesday.strftime("%Y-%m-%d")
        return f"已跳过 {date_str} 的周报"

    def _handle_cancel_skip(self) -> str:
        """取消跳过"""
        next_wednesday = self._get_next_wednesday()
        self.report_service.cancel_skip(next_wednesday)
        date_str = next_wednesday.strftime("%Y-%m-%d")
        return f"已恢复 {date_str} 的周报"

    def _handle_get_report(self) -> str:
        """获取最新周报链接"""
        url = self.report_service.get_latest_report_url()
        if url:
            return f"最新周报：{url}"
        return "暂无周报记录"

    def _handle_help(self) -> str:
        """帮助信息"""
        return "周报助手功能：\n• 每周二 11:00 自动创建新周报并提醒\n• @我 说「周报」查看最新周报链接\n• @我 说「跳过」跳过本周\n• @我 说「取消跳过」恢复本周"

    @staticmethod
    def _get_next_wednesday() -> date:
        """获取下一个周三"""
        today = date.today()
        days_until_wednesday = (2 - today.weekday()) % 7
        if days_until_wednesday == 0:
            days_until_wednesday = 7
        return today + timedelta(days=days_until_wednesday)
```

**Step 2: Commit**

```bash
git add src/handlers/event_handler.py
git commit -m "refactor: rewrite event_handler with keyword matching"
```

---

### Task 7: 简化 database.py（移除 todos 表）

**Files:**
- Modify: `src/models/database.py`

**Step 1: 移除 todos 相关代码**

删除：
- `Todo` dataclass
- `todos` 表创建语句
- 所有 todo 相关方法：`add_todo`, `get_pending_todos`, `complete_todo`, `mark_todos_as_reported`

保留：
- `WeeklyReport` dataclass
- `weekly_reports` 表
- 周报相关方法

**Step 2: Commit**

```bash
git add src/models/database.py
git commit -m "refactor: remove todos table from database"
```

---

### Task 8: 更新 main.py

**Files:**
- Modify: `src/main.py`

**Step 1: 移除 IntentService 和 TodoService 的导入和初始化**

删除：
```python
from src.services.intent_service import IntentService
from src.services.todo_service import TodoService

intent_service = IntentService()
todo_service = TodoService(db)
```

**Step 2: 更新 ReportService 初始化**

从：
```python
report_service = ReportService(db, lark_client, doc_service, todo_service)
```

改为：
```python
report_service = ReportService(db, lark_client, doc_service)
```

**Step 3: 更新 EventHandler 初始化**

从：
```python
event_handler = EventHandler(intent_service, report_service, todo_service, lark_client)
```

改为：
```python
event_handler = EventHandler(report_service, lark_client)
```

**Step 4: 简化消息处理**

移除 mentions 处理，简化为：
```python
reply = event_handler.handle_message(chat_id, sender_id, text_content)
```

**Step 5: Commit**

```bash
git add src/main.py
git commit -m "refactor: simplify main.py, remove intent and todo services"
```

---

### Task 9: 更新 scheduler.py（两个定时任务）

**Files:**
- Modify: `src/scheduler.py`

**Step 1: 重写 scheduler.py**

```python
# src/scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import date, timedelta
from src.services.report_service import ReportService
from src.config import Config


class ReportScheduler:
    def __init__(self, report_service: ReportService):
        self.report_service = report_service
        self.scheduler = BackgroundScheduler(timezone="Asia/Shanghai")

    def start(self):
        """启动定时任务"""
        # 周一 11:00 创建周报
        self.scheduler.add_job(
            self._create_weekly_report,
            CronTrigger(day_of_week=0, hour=11, minute=0),  # 0 = 周一
            id="create_report",
            name="Create weekly report"
        )
        print("Scheduler started: Create report at Monday 11:00")

        # 周二 11:00 发送提醒
        self.scheduler.add_job(
            self._send_reminder,
            CronTrigger(day_of_week=1, hour=11, minute=0),  # 1 = 周二
            id="send_reminder",
            name="Send weekly reminder"
        )
        print("Scheduler started: Send reminder at Tuesday 11:00")

        self.scheduler.start()

    def _get_next_wednesday(self) -> date:
        """获取下一个周三"""
        today = date.today()
        days_until_wednesday = (2 - today.weekday()) % 7
        if days_until_wednesday == 0:
            days_until_wednesday = 7
        return today + timedelta(days=days_until_wednesday)

    def _create_weekly_report(self):
        """周一任务：创建周报"""
        # 周一创建的是本周三的周报
        next_wednesday = self._get_next_wednesday()
        print(f"[Scheduler] Creating report for {next_wednesday}")
        result = self.report_service.create_weekly_report(next_wednesday)
        if result:
            print(f"[Scheduler] Report created: {result['doc_url']}")
        else:
            print("[Scheduler] Failed to create report")

    def _send_reminder(self):
        """周二任务：发送提醒"""
        # 周二发送的是明天（周三）的周报提醒
        tomorrow = date.today() + timedelta(days=1)
        print(f"[Scheduler] Sending reminder for {tomorrow}")
        success = self.report_service.send_report_card(tomorrow)
        if success:
            print("[Scheduler] Reminder sent")
        else:
            print("[Scheduler] Failed to send reminder")

    def stop(self):
        """停止定时任务"""
        self.scheduler.shutdown()
```

**Step 2: Commit**

```bash
git add src/scheduler.py
git commit -m "refactor: update scheduler with separate create and remind tasks"
```

---

### Task 10: 清理配置和依赖

**Files:**
- Modify: `src/config.py`
- Modify: `requirements.txt`

**Step 1: 移除 ARK API 配置（不再需要 LLM）**

从 `config.py` 删除：
```python
ARK_API_KEY = os.getenv("ARK_API_KEY", "")
ARK_MODEL_ENDPOINT = os.getenv("ARK_MODEL_ENDPOINT", "")
ARK_BASE_URL = os.getenv("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
```

**注意：保留多维表格配置**（用于记录周报）：
```python
REPORT_BITABLE_APP_TOKEN = os.getenv("REPORT_BITABLE_APP_TOKEN", "")
REPORT_BITABLE_TABLE_ID = os.getenv("REPORT_BITABLE_TABLE_ID", "")
```

**Step 2: 从 requirements.txt 移除 volcengine SDK**

删除 `volcenginesdkarkruntime` 相关依赖。

**Step 3: Commit**

```bash
git add src/config.py requirements.txt
git commit -m "refactor: remove LLM config, keep bitable config"
```

---

### Task 11: 部署和测试

**Step 1: Push 到远程**

```bash
git push origin main
```

**Step 2: 部署到服务器**

```bash
ssh root@115.190.113.142 "cd /root/weekly-report-bot && git pull origin main && pkill -f 'python3 -m src.main' || true; sleep 1; nohup python3 -m src.main > /root/bot.log 2>&1 &"
```

**Step 3: 验证机器人运行**

```bash
ssh root@115.190.113.142 "sleep 3 && ps aux | grep 'python3 -m src.main' | grep -v grep && tail -30 /root/bot.log"
```

**Step 4: 测试功能**

在飞书群里测试：
1. @周报助手 周报 → 应返回最新周报链接
2. @周报助手 跳过 → 应返回"已跳过 YYYY-MM-DD 的周报"
3. @周报助手 取消跳过 → 应返回"已恢复 YYYY-MM-DD 的周报"
4. @周报助手 帮助 → 应返回帮助信息

---

## 验证清单

- [ ] 机器人启动无错误
- [ ] 定时任务正常注册（周一 11:00 创建周报，周二 11:00 发送提醒）
- [ ] @机器人 "周报" 返回链接
- [ ] @机器人 "跳过" 正常工作
- [ ] @机器人 "取消跳过" 正常工作
- [ ] @机器人 "帮助" 返回帮助信息
- [ ] 文档复制后群聊有编辑权限

---

## 简化前后对比

| 项目 | 简化前 | 简化后 |
|------|--------|--------|
| 服务数量 | 5 个 | 3 个 |
| LLM 调用 | 每条消息 | 无 |
| 数据库表 | 2 个 | 1 个 |
| 消息处理 | 复杂意图识别 | 关键词匹配 |
| Todo 功能 | 自动同步 | 用户手动 |
| 代码行数 | ~1000+ | ~400 |
