# src/services/intent_service.py
from __future__ import annotations
import json
import httpx
from typing import Optional, Tuple
from dataclasses import dataclass
from src.config import Config


@dataclass
class Intent:
    type: str  # todo, send_report, skip, cancel_skip, unknown
    content: Optional[str] = None


class IntentService:
    """使用豆包 LLM 识别用户意图"""

    SYSTEM_PROMPT = """你是周报机器人的意图识别器。只返回意图类型，不要提取内容。

意图：
- todo: 包含待办事项（有"todo"、"待办"、"本周"、带序号列表等）
- send_report: 要求发送/查看周报
- skip: 要求跳过周报
- cancel_skip: 取消跳过
- unknown: 无法识别

只返回JSON：{"intent": "xxx"}

示例：
"本周todo：开会" → {"intent": "todo"}
"发一下周报" → {"intent": "send_report"}
"这周跳过" → {"intent": "skip"}
"还是发吧" → {"intent": "cancel_skip"}
"天气真好" → {"intent": "unknown"}"""

    def __init__(self):
        self.api_key = Config.ARK_API_KEY
        self.model = Config.ARK_MODEL_ENDPOINT
        self.base_url = Config.ARK_BASE_URL

    def recognize(self, message: str) -> Intent:
        """识别用户消息的意图"""
        try:
            print(f"[IntentService] Calling LLM with message: {message[:100]}...")
            response = self._call_llm(message)
            print(f"[IntentService] LLM response: {response}")
            return self._parse_response(response)
        except Exception as e:
            import traceback
            print(f"[IntentService] Error: {e}")
            traceback.print_exc()
            return Intent(type="unknown")

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
            "max_tokens": 50,  # 只需返回意图，不需要太长
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
            valid_intents = ["todo", "send_report", "skip", "cancel_skip", "unknown"]
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
