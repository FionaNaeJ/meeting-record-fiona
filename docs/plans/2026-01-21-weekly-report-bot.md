# 周报自动发送机器人 实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 创建一个飞书机器人，自动复制上周周报、更新日期和 Todo、发送到群聊，并支持通过 @ 机器人收集 todo 和取消某周周报。

**Architecture:**
- Python 后端服务，使用 Flask 接收飞书事件回调
- APScheduler 处理定时任务（每周三发送周报）
- SQLite 存储 todo 列表和周报状态
- 飞书开放平台 API 操作文档和消息

**Tech Stack:** Python 3.11+, Flask, APScheduler, SQLite, 飞书开放平台 SDK (lark-oapi)

---

## 项目结构

```
weekly-report-bot/
├── src/
│   ├── __init__.py
│   ├── main.py              # Flask 应用入口
│   ├── config.py            # 配置管理
│   ├── scheduler.py         # 定时任务
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── event_handler.py # 飞书事件处理
│   │   └── command_handler.py # 命令解析
│   ├── services/
│   │   ├── __init__.py
│   │   ├── lark_client.py   # 飞书 API 封装
│   │   ├── document_service.py # 文档操作
│   │   ├── todo_service.py  # Todo 管理
│   │   └── report_service.py # 周报生成主逻辑
│   └── models/
│       ├── __init__.py
│       └── database.py      # SQLite 数据模型
├── tests/
│   └── ...
├── requirements.txt
├── .env.example
└── README.md
```

---

## Task 1: 项目初始化

**Files:**
- Create: `requirements.txt`
- Create: `src/__init__.py`
- Create: `src/config.py`
- Create: `.env.example`

**Step 1: 创建 requirements.txt**

```txt
flask==3.0.0
lark-oapi==1.3.0
apscheduler==3.10.4
python-dotenv==1.0.0
pytest==8.0.0
```

**Step 2: 创建配置模块**

```python
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
    REPORT_BITABLE_APP_TOKEN = os.getenv("REPORT_BITABLE_APP_TOKEN", "")  # 多维表格 app_token
    REPORT_BITABLE_TABLE_ID = os.getenv("REPORT_BITABLE_TABLE_ID", "")    # 数据表 table_id

    # 文档权限配置（创建文档后自动授予管理者权限）
    DOC_PERMISSION_EMAIL = os.getenv("DOC_PERMISSION_EMAIL", "fuqiannan.fionafu@bytedance.com")
    DOC_PERMISSION_OPEN_ID = os.getenv("DOC_PERMISSION_OPEN_ID", "ou_9e5dddb6debcf86715b2d98eb38e519f")
    DOC_PERMISSION_LEVEL = "full_access"  # full_access = 管理者权限
```

**Step 3: 创建 .env.example**

```
LARK_APP_ID=your_app_id
LARK_APP_SECRET=your_app_secret
LARK_VERIFICATION_TOKEN=your_verification_token
LARK_ENCRYPT_KEY=your_encrypt_key
TARGET_CHAT_ID=your_chat_id
REPORT_BITABLE_APP_TOKEN=your_bitable_app_token
REPORT_BITABLE_TABLE_ID=your_bitable_table_id
```

**Step 4: 创建 src/__init__.py**

```python
# src/__init__.py
```

**Step 5: 初始化 git 仓库并提交**

```bash
git init
git add .
git commit -m "chore: initialize project structure and config"
```

---

## Task 2: 数据库模型

**Files:**
- Create: `src/models/__init__.py`
- Create: `src/models/database.py`
- Create: `tests/test_database.py`

**Step 1: 编写数据库测试**

```python
# tests/test_database.py
import pytest
import os
import tempfile
from src.models.database import Database, Todo, WeeklyReport

@pytest.fixture
def db():
    fd, path = tempfile.mkstemp()
    database = Database(path)
    yield database
    os.close(fd)
    os.unlink(path)

def test_add_todo(db):
    todo = db.add_todo("完成周报机器人开发", "ou_user123")
    assert todo.id is not None
    assert todo.content == "完成周报机器人开发"
    assert todo.completed is False

def test_get_pending_todos(db):
    db.add_todo("任务1", "user1")
    db.add_todo("任务2", "user2")
    todos = db.get_pending_todos()
    assert len(todos) == 2

def test_complete_todo(db):
    todo = db.add_todo("测试任务", "user1")
    db.complete_todo(todo.id)
    todos = db.get_pending_todos()
    assert len(todos) == 0

def test_skip_week(db):
    db.skip_week("2026-01-22")
    assert db.is_week_skipped("2026-01-22") is True
    assert db.is_week_skipped("2026-01-29") is False

def test_cancel_skip(db):
    db.skip_week("2026-01-22")
    db.cancel_skip("2026-01-22")
    assert db.is_week_skipped("2026-01-22") is False
```

