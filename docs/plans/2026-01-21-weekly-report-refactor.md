# Weekly Report Bot Refactor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 重构周报机器人，实现异步处理 todo、同周更新同一份周报、复制最后一份周报而非固定模板。

**Architecture:**
- 收到 todo 后先回复"已接收"，通过线程异步创建/更新周报
- 使用云空间文档（docx）而非知识库（wiki），通过飞书 Drive API 复制文档
- 数据库记录每周周报的 doc_token 和 doc_url，同一周内更新同一份

**Tech Stack:** Python 3, Flask, lark-oapi, APScheduler, SQLite, httpx

---

### Task 1: 更新配置 - 使用云空间文档模板

**Files:**
- Modify: `src/config.py:15-17`

**Step 1: 修改配置**

将 wiki 模板改为 docx 模板：

```python
# 周报配置 - 使用云空间文档（非知识库）
TEMPLATE_DOC_TOKEN = os.getenv("TEMPLATE_DOC_TOKEN", "CzQ2dUoAmoI5GXxsVswcjw2YnGh")
TARGET_CHAT_ID = os.getenv("TARGET_CHAT_ID")  # 发送周报的群 ID
```

删除 `TEMPLATE_WIKI_TOKEN` 和 `WIKI_SPACE_ID`。

**Step 2: 更新 .env 文件**

确保服务器上的 .env 包含：
```
TEMPLATE_DOC_TOKEN=CzQ2dUoAmoI5GXxsVswcjw2YnGh
```

**Step 3: Commit**

```bash
git add src/config.py
git commit -m "refactor: use docx template instead of wiki"
```

---

### Task 2: 扩展数据库 - 添加周报 URL 和查询方法

**Files:**
- Modify: `src/models/database.py:21-25,116-132`

**Step 1: 修改 WeeklyReport dataclass**

```python
@dataclass
class WeeklyReport:
    id: Optional[int]
    week_date: str  # 格式: 2026-01-22 (下周三的日期)
    doc_token: Optional[str]
    doc_url: Optional[str]  # 新增：文档 URL
    status: str  # pending, sent, skipped
    created_at: datetime
```

**Step 2: 修改数据库表结构**

在 `_init_tables` 方法中添加 `doc_url` 列：

```python
cursor.execute("""
    CREATE TABLE IF NOT EXISTS weekly_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        week_date TEXT UNIQUE NOT NULL,
        doc_token TEXT,
        doc_url TEXT,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
```

**Step 3: 添加查询本周周报的方法**

```python
def get_report_by_week_date(self, week_date: str) -> Optional[WeeklyReport]:
    """获取指定周的周报"""
    cursor = self.conn.cursor()
    cursor.execute(
        "SELECT id, week_date, doc_token, doc_url, status, created_at FROM weekly_reports WHERE week_date = ?",
        (week_date,)
    )
    row = cursor.fetchone()
    if row:
        return WeeklyReport(id=row[0], week_date=row[1], doc_token=row[2], doc_url=row[3], status=row[4], created_at=row[5])
    return None
```

**Step 4: 修改 mark_report_sent 方法**

```python
def mark_report_sent(self, week_date: str, doc_token: str, doc_url: str):
    """标记周报已发送/已创建"""
    cursor = self.conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO weekly_reports (week_date, doc_token, doc_url, status) VALUES (?, ?, ?, 'sent')",
        (week_date, doc_token, doc_url)
    )
    self.conn.commit()
```

**Step 5: 修改 get_last_report 方法**

```python
def get_last_report(self) -> Optional[WeeklyReport]:
    cursor = self.conn.cursor()
    cursor.execute(
        "SELECT id, week_date, doc_token, doc_url, status, created_at FROM weekly_reports WHERE status = 'sent' ORDER BY week_date DESC LIMIT 1"
    )
    row = cursor.fetchone()
    if row:
        return WeeklyReport(id=row[0], week_date=row[1], doc_token=row[2], doc_url=row[3], status=row[4], created_at=row[5])
    return None
```

**Step 6: Commit**

```bash
git add src/models/database.py
git commit -m "feat: add doc_url field and get_report_by_week_date method"
```

---

### Task 3: 添加飞书云空间文档复制 API

**Files:**
- Modify: `src/services/lark_client.py:123-178`

**Step 1: 添加复制云空间文档的方法**

替换之前的 `create_document_from_markdown` 方法：

