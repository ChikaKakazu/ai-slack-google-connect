"""Tests for interactive_handler module."""

import json
from unittest.mock import MagicMock, patch

import pytest


class TestHandleConfirmSlot:
    @patch("handlers.interactive_handler.token_service")
    def test_no_credentials_sends_error(self, mock_token_service):
        from handlers.interactive_handler import _handle_confirm_slot

        mock_token_service.get_credentials.return_value = None

        ack = MagicMock()
        say = MagicMock()
        client = MagicMock()
        body = {
            "user": {"id": "U123"},
            "channel": {"id": "C123"},
            "actions": [{"value": json.dumps({"start": "2024-01-15T14:00:00+09:00", "end": "2024-01-15T14:30:00+09:00", "attendees": ["a@test.com"], "summary": "MTG"})}],
            "message": {"ts": "1234.5678"},
        }

        _handle_confirm_slot(ack, body, client, say)
        ack.assert_called_once()
        say.assert_called_once()
        assert "認証" in say.call_args[1]["text"]

    @patch("handlers.interactive_handler.CalendarService")
    @patch("handlers.interactive_handler.token_service")
    def test_successful_event_creation(self, mock_token_service, mock_cal_cls):
        from handlers.interactive_handler import _handle_confirm_slot

        mock_token_service.get_credentials.return_value = MagicMock()
        mock_cal = MagicMock()
        mock_cal_cls.return_value = mock_cal
        mock_cal.create_event.return_value = {
            "id": "event123",
            "summary": "MTG",
            "start": {"dateTime": "2024-01-15T14:00:00+09:00"},
            "end": {"dateTime": "2024-01-15T14:30:00+09:00"},
            "attendees": [{"email": "a@test.com"}],
            "htmlLink": "https://calendar.google.com/event/123",
        }

        ack = MagicMock()
        say = MagicMock()
        client = MagicMock()
        body = {
            "user": {"id": "U123"},
            "channel": {"id": "C123"},
            "actions": [{"value": json.dumps({
                "action": "confirm_slot",
                "start": "2024-01-15T14:00:00+09:00",
                "end": "2024-01-15T14:30:00+09:00",
                "attendees": ["a@test.com"],
                "summary": "MTG",
            })}],
            "message": {"ts": "1234.5678"},
        }

        _handle_confirm_slot(ack, body, client, say)
        ack.assert_called_once()
        client.chat_update.assert_called_once()

    def test_invalid_action_value(self):
        from handlers.interactive_handler import _handle_confirm_slot

        ack = MagicMock()
        say = MagicMock()
        client = MagicMock()
        body = {
            "user": {"id": "U123"},
            "channel": {"id": "C123"},
            "actions": [{"value": "invalid-json"}],
            "message": {"ts": "1234.5678"},
        }

        _handle_confirm_slot(ack, body, client, say)
        ack.assert_called_once()
        say.assert_called_once()
        assert "エラー" in say.call_args[1]["text"]


class TestHandleOAuthButton:
    def test_acknowledges(self):
        from handlers.interactive_handler import _handle_oauth_button

        ack = MagicMock()
        body = {}
        _handle_oauth_button(ack, body)
        ack.assert_called_once()