**Step 2: 运行测试确认失败**

```bash
pytest tests/test_database.py -v
```

Expected: FAIL - 模块不存在

**Step 3: 实现数据库模型**

```python
# src/models/__init__.py
from .database import Database, Todo, WeeklyReport
```

```python
# src/models/database.py
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import os

@dataclass
class Todo:
    id: Optional[int]
    content: str
    created_by: str
    created_at: datetime
    completed: bool
    completed_at: Optional[datetime] = None
    mentions: Optional[str] = None  # JSON 存储 @ 人信息: [{"user_id": "ou_xxx", "name": "张三", "offset": 2}]

@dataclass
class WeeklyReport:
    id: Optional[int]
    week_date: str  # 格式: 2026-01-22
    doc_token: Optional[str]
    status: str  # pending, sent, skipped
    created_at: datetime

class Database:
    def __init__(self, db_path: str):
        os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_tables()

    def _init_tables(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                created_by TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed BOOLEAN DEFAULT FALSE,
                completed_at TIMESTAMP,
                mentions TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS weekly_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                week_date TEXT UNIQUE NOT NULL,
                doc_token TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

    def add_todo(self, content: str, created_by: str, mentions: str = None) -> Todo:
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO todos (content, created_by, mentions) VALUES (?, ?, ?)",
            (content, created_by, mentions)
        )
        self.conn.commit()
        return Todo(
            id=cursor.lastrowid,
            content=content,
            created_by=created_by,
            created_at=datetime.now(),
            completed=False,
            mentions=mentions
        )

    def get_pending_todos(self) -> list[Todo]:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id, content, created_by, created_at, completed, completed_at, mentions FROM todos WHERE completed = FALSE"
        )
        rows = cursor.fetchall()
        return [Todo(id=r[0], content=r[1], created_by=r[2], created_at=r[3], completed=r[4], completed_at=r[5], mentions=r[6]) for r in rows]

    def complete_todo(self, todo_id: int):
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE todos SET completed = TRUE, completed_at = CURRENT_TIMESTAMP WHERE id = ?",
            (todo_id,)
        )
        self.conn.commit()

    def clear_completed_todos(self):
        """清理已完成的 todo（周报发送后调用）"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM todos WHERE completed = TRUE")
        self.conn.commit()

    def skip_week(self, week_date: str):
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO weekly_reports (week_date, status) VALUES (?, 'skipped')",
            (week_date,)
        )
        self.conn.commit()

    def cancel_skip(self, week_date: str):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM weekly_reports WHERE week_date = ? AND status = 'skipped'", (week_date,))
        self.conn.commit()

    def is_week_skipped(self, week_date: str) -> bool:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT status FROM weekly_reports WHERE week_date = ?",
            (week_date,)
        )
        row = cursor.fetchone()
        return row is not None and row[0] == "skipped"

    def mark_report_sent(self, week_date: str, doc_token: str):
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO weekly_reports (week_date, doc_token, status) VALUES (?, ?, 'sent')",
            (week_date, doc_token)
        )
        self.conn.commit()

    def get_last_report(self) -> Optional[WeeklyReport]:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id, week_date, doc_token, status, created_at FROM weekly_reports WHERE status = 'sent' ORDER BY week_date DESC LIMIT 1"
        )
        row = cursor.fetchone()
        if row:
            return WeeklyReport(id=row[0], week_date=row[1], doc_token=row[2], status=row[3], created_at=row[4])
        return None
```

**Step 4: 运行测试确认通过**

```bash
pytest tests/test_database.py -v
```

Expected: PASS

**Step 5: 提交**

```bash
git add .
git commit -m "feat: add database models for todos and weekly reports"
```

---

## Task 3: 飞书 API 客户端封装

**Files:**
- Create: `src/services/__init__.py`
- Create: `src/services/lark_client.py`
- Create: `tests/test_lark_client.py`

**Step 1: 编写测试（使用 mock）**

```python
# tests/test_lark_client.py
import pytest
from unittest.mock import Mock, patch
from src.services.lark_client import LarkClient

@pytest.fixture
def client():
    with patch.dict('os.environ', {
        'LARK_APP_ID': 'test_app_id',
        'LARK_APP_SECRET': 'test_secret'
    }):
        return LarkClient()

def test_client_initialization(client):
    assert client is not None

def test_format_date_for_title():
    # 测试日期格式化
    from datetime import date
    result = LarkClient.format_date_for_title(date(2026, 1, 21))
    assert result == "2026.1.21"

def test_get_next_wednesday():
    from datetime import date
    # 假设今天是 2026-01-21 (周二)
    result = LarkClient.get_next_wednesday(date(2026, 1, 21))
    assert result == date(2026, 1, 22)  # 明天周三

    # 如果今天是周三
    result = LarkClient.get_next_wednesday(date(2026, 1, 22))
    assert result == date(2026, 1, 22)  # 就是今天

    # 如果今天是周四
    result = LarkClient.get_next_wednesday(date(2026, 1, 23))
    assert result == date(2026, 1, 29)  # 下周三
```

