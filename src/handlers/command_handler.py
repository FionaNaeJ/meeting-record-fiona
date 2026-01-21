# src/handlers/command_handler.py
import re
from typing import Tuple, Optional

class CommandHandler:
    @staticmethod
    def parse_command(message: str) -> Tuple[Optional[str], Optional[str]]:
        """
        解析用户命令
        返回: (command_type, argument)
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

        # Todo（模糊匹配：只要包含 todo 或 待办 就识别）
        todo_patterns = [
            r'[Tt][Oo][Dd][Oo][:\s：]*(.+)$',  # todo后面可以没有分隔符
            r'待办[:\s：]*(.+)$',
        ]
        for pattern in todo_patterns:
            match = re.search(pattern, message)
            if match:
                content = match.group(1).strip()
                # 去掉开头的分隔符
                content = re.sub(r'^[:\s：，,]+', '', content)
                if content:
                    return ("todo", content)

        return (None, None)
