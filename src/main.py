# src/main.py
from __future__ import annotations
import json
import hashlib
import time
import threading
from flask import Flask, jsonify
import lark_oapi as lark
from lark_oapi.api.im.v1 import P2ImMessageReceiveV1

from src.config import Config
from src.version import __version__
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

# 消息去重缓存
processed_messages = set()  # message_id 去重
processed_content_hashes = {}  # 内容哈希去重 {hash: timestamp}
MAX_CACHE_SIZE = 1000
CONTENT_DEDUP_SECONDS = 300  # 5 分钟内相同内容不重复处理


def extract_text_from_post(content: dict) -> str:
    """从富文本消息中提取纯文本"""
    texts = []
    for line in content.get("content", []):
        for item in line:
            if item.get("tag") == "text":
                texts.append(item.get("text", ""))
            elif item.get("tag") == "at":
                # 保留 @user_id 格式，后面会处理
                texts.append(item.get("user_id", ""))
    return "".join(texts)


def handle_im_message(data: P2ImMessageReceiveV1):
    """处理飞书消息事件（长连接模式）"""
    global processed_messages

    try:
        event = data.event
        message = event.message
        message_id = message.message_id

        # 使用 message_id + create_time 去重
        dedup_key = f"{message_id}_{message.create_time}"
        if dedup_key in processed_messages:
            print(f"[DEBUG] Duplicate message {dedup_key}, skipping")
            return
        processed_messages.add(dedup_key)

        # 防止缓存过大
        if len(processed_messages) > MAX_CACHE_SIZE:
            processed_messages = set(list(processed_messages)[-500:])

        chat_id = message.chat_id
        message_type = message.message_type

        print(f"[DEBUG] Processing message {message_id}, chat_id={chat_id}")

        # 只处理群聊中 @ 机器人的消息
        mentions = message.mentions or []
        if not mentions:
            print("[DEBUG] No mentions, ignoring")
            return

        # 获取消息内容（支持 text 和 post 类型）
        content = json.loads(message.content or "{}")
        if message_type == "text":
            text = content.get("text", "").strip()
        elif message_type == "post":
            text = extract_text_from_post(content)
        else:
            print(f"[DEBUG] Unsupported message type: {message_type}")
            return

        print(f"[DEBUG] Extracted text: {text[:100]}...")

        # 分离机器人 mention 和其他 mentions
        other_mentions = []
        for mention in mentions:
            mention_key = mention.key or ""
            if mention_key == "@_user_1":
                # @_user_1 是机器人自己，移除
                text = text.replace(mention_key, "").strip()
            else:
                # 保存其他 @ 信息
                other_mentions.append({
                    "user_id": mention.id.open_id if mention.id else "",
                    "name": mention.name or "",
                    "key": mention_key
                })
                # 也移除其他 @ 标记
                text = text.replace(mention_key, "").strip()

        print(f"[DEBUG] Final text for LLM: {text[:100]}...")

        # 内容去重（5 分钟内相同内容不重复处理）
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

        # 处理消息
        sender_id = event.sender.sender_id.open_id if event.sender and event.sender.sender_id else ""
        reply = event_handler.handle_message(
            chat_id,
            sender_id,
            text,
            other_mentions if other_mentions else None
        )

        # 如果有回复内容，发送回复
        if reply:
            print(f"[DEBUG] Sending reply: {reply}")
            lark_client.send_message_to_chat(chat_id, reply)

    except Exception as e:
        import traceback
        print(f"Error handling message: {e}")
        traceback.print_exc()


# 创建事件处理器
lark_event_handler = lark.EventDispatcherHandler.builder(
    Config.LARK_ENCRYPT_KEY or "",
    Config.LARK_VERIFICATION_TOKEN or ""
).register_p2_im_message_receive_v1(handle_im_message).build()


@app.route("/api/trigger", methods=["POST"])
def trigger_report():
    """手动触发周报创建（用于测试）"""
    target_date = LarkClient.get_next_wednesday()
    result = report_service.get_or_create_weekly_report(target_date)
    if result:
        return jsonify({"success": True, "doc_url": result["doc_url"]})
    return jsonify({"success": False})


@app.route("/api/status", methods=["GET"])
def get_status():
    """获取当前状态"""
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


def start_flask():
    """启动 Flask API 服务"""
    app.run(host="0.0.0.0", port=8080, debug=False, use_reloader=False)


def start_lark_ws():
    """启动飞书长连接"""
    cli = lark.ws.Client(
        Config.LARK_APP_ID,
        Config.LARK_APP_SECRET,
        event_handler=lark_event_handler,
        log_level=lark.LogLevel.DEBUG
    )
    cli.start()


def main():
    """主函数"""
    print(f"Starting Weekly Report Bot v{__version__}...")

    # 启动定时任务
    scheduler.start()
    print("Scheduler started: Weekly report at Tuesday 11:00")

    # 在单独线程启动 Flask（用于 API）
    flask_thread = threading.Thread(target=start_flask, daemon=True)
    flask_thread.start()
    print("Flask API started on port 8080")

    # 启动飞书长连接（主线程，阻塞）
    print("Starting Lark WebSocket connection...")
    start_lark_ws()


if __name__ == "__main__":
    main()