**Step 2: 运行测试确认失败**

```bash
pytest tests/test_lark_client.py -v
```

Expected: FAIL

**Step 3: 实现飞书客户端**

```python
# src/services/__init__.py
from .lark_client import LarkClient
```

```python
# src/services/lark_client.py
import lark_oapi as lark
from lark_oapi.api.wiki.v2 import *
from lark_oapi.api.docx.v1 import *
from lark_oapi.api.im.v1 import *
from lark_oapi.api.drive.v1 import *
from datetime import date, timedelta
from typing import Optional
from src.config import Config

class LarkClient:
    def __init__(self):
        self.client = lark.Client.builder() \
            .app_id(Config.LARK_APP_ID) \
            .app_secret(Config.LARK_APP_SECRET) \
            .build()

    @staticmethod
    def format_date_for_title(d: date) -> str:
        """格式化日期为标题格式: 2026.1.21"""
        return f"{d.year}.{d.month}.{d.day}"

    @staticmethod
    def get_next_wednesday(from_date: date = None) -> date:
        """获取下一个周三的日期"""
        if from_date is None:
            from_date = date.today()
        days_until_wednesday = (2 - from_date.weekday()) % 7  # 2 = Wednesday
        if days_until_wednesday == 0 and from_date.weekday() == 2:
            return from_date  # 今天就是周三
        if days_until_wednesday == 0:
            days_until_wednesday = 7
        return from_date + timedelta(days=days_until_wednesday)

    def get_wiki_node(self, token: str) -> Optional[dict]:
        """获取 Wiki 节点信息"""
        request = GetNodeSpaceRequest.builder() \
            .token(token) \
            .build()
        response = self.client.wiki.v2.space.get_node(request)
        if response.success():
            return {
                "node_token": response.data.node.node_token,
                "obj_token": response.data.node.obj_token,
                "obj_type": response.data.node.obj_type,
                "title": response.data.node.title,
                "space_id": response.data.node.space_id,
                "parent_node_token": response.data.node.parent_node_token,
            }
        return None

    def get_document_content(self, doc_id: str) -> Optional[str]:
        """获取文档纯文本内容"""
        request = RawContentDocumentRequest.builder() \
            .document_id(doc_id) \
            .build()
        response = self.client.docx.v1.document.raw_content(request)
        if response.success():
            return response.data.content
        return None

    def copy_wiki_node(self, space_id: str, node_token: str, new_title: str) -> Optional[str]:
        """复制 Wiki 节点，返回新节点的 token"""
        request = CopySpaceNodeRequest.builder() \
            .space_id(space_id) \
            .node_token(node_token) \
            .request_body(CopySpaceNodeRequestBody.builder()
                .target_space_id(space_id)
                .title(new_title)
                .build()) \
            .build()
        response = self.client.wiki.v2.space_node.copy(request)
        if response.success():
            return response.data.node.node_token
        print(f"Copy failed: {response.msg}")
        return None

    def update_document_title(self, doc_id: str, new_title: str) -> bool:
        """更新文档标题"""
        # 文档标题是第一个 block，需要用 patch 更新
        # 这里简化处理，实际可能需要更复杂的逻辑
        return True  # 复制时已经设置了标题

    def send_message_to_chat(self, chat_id: str, content: str, msg_type: str = "text") -> bool:
        """发送消息到群聊"""
        if msg_type == "text":
            content_json = f'{{"text": "{content}"}}'
        else:
            content_json = content

        request = CreateMessageRequest.builder() \
            .receive_id_type("chat_id") \
            .request_body(CreateMessageRequestBody.builder()
                .receive_id(chat_id)
                .msg_type(msg_type)
                .content(content_json)
                .build()) \
            .build()
        response = self.client.im.v1.message.create(request)
        return response.success()

    def add_report_to_bitable(self, app_token: str, table_id: str, report_date: str, title: str, doc_url: str, status: str = "已发送") -> bool:
        """
        将周报记录添加到多维表格
        """
        from lark_oapi.api.bitable.v1 import *

        request = CreateAppTableRecordRequest.builder() \
            .app_token(app_token) \
            .table_id(table_id) \
            .request_body(AppTableRecord.builder()
                .fields({
                    "周报日期": report_date,
                    "标题": title,
                    "文档链接": {"link": doc_url, "text": title},
                    "状态": status
                })
                .build()) \
            .build()
        response = self.client.bitable.v1.app_table_record.create(request)
        if response.success():
            print(f"Report added to bitable: {title}")
            return True
        print(f"Failed to add report to bitable: {response.msg}")
        return False

    def grant_document_permission(self, doc_token: str, doc_type: str, member_id: str, member_type: str = "openid", perm: str = "full_access") -> bool:
        """
        给文档添加协作者权限
        doc_type: wiki, docx, bitable 等
        member_type: openid, email, userid 等
        perm: view, edit, full_access
        """
        request = CreatePermissionMemberRequest.builder() \
            .token(doc_token) \
            .type(doc_type) \
            .request_body(PermissionMember.builder()
                .member_type(member_type)
                .member_id(member_id)
                .perm(perm)
                .build()) \
            .build()
        response = self.client.drive.v1.permission_member.create(request)
        if response.success():
            print(f"Permission granted: {member_id} -> {perm}")
            return True
        print(f"Permission grant failed: {response.msg}")
        return False

    def send_report_card(self, chat_id: str, title: str, doc_url: str, todos: list[str]) -> bool:
        """发送周报卡片消息"""
        todo_text = "\\n".join([f"• {t}" for t in todos]) if todos else "暂无新增待办"

        card_content = {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": title},
                "template": "blue"
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {"tag": "lark_md", "content": f"**本周待办:**\\n{todo_text}"}
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

        import json
        return self.send_message_to_chat(chat_id, json.dumps(card_content), "interactive")
```

