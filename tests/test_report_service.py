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