```python
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
        print("Failed to get tenant access token")
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
        print(f"[LarkClient] Copy document response: {resp.status_code} {resp.text[:200]}")

        if resp.status_code != 200:
            print(f"Copy document failed: {resp.text}")
            return None

        data = resp.json()
        if data.get("code") != 0:
            print(f"Copy document error: {data.get('msg')}")
            return None

        new_token = data["data"]["file"]["token"]
        doc_url = f"https://bytedance.larkoffice.com/docx/{new_token}"

        return {"doc_token": new_token, "doc_url": doc_url}
```

**Step 2: 删除旧的 create_document_from_markdown 方法**

删除之前添加的 `create_document_from_markdown` 方法（第 123-163 行）。

**Step 3: Commit**

```bash
git add src/services/lark_client.py
git commit -m "feat: add copy_document method for docx files"
```

---

### Task 4: 重写文档服务 - 复制和更新周报

**Files:**
- Modify: `src/services/document_service.py`

**Step 1: 完全重写 document_service.py**

```python
# src/services/document_service.py
from __future__ import annotations
import re
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
        # 生成新标题
        new_title = self.generate_new_title(target_date)

        # 复制文档
        result = self.lark.copy_document(source_doc_token, new_title)
        if not result:
            print(f"[DocumentService] Failed to copy document from {source_doc_token}")
            return None

        doc_token = result["doc_token"]
        doc_url = result["doc_url"]

        print(f"[DocumentService] Created new report: {doc_url}")

        # 授予文档管理者权限
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
git commit -m "refactor: simplify document service for docx copy"
```

---

### Task 5: 重写周报服务 - 同周更新同一份

**Files:**
- Modify: `src/services/report_service.py`

**Step 1: 完全重写 report_service.py**

```python
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

        # 保存到数据库
        self.db.mark_report_sent(date_str, result["doc_token"], result["doc_url"])
        print(f"[ReportService] Created new report: {result['doc_url']}")

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

        # 获取待办事项
        todos = self.todo_service.get_todo_texts()

        # 生成标题
        title = self.doc_service.generate_new_title(target_date)

        # 发送卡片
        success = self.lark.send_report_card(
            chat_id=Config.TARGET_CHAT_ID,
            title=title,
            doc_url=report.doc_url,
            todos=todos
        )

        if success:
            print(f"[ReportService] Report card sent for {date_str}")

            # 添加到周报汇总表
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
```

**Step 2: Commit**

```bash
git add src/services/report_service.py
git commit -m "refactor: report service with get_or_create_weekly_report"
```

---

### Task 6: 重写事件处理 - 异步处理 todo

**Files:**
- Modify: `src/handlers/event_handler.py`

**Step 1: 完全重写 event_handler.py**

```python
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
            return self._handle_todo(chat_id, message, user_id, mentions)
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
        """处理 todo 意图：先回复确认，异步创建/更新周报"""
        if not content:
            return ""

        # 1. 保存 todo
        self.todo_service.add_todo(content, user_id, mentions)

        # 2. 异步创建/更新周报
        thread = threading.Thread(
            target=self._async_update_report,
            args=(chat_id,),
            daemon=True
        )
        thread.start()

        # 3. 立即返回确认
        return "已接收 todo，正在更新周报..."

    def _async_update_report(self, chat_id: str):
        """异步更新周报并发送结果"""
        try:
            target_date = LarkClient.get_next_wednesday()
            result = self.report_service.get_or_create_weekly_report(target_date)

            if result:
                message = f"周报已更新：{result['doc_url']}"
            else:
                message = "周报更新失败，请稍后重试"

            self.lark.send_message_to_chat(chat_id, message)

        except Exception as e:
            print(f"[EventHandler] Error in async update: {e}")
            import traceback
            traceback.print_exc()
            self.lark.send_message_to_chat(chat_id, "周报更新出错，请稍后重试")

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
```

**Step 2: Commit**

```bash
git add src/handlers/event_handler.py
git commit -m "refactor: async todo handling with immediate reply"
```

---

### Task 7: 更新定时任务 - 检查周报日期

**Files:**
- Modify: `src/scheduler.py:37-47`

**Step 1: 修改定时任务逻辑**

```python
def _send_weekly_report(self):
    """执行周报发送任务（周二 11:00 执行）"""
    from datetime import timedelta
    from src.services.lark_client import LarkClient

    print("[Scheduler] Running scheduled weekly report...")

    try:
        # 计算明天（周三）的日期
        today = LarkClient.get_next_wednesday()  # 如果今天是周二，这会返回明天周三
        # 但我们需要确保是"明天"，所以用更直接的方式
        from datetime import date
        tomorrow = date.today() + timedelta(days=1)

        print(f"[Scheduler] Tomorrow is {tomorrow}, sending report card...")

        success = self.report_service.send_report_card(tomorrow)
        if success:
            print("[Scheduler] Weekly report card sent successfully")
        else:
            print("[Scheduler] Weekly report card was skipped or failed")

    except Exception as e:
        print(f"[Scheduler] Error sending weekly report: {e}")
        import traceback
        traceback.print_exc()
```