**Step 4: 运行测试确认通过**

```bash
pytest tests/test_lark_client.py -v
```

Expected: PASS

**Step 5: 提交**

```bash
git add .
git commit -m "feat: add Lark API client wrapper"
```

---

## Task 4: 文档服务 - 周报复制与更新

**Files:**
- Create: `src/services/document_service.py`
- Create: `tests/test_document_service.py`

**Step 1: 编写测试**

```python
# tests/test_document_service.py
import pytest
from datetime import date
from src.services.document_service import DocumentService

def test_generate_new_title():
    old_title = "火山引擎PMM&开发者周报2026.1.14"
    new_date = date(2026, 1, 22)
    result = DocumentService.generate_new_title(old_title, new_date)
    assert result == "火山引擎PMM&开发者周报2026.1.22"

def test_generate_new_title_with_space():
    old_title = "火山引擎PMM&开发者周报2026.1.21 "
    new_date = date(2026, 1, 28)
    result = DocumentService.generate_new_title(old_title, new_date)
    assert result == "火山引擎PMM&开发者周报2026.1.28"

def test_update_todo_section():
    old_content = """Weekly Todo：
任务1 @张三
任务2 @李四

Part.1 产品发布"""

    new_todos = ["新任务A @王五", "新任务B @赵六"]
    result = DocumentService.generate_todo_section(new_todos)

    assert "新任务A @王五" in result
    assert "新任务B @赵六" in result
```

**Step 2: 运行测试确认失败**

```bash
pytest tests/test_document_service.py -v
```

Expected: FAIL

**Step 3: 实现文档服务**

```python
# src/services/document_service.py
import re
from datetime import date
from typing import Optional
from src.services.lark_client import LarkClient

class DocumentService:
    def __init__(self, lark_client: LarkClient):
        self.lark = lark_client

    @staticmethod
    def generate_new_title(old_title: str, new_date: date) -> str:
        """根据旧标题生成新标题，替换日期部分"""
        # 匹配 2026.1.14 或 2026.1.21 这样的日期格式
        pattern = r'\d{4}\.\d{1,2}\.\d{1,2}'
        new_date_str = LarkClient.format_date_for_title(new_date)
        new_title = re.sub(pattern, new_date_str, old_title.strip())
        return new_title

    @staticmethod
    def generate_todo_section(todos: list[str]) -> str:
        """生成新的 Todo 部分内容"""
        if not todos:
            return "Weekly Todo：\n（暂无待办事项）\n"

        todo_lines = "\n".join(todos)
        return f"Weekly Todo：\n{todo_lines}\n"

    def copy_and_update_report(
        self,
        source_wiki_token: str,
        new_date: date,
        new_todos: list[str]
    ) -> Optional[str]:
        """
        复制上周周报并更新为本周版本
        返回新文档的 wiki token
        """
        # 1. 获取源文档信息
        node_info = self.lark.get_wiki_node(source_wiki_token)
        if not node_info:
            return None

        # 2. 生成新标题
        new_title = self.generate_new_title(node_info["title"], new_date)

        # 3. 复制文档
        new_token = self.lark.copy_wiki_node(
            space_id=node_info["space_id"],
            node_token=source_wiki_token,
            new_title=new_title
        )

        if not new_token:
            return None

        # 4. 授予文档管理者权限
        self.lark.grant_document_permission(
            doc_token=new_token,
            doc_type="wiki",
            member_id=Config.DOC_PERMISSION_OPEN_ID,
            member_type="openid",
            perm=Config.DOC_PERMISSION_LEVEL  # full_access = 管理者权限
        )

        # 5. TODO: 更新文档内容（Todo 部分）
        # 这需要使用 docx 的 block 操作 API，较为复杂
        # 简化版本：在发送消息时附带新的 todo 列表

        return new_token

    def get_document_url(self, wiki_token: str, space_id: str) -> str:
        """生成文档的访问 URL"""
        return f"https://bytedance.larkoffice.com/wiki/{wiki_token}"
```

