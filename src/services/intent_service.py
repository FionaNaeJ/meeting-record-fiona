# src/services/intent_service.py
from __future__ import annotations
import json
import httpx
from typing import Optional
from dataclasses import dataclass
from src.config import Config


@dataclass
class Intent:
    type: str  # todo, send_report, skip, cancel_skip, status, help, unknown
    content: Optional[str] = None


class IntentService:
    """使用豆包 LLM 识别用户意图"""

    SYSTEM_PROMPT = """你是周报机器人的意图识别器。

意图：
- todo: 包含待办事项（有"todo"、"待办"、"本周"、带序号列表等）
- send_report: 要求发送/查看周报
- skip: 要求跳过周报
- cancel_skip: 取消跳过
- unknown: 无法识别

返回JSON：
- 非todo意图：{"intent": "xxx"}
- todo意图：{"intent": "todo", "content": "提取的todo内容"}

提取todo内容时：
- 去掉"todo"、"待办"等前缀词
- 去掉@人的标记
- 保留实际的任务内容

示例：
"本周todo：1. 开会 2. 写文档" → {"intent": "todo", "content": "1. 开会 2. 写文档"}
"todo 完成周报" → {"intent": "todo", "content": "完成周报"}
"发一下周报" → {"intent": "send_report"}
"这周跳过" → {"intent": "skip"}
"天气真好" → {"intent": "unknown"}"""

    def __init__(self):
        self.api_key = Config.ARK_API_KEY
        self.model = Config.ARK_MODEL_ENDPOINT
        self.base_url = Config.ARK_BASE_URL

    def recognize(self, message: str) -> Intent:
        """识别用户消息的意图"""
        if not self.api_key or not self.model or not self.base_url:
            return self._rule_based_recognize(message)
        try:
            print(f"[IntentService] Calling LLM with message: {message[:100]}...")
            response = self._call_llm(message)
            print(f"[IntentService] LLM response: {response}")
            return self._parse_response(response)
        except Exception as e:
            import traceback
            print(f"[IntentService] Error: {e}")
            traceback.print_exc()
            return self._rule_based_recognize(message)

    def _call_llm(self, message: str) -> str:
        """调用豆包 API"""
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": message}
            ],
            "max_tokens": 500,  # 需要返回意图和提取的内容
            "temperature": 0.1  # 低温度，更确定性的输出
        }

        with httpx.Client(timeout=30.0) as client:  # 增加超时时间
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    def _parse_response(self, response: str) -> Intent:
        """解析 LLM 返回的 JSON"""
        try:
            # 尝试直接解析
            data = json.loads(response.strip())
            intent_type = data.get("intent", "unknown")
            content = data.get("content")

            # 验证意图类型
            valid_intents = ["todo", "send_report", "skip", "cancel_skip", "status", "help", "unknown"]
            if intent_type not in valid_intents:
                intent_type = "unknown"

            return Intent(type=intent_type, content=content)
        except json.JSONDecodeError:
            # 如果解析失败，尝试从文本中提取 JSON
            import re
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group())
                    return Intent(
                        type=data.get("intent", "unknown"),
                        content=data.get("content")
                    )
                except:
                    pass
            return Intent(type="unknown")

    def _rule_based_recognize(self, message: str) -> Intent:
        import re
        msg = message.strip()

        if msg in ["跳过本周", "跳过"]:
            return Intent(type="skip")
        if re.match(r'^跳过\s+\d{4}-\d{2}-\d{2}$', msg):
            return Intent(type="skip")

        if msg in ["取消跳过", "恢复本周"]:
            return Intent(type="cancel_skip")
        if re.match(r'^取消跳过\s+\d{4}-\d{2}-\d{2}$', msg):
            return Intent(type="cancel_skip")

        if msg in ["状态", "查看状态", "status"]:
            return Intent(type="status")

        if msg in ["帮助", "help", "?"]:
            return Intent(type="help")

        if "周报" in msg:
            return Intent(type="send_report")

        if re.search(r'[Tt][Oo][Dd][Oo]|待办', msg):
            return Intent(type="todo")

        return Intent(type="unknown")
