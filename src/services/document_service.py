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

        # 授予目标群组编辑权限
        if Config.TARGET_CHAT_ID:
            self.lark.grant_document_permission(
                doc_token=doc_token,
                doc_type="docx",
                member_id=Config.TARGET_CHAT_ID,
                member_type="openchat",
                perm="edit"
            )
            print(f"[DocumentService] Granted edit permission to chat: {Config.TARGET_CHAT_ID}")

        return {"doc_token": doc_token, "doc_url": doc_url}

    def get_document_url(self, doc_token: str) -> str:
        """生成文档的访问 URL"""
        return f"https://bytedance.larkoffice.com/docx/{doc_token}"