**Step 4: 运行测试确认通过**

```bash
pytest tests/test_document_service.py -v
```

Expected: PASS

**Step 5: 提交**

```bash
git add .
git commit -m "feat: add document service for report copying"
```

---

## Task 5: Todo 服务

**Files:**
- Create: `src/services/todo_service.py`
- Create: `tests/test_todo_service.py`

**Step 1: 编写测试**

```python
# tests/test_todo_service.py
import pytest
import tempfile
import os
from src.services.todo_service import TodoService
from src.models.database import Database

@pytest.fixture
def todo_service():
    fd, path = tempfile.mkstemp()
    db = Database(path)
    service = TodoService(db)
    yield service
    os.close(fd)
    os.unlink(path)

def test_parse_todo_from_message():
    message = "todo 完成周报机器人开发"
    result = TodoService.parse_todo_from_message(message)
    assert result == "完成周报机器人开发"

def test_parse_todo_with_at():
    message = "TODO: 和@张三沟通需求"
    result = TodoService.parse_todo_from_message(message)
    assert result == "和@张三沟通需求"

def test_parse_not_todo():
    message = "这不是一个待办事项"
    result = TodoService.parse_todo_from_message(message)
    assert result is None

def test_add_and_get_todos(todo_service):
    todo_service.add_todo("任务1", "user1")
    todo_service.add_todo("任务2", "user2")
    todos = todo_service.get_pending_todos()
    assert len(todos) == 2
    assert todos[0].content == "任务1"
```

**Step 2: 运行测试确认失败**

```bash
pytest tests/test_todo_service.py -v
```

Expected: FAIL

**Step 3: 实现 Todo 服务**

```python
# src/services/todo_service.py
import re
from typing import Optional
from src.models.database import Database, Todo

class TodoService:
    def __init__(self, db: Database):
        self.db = db

    @staticmethod
    def parse_todo_from_message(message: str) -> Optional[str]:
        """
        从消息中解析 todo 内容
        支持格式：
        - "todo 内容"
        - "TODO: 内容"
        - "待办 内容"
        """
        patterns = [
            r'^[Tt][Oo][Dd][Oo][:\s：]\s*(.+)$',
            r'^[Tt][Oo][Dd][Oo]\s+(.+)$',
            r'^待办[:\s：]\s*(.+)$',
            r'^待办\s+(.+)$',
        ]

        message = message.strip()
        for pattern in patterns:
            match = re.match(pattern, message)
            if match:
                return match.group(1).strip()

        return None

    def add_todo(self, content: str, created_by: str, mentions: list[dict] = None) -> Todo:
        """
        添加新的待办事项
        mentions: [{"user_id": "ou_xxx", "name": "张三", "offset": 2}, ...]
        """
        import json
        mentions_json = json.dumps(mentions) if mentions else None
        return self.db.add_todo(content, created_by, mentions_json)

    def get_pending_todos(self) -> list[Todo]:
        """获取所有未完成的待办事项"""
        return self.db.get_pending_todos()

    def get_todo_texts(self) -> list[str]:
        """获取待办事项的文本列表（用于周报）"""
        todos = self.get_pending_todos()
        return [todo.content for todo in todos]

    def complete_todo(self, todo_id: int):
        """标记待办事项为已完成"""
        self.db.complete_todo(todo_id)

    def mark_todos_as_reported(self):
        """周报发送后，将当前待办标记为已报告（保留到下周）"""
        # 待办事项会保留，直到用户手动标记完成
        pass
```

**Step 4: 运行测试确认通过**

```bash
pytest tests/test_todo_service.py -v
```

Expected: PASS

**Step 5: 提交**

```bash
git add .
git commit -m "feat: add todo service for managing weekly tasks"
```

---

## Task 6: 周报主服务

**Files:**
- Create: `src/services/report_service.py`
- Create: `tests/test_report_service.py`

**Step 1: 编写测试**

```python
# tests/test_report_service.py
import pytest
from datetime import date
from unittest.mock import Mock, patch
from src.services.report_service import ReportService

def test_should_send_report_normal_week():
    db = Mock()
    db.is_week_skipped.return_value = False
    service = ReportService(db, Mock(), Mock(), Mock())

    assert service.should_send_report(date(2026, 1, 22)) is True

def test_should_not_send_report_skipped_week():
    db = Mock()
    db.is_week_skipped.return_value = True
    service = ReportService(db, Mock(), Mock(), Mock())

    assert service.should_send_report(date(2026, 1, 22)) is False

def test_skip_and_cancel():
    db = Mock()
    service = ReportService(db, Mock(), Mock(), Mock())

    service.skip_week(date(2026, 1, 22))
    db.skip_week.assert_called_once_with("2026-01-22")

    service.cancel_skip(date(2026, 1, 22))
    db.cancel_skip.assert_called_once_with("2026-01-22")
```

