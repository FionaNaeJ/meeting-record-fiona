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
    from datetime import date
    result = LarkClient.format_date_for_title(date(2026, 1, 21))
    assert result == "2026.1.21"

def test_get_next_wednesday():
    from datetime import date
    # 2026-01-20 是周二
    result = LarkClient.get_next_wednesday(date(2026, 1, 20))
    assert result == date(2026, 1, 21)  # 明天周三

    # 2026-01-21 是周三
    result = LarkClient.get_next_wednesday(date(2026, 1, 21))
    assert result == date(2026, 1, 21)  # 就是今天

    # 2026-01-22 是周四
    result = LarkClient.get_next_wednesday(date(2026, 1, 22))
    assert result == date(2026, 1, 28)  # 下周三