**Step 2: Commit**

```bash
git add src/scheduler.py
git commit -m "refactor: scheduler sends card for tomorrow's date"
```

---

### Task 8: 添加内容去重 - 防止重复处理相同消息

**Files:**
- Modify: `src/main.py:29-31,56-65`

**Step 1: 添加内容哈希去重**

在消息去重部分添加内容哈希：

```python
import hashlib

# 消息去重缓存
processed_messages = set()  # message_id 去重
processed_content_hashes = {}  # 内容哈希去重 {hash: timestamp}
MAX_CACHE_SIZE = 1000
CONTENT_DEDUP_SECONDS = 300  # 5 分钟内相同内容不重复处理
```

**Step 2: 修改 handle_im_message 函数**

在消息 ID 去重之后，处理消息之前，添加内容去重：

```python
# 内容去重（5 分钟内相同内容不重复处理）
import time
content_hash = hashlib.md5(text.encode()).hexdigest()
current_time = time.time()

if content_hash in processed_content_hashes:
    last_time = processed_content_hashes[content_hash]
    if current_time - last_time < CONTENT_DEDUP_SECONDS:
        print(f"[DEBUG] Duplicate content within {CONTENT_DEDUP_SECONDS}s, skipping")
        return

processed_content_hashes[content_hash] = current_time

# 清理过期的内容哈希
expired_hashes = [h for h, t in processed_content_hashes.items() if current_time - t > CONTENT_DEDUP_SECONDS * 2]
for h in expired_hashes:
    del processed_content_hashes[h]
```

**Step 3: Commit**

```bash
git add src/main.py
git commit -m "feat: add content-based deduplication"
```

---

### Task 9: 删除无用代码和清理

**Files:**
- Modify: `src/services/lark_client.py` - 删除旧的 wiki 相关方法
- Modify: `src/config.py` - 删除 WIKI_SPACE_ID

**Step 1: 清理 lark_client.py**

删除以下方法（如果不再使用）：
- `get_wiki_node`
- `copy_wiki_node`

保留 `_get_tenant_access_token` 方法。

**Step 2: 清理 config.py**

删除 `WIKI_SPACE_ID` 配置。

**Step 3: Commit**

```bash
git add src/services/lark_client.py src/config.py
git commit -m "chore: remove unused wiki-related code"
```

---

### Task 10: 部署和测试

**Step 1: 同步代码到服务器**

```bash
scp -r src/ root@115.190.113.142:/root/weekly-report-bot/
```

**Step 2: 重启服务**

```bash
ssh root@115.190.113.142 "pkill -f 'python3 -m src.main' || true; cd /root/weekly-report-bot && nohup python3 -m src.main > /root/bot.log 2>&1 &"
```

**Step 3: 测试流程**

1. 在群里 @机器人 发送 todo
2. 验证：立即收到"已接收 todo，正在更新周报..."
3. 验证：几秒后收到"周报已更新：{url}"
4. 验证：URL 是 docx 格式，文档标题日期是下周三
5. 再次发送 todo，验证更新的是同一份周报
6. 发送相同内容，验证不会重复处理

**Step 4: 检查日志**

```bash
ssh root@115.190.113.142 "tail -50 /root/bot.log"
```

---

## 完整流程图

```
用户 @机器人 发送 todo
        ↓
    消息 ID 去重
        ↓
    内容哈希去重（5分钟）
        ↓
    LLM 识别意图 = todo
        ↓
    保存 todo 到数据库
        ↓
    立即回复"已接收 todo，正在更新周报..."
        ↓
    [异步线程]
        ↓
    计算下周三日期
        ↓
    数据库查询：本周周报存在?
       ↓            ↓
      存在         不存在
       ↓            ↓
    返回现有      获取最后一份周报 token
       ↓            ↓
       ←          复制创建新文档
                    ↓
                 授权文档权限
                    ↓
                 保存到数据库
        ↓
    发送"周报已更新：{url}"

---

每周二 11:00 定时任务
        ↓
    计算明天（周三）日期
        ↓
    检查是否跳过
        ↓
    数据库查询本周周报
        ↓
    发送卡片消息到群
```