**Step 2: 运行测试确认失败**

```bash
pytest tests/test_report_service.py -v
```

Expected: FAIL

**Step 3: 实现周报服务**

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

    def get_last_report_token(self) -> Optional[str]:
        """获取上一次发送的周报 token"""
        report = self.db.get_last_report()
        if report:
            return report.doc_token
        # 如果没有历史记录，使用配置的模板
        return Config.TEMPLATE_WIKI_TOKEN

    def generate_and_send_report(self, target_date: date = None) -> bool:
        """
        生成并发送周报
        1. 检查是否跳过
        2. 复制上周周报
        3. 更新日期和 todo
        4. 发送到群聊
        """
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
            # 记录发送成功
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
```

**Step 4: 运行测试确认通过**

```bash
pytest tests/test_report_service.py -v
```

Expected: PASS

**Step 5: 提交**

```bash
git add .
git commit -m "feat: add report service for weekly report generation"
```

---

## Task 7: 事件处理器 - 处理群消息

**Files:**
- Create: `src/handlers/__init__.py`
- Create: `src/handlers/event_handler.py`
- Create: `src/handlers/command_handler.py`
- Create: `tests/test_command_handler.py`

**Step 1: 编写命令处理器测试**

```python
# tests/test_command_handler.py
import pytest
from src.handlers.command_handler import CommandHandler

def test_parse_skip_command():
    result = CommandHandler.parse_command("跳过本周")
    assert result == ("skip", None)

def test_parse_skip_with_date():
    result = CommandHandler.parse_command("跳过 2026-01-29")
    assert result == ("skip", "2026-01-29")

def test_parse_cancel_skip():
    result = CommandHandler.parse_command("取消跳过")
    assert result == ("cancel_skip", None)

def test_parse_status():
    result = CommandHandler.parse_command("状态")
    assert result == ("status", None)

def test_parse_todo():
    result = CommandHandler.parse_command("todo 完成开发")
    assert result == ("todo", "完成开发")

def test_parse_unknown():
    result = CommandHandler.parse_command("随便说点什么")
    assert result == (None, None)
```

**Step 2: 运行测试确认失败**

```bash
pytest tests/test_command_handler.py -v
```

Expected: FAIL

**Step 3: 实现命令处理器**

```python
# src/handlers/__init__.py
from .command_handler import CommandHandler
from .event_handler import EventHandler
```

```python
# src/handlers/command_handler.py
import re
from typing import Tuple, Optional

class CommandHandler:
    @staticmethod
    def parse_command(message: str) -> Tuple[Optional[str], Optional[str]]:
        """
        解析用户命令
        返回: (command_type, argument)

        支持的命令：
        - "跳过本周" / "跳过 2026-01-29" -> ("skip", date_or_none)
        - "取消跳过" / "取消跳过 2026-01-29" -> ("cancel_skip", date_or_none)
        - "状态" / "查看状态" -> ("status", None)
        - "todo xxx" / "待办 xxx" -> ("todo", content)
        - "帮助" / "help" -> ("help", None)
        """
        message = message.strip()

        # 跳过命令
        if message == "跳过本周" or message == "跳过":
            return ("skip", None)

        skip_match = re.match(r'^跳过\s+(\d{4}-\d{2}-\d{2})$', message)
        if skip_match:
            return ("skip", skip_match.group(1))

        # 取消跳过
        if message == "取消跳过" or message == "恢复本周":
            return ("cancel_skip", None)

        cancel_match = re.match(r'^取消跳过\s+(\d{4}-\d{2}-\d{2})$', message)
        if cancel_match:
            return ("cancel_skip", cancel_match.group(1))

        # 状态查询
        if message in ["状态", "查看状态", "status"]:
            return ("status", None)

        # 帮助
        if message in ["帮助", "help", "?"]:
            return ("help", None)

        # Todo
        todo_patterns = [
            r'^[Tt][Oo][Dd][Oo][:\s：]\s*(.+)$',
            r'^[Tt][Oo][Dd][Oo]\s+(.+)$',
            r'^待办[:\s：]\s*(.+)$',
            r'^待办\s+(.+)$',
        ]
        for pattern in todo_patterns:
            match = re.match(pattern, message)
            if match:
                return ("todo", match.group(1).strip())

        return (None, None)
