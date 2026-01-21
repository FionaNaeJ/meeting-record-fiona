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