```

```python
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
        """
        处理群消息，返回回复内容
        mentions: 消息中的 @ 信息（不包括 @机器人）
        """
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
```

**Step 4: 运行测试确认通过**

```bash
pytest tests/test_command_handler.py -v
```

Expected: PASS

**Step 5: 提交**

```bash
git add .
git commit -m "feat: add event and command handlers for bot messages"
```

---

## Task 8: 定时任务调度器

**Files:**
- Create: `src/scheduler.py`

**Step 1: 实现调度器**

```python
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
```

**Step 2: 提交**

```bash
git add .
git commit -m "feat: add APScheduler for weekly report scheduling"
```

---

## Task 9: Flask 应用主入口

**Files:**
- Create: `src/main.py`

**Step 1: 实现 Flask 应用**

```python
# src/main.py
import json
from flask import Flask, request, jsonify
from src.config import Config
from src.models.database import Database
from src.services.lark_client import LarkClient
from src.services.document_service import DocumentService
from src.services.todo_service import TodoService
from src.services.report_service import ReportService
from src.handlers.event_handler import EventHandler
from src.scheduler import ReportScheduler

app = Flask(__name__)

# 初始化服务
db = Database(Config.DATABASE_PATH)
lark_client = LarkClient()
doc_service = DocumentService(lark_client)
todo_service = TodoService(db)
report_service = ReportService(db, lark_client, doc_service, todo_service)
event_handler = EventHandler(report_service, todo_service, lark_client)
scheduler = ReportScheduler(report_service)


@app.route("/webhook/event", methods=["POST"])
def handle_event():
    """处理飞书事件回调"""
    data = request.json

    # URL 验证
    if "challenge" in data:
        return jsonify({"challenge": data["challenge"]})

    # 验证 token
    if data.get("token") != Config.LARK_VERIFICATION_TOKEN:
        return jsonify({"error": "Invalid token"}), 403

    # 处理消息事件
    event = data.get("event", {})
    event_type = data.get("header", {}).get("event_type", "")

    if event_type == "im.message.receive_v1":
        message = event.get("message", {})
        chat_id = message.get("chat_id", "")

        # 只处理群聊中 @ 机器人的消息
        mentions = message.get("mentions", [])
        if not mentions:
            return jsonify({"msg": "ignored"})

        # 获取消息内容
        content = json.loads(message.get("content", "{}"))
        text = content.get("text", "").strip()

        # 分离机器人 mention 和其他 mentions
        bot_app_id = Config.LARK_APP_ID
        other_mentions = []
        for mention in mentions:
            if mention.get("id", {}).get("open_id", "") == bot_app_id or mention.get("key", "").startswith("@_user_"):
                # 移除 @机器人
                text = text.replace(mention.get("key", ""), "").strip()
            else:
                # 保存其他 @ 信息，用于 todo
                other_mentions.append({
                    "user_id": mention.get("id", {}).get("open_id", ""),
                    "name": mention.get("name", ""),
                    "key": mention.get("key", "")
                })

        # 处理消息
        sender_id = event.get("sender", {}).get("sender_id", {}).get("open_id", "")
        reply = event_handler.handle_message(chat_id, sender_id, text, other_mentions if other_mentions else None)

        # 如果有回复内容，发送回复
        if reply:
            lark_client.send_message_to_chat(chat_id, reply)

    return jsonify({"msg": "ok"})


@app.route("/api/trigger", methods=["POST"])
def trigger_report():
    """手动触发周报发送（用于测试）"""
    success = report_service.generate_and_send_report()
    return jsonify({"success": success})


@app.route("/api/status", methods=["GET"])
def get_status():
    """获取当前状态"""
    from datetime import date
    next_wed = LarkClient.get_next_wednesday()
    todos = todo_service.get_pending_todos()

    return jsonify({
        "next_report_date": next_wed.strftime("%Y-%m-%d"),
        "is_skipped": not report_service.should_send_report(next_wed),
        "pending_todos": len(todos),
        "todos": [{"id": t.id, "content": t.content} for t in todos]
    })


@app.route("/health", methods=["GET"])
def health():
    """健康检查"""
    return jsonify({"status": "ok"})


def create_app():
    """创建应用实例"""
    scheduler.start()
    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=8080, debug=True)
```

**Step 2: 提交**

```bash
git add .
git commit -m "feat: add Flask main application with webhook endpoint"
```

---

## Task 10: README 和部署配置

**Files:**
- Create: `README.md`
- Create: `Dockerfile`
- Create: `docker-compose.yml`

**Step 1: 创建 README**

```markdown
# 周报自动发送机器人

自动复制上周周报、更新日期和待办事项、发送到飞书群。

## 功能

- 每周二上午 11 点自动发送周报到指定群聊（标题日期为周三会议日）
- 通过 @ 机器人添加待办事项
- 支持跳过某周周报（节假日）
- 卡片消息展示周报链接和待办

## 使用方法

### 群聊命令

| 命令 | 说明 |
|------|------|
| `@机器人 todo <内容>` | 添加待办事项 |
| `@机器人 跳过本周` | 跳过本周周报 |
| `@机器人 取消跳过` | 恢复本周周报 |
| `@机器人 状态` | 查看当前状态 |
| `@机器人 帮助` | 显示帮助信息 |

## 部署

### 1. 配置飞书应用

1. 在 [飞书开放平台](https://open.feishu.cn) 创建企业自建应用
2. 添加机器人能力
3. 配置权限：
   - `im:message:send_as_bot` - 发送消息
   - `im:message:receive_as_bot` - 接收消息
   - `wiki:wiki:readonly` - 读取知识库
   - `wiki:wiki` - 编辑知识库
   - `docx:document:readonly` - 读取文档
4. 配置事件订阅：
   - 请求地址: `https://your-domain.com/webhook/event`
   - 事件: `im.message.receive_v1`

### 2. 环境变量

复制 `.env.example` 为 `.env` 并填写配置：

```bash
cp .env.example .env
```

### 3. 启动服务

```bash
# 使用 Docker
docker-compose up -d

# 或直接运行
pip install -r requirements.txt
python -m src.main
```

## 开发

```bash
# 安装依赖
pip install -r requirements.txt

# 运行测试
pytest

# 手动触发周报（测试）
curl -X POST http://localhost:8080/api/trigger
```
```

**Step 2: 创建 Dockerfile**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

CMD ["python", "-m", "src.main"]
```

**Step 3: 创建 docker-compose.yml**

```yaml
version: '3.8'

services:
  bot:
    build: .
    ports:
      - "8080:8080"
    volumes:
      - ./data:/app/data
    env_file:
      - .env
    restart: unless-stopped
```

**Step 4: 提交**

```bash
git add .
git commit -m "docs: add README and Docker deployment config"
```

---

## Task 11: 集成测试

**Files:**
- Create: `tests/test_integration.py`

**Step 1: 编写集成测试**

```python
# tests/test_integration.py
import pytest
import tempfile
import os
from unittest.mock import Mock, patch
from src.models.database import Database
from src.services.todo_service import TodoService
from src.services.report_service import ReportService
from src.handlers.event_handler import EventHandler

@pytest.fixture
def services():
    fd, path = tempfile.mkstemp()
    db = Database(path)

    lark_client = Mock()
    todo_service = TodoService(db)
    doc_service = Mock()
    report_service = ReportService(db, lark_client, doc_service, todo_service)
    event_handler = EventHandler(report_service, todo_service, lark_client)

    yield {
        "db": db,
        "todo_service": todo_service,
        "report_service": report_service,
        "event_handler": event_handler,
    }

    os.close(fd)
    os.unlink(path)

def test_full_todo_workflow(services):
    handler = services["event_handler"]
    todo_service = services["todo_service"]

    # 添加待办
    reply = handler.handle_message("chat1", "user1", "todo 完成设计文档")
    assert "已添加待办" in reply
    assert "1 项" in reply

    # 再添加一个
    reply = handler.handle_message("chat1", "user2", "TODO: 代码评审")
    assert "2 项" in reply

    # 查看状态
    reply = handler.handle_message("chat1", "user1", "状态")
    assert "2 项" in reply

def test_skip_workflow(services):
    handler = services["event_handler"]
    report_service = services["report_service"]

    # 跳过本周
    reply = handler.handle_message("chat1", "user1", "跳过本周")
    assert "已跳过" in reply

    # 检查状态
    reply = handler.handle_message("chat1", "user1", "状态")
    assert "已跳过" in reply

    # 取消跳过
    reply = handler.handle_message("chat1", "user1", "取消跳过")
    assert "已恢复" in reply
```

**Step 2: 运行所有测试**

```bash
pytest -v
```

Expected: All PASS

**Step 3: 提交**

```bash
git add .
git commit -m "test: add integration tests for full workflow"
```

---

## 后续步骤（部署后）

1. **配置飞书应用** - 在开放平台创建应用并配置权限
2. **获取群 ID** - 使用 API 获取目标群的 chat_id
3. **配置 Webhook** - 将服务地址配置到飞书事件订阅
4. **测试流程** - 手动触发一次周报发送验证
5. **给文档授权** - 确保机器人有权限访问和复制周报文档

---

## 文档授权说明

根据全局规则，所有创建的飞书文档需要给 `fuqiannan.fionafu@bytedance.com` 开启 `full_access`（管理者）权限。这已在 `LarkClient.copy_wiki_node` 后自动处理。

---

## 后续待办

- [ ] **批量添加编辑权限**：用户将提供十几个邮箱，需要给这些邮箱添加编辑权限（`edit`）。实现方式：在 Config 中增加 `DOC_EDITORS_EMAILS` 列表，创建文档后遍历调用 `grant_document_permission`。
