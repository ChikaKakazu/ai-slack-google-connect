"""Tests for interactive_handler module."""

import json
from unittest.mock import MagicMock, patch

import pytest


class TestHandleConfirmSlot:
    @patch("handlers.interactive_handler.build_slot_confirmation_modal")
    def test_opens_modal(self, mock_build_modal):
        from handlers.interactive_handler import _handle_confirm_slot

        mock_build_modal.return_value = {"type": "modal"}

        ack = MagicMock()
        say = MagicMock()
        client = MagicMock()
        body = {
            "user": {"id": "U123"},
            "channel": {"id": "C123"},
            "trigger_id": "trigger123",
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
        client.views_open.assert_called_once_with(
            trigger_id="trigger123", view={"type": "modal"}
        )

    def test_invalid_action_value(self):
        from handlers.interactive_handler import _handle_confirm_slot

        ack = MagicMock()
        say = MagicMock()
        client = MagicMock()
        body = {
            "user": {"id": "U123"},
            "channel": {"id": "C123"},
            "trigger_id": "trigger123",
            "actions": [{"value": "invalid-json"}],
            "message": {"ts": "1234.5678"},
        }

        _handle_confirm_slot(ack, body, client, say)
        ack.assert_called_once()
        say.assert_called_once()
        assert "エラー" in say.call_args[1]["text"]

    def test_no_trigger_id(self):
        from handlers.interactive_handler import _handle_confirm_slot

        ack = MagicMock()
        say = MagicMock()
        client = MagicMock()
        body = {
            "user": {"id": "U123"},
            "channel": {"id": "C123"},
            "actions": [{"value": json.dumps({
                "start": "2024-01-15T14:00:00+09:00",
                "end": "2024-01-15T14:30:00+09:00",
                "attendees": ["a@test.com"],
            })}],
            "message": {"ts": "1234.5678"},
        }

        _handle_confirm_slot(ack, body, client, say)
        ack.assert_called_once()
        say.assert_called_once()
        assert "モーダル" in say.call_args[1]["text"]


class TestHandleSlotModalSubmit:
    @patch("handlers.interactive_handler.CalendarService")
    @patch("handlers.interactive_handler.token_service")
    def test_successful_event_creation(self, mock_token_service, mock_cal_cls):
        from handlers.interactive_handler import _handle_slot_modal_submit

        mock_token_service.get_credentials.return_value = MagicMock()
        mock_cal = MagicMock()
        mock_cal_cls.return_value = mock_cal
        mock_cal.create_event.return_value = {
            "id": "event123",
            "summary": "カスタムMTG",
            "start": {"dateTime": "2024-01-15T14:00:00+09:00"},
            "end": {"dateTime": "2024-01-15T14:30:00+09:00"},
            "attendees": [{"email": "a@test.com"}],
            "htmlLink": "https://calendar.google.com/event/123",
        }

        ack = MagicMock()
        client = MagicMock()
        body = {"user": {"id": "U123"}}
        view = {
            "private_metadata": json.dumps({
                "start": "2024-01-15T14:00:00+09:00",
                "end": "2024-01-15T14:30:00+09:00",
                "attendees": ["a@test.com"],
                "channel_id": "C123",
                "message_ts": "1234.5678",
            }),
            "state": {
                "values": {
                    "summary_block": {
                        "summary_input": {"value": "カスタムMTG"}
                    }
                }
            },
        }

        _handle_slot_modal_submit(ack, body, client, view)
        ack.assert_called_once()
        mock_cal.create_event.assert_called_once()
        assert mock_cal.create_event.call_args[1]["summary"] == "カスタムMTG"
        client.chat_update.assert_called_once()

    @patch("handlers.interactive_handler.token_service")
    def test_no_credentials_sends_error(self, mock_token_service):
        from handlers.interactive_handler import _handle_slot_modal_submit

        mock_token_service.get_credentials.return_value = None

        ack = MagicMock()
        client = MagicMock()
        body = {"user": {"id": "U123"}}
        view = {
            "private_metadata": json.dumps({
                "start": "2024-01-15T14:00:00+09:00",
                "end": "2024-01-15T14:30:00+09:00",
                "attendees": ["a@test.com"],
                "channel_id": "C123",
                "message_ts": "1234.5678",
            }),
            "state": {
                "values": {
                    "summary_block": {
                        "summary_input": {"value": "MTG"}
                    }
                }
            },
        }

        _handle_slot_modal_submit(ack, body, client, view)
        ack.assert_called_once()
        client.chat_postMessage.assert_called_once()
        assert "認証" in client.chat_postMessage.call_args[1]["text"]

    @patch("handlers.interactive_handler.CalendarService")
    @patch("handlers.interactive_handler.token_service")
    def test_calendar_error_sends_message(self, mock_token_service, mock_cal_cls):
        from handlers.interactive_handler import _handle_slot_modal_submit

        mock_token_service.get_credentials.return_value = MagicMock()
        mock_cal = MagicMock()
        mock_cal_cls.return_value = mock_cal
        mock_cal.create_event.side_effect = Exception("API error")

        ack = MagicMock()
        client = MagicMock()
        body = {"user": {"id": "U123"}}
        view = {
            "private_metadata": json.dumps({
                "start": "2024-01-15T14:00:00+09:00",
                "end": "2024-01-15T14:30:00+09:00",
                "attendees": ["a@test.com"],
                "channel_id": "C123",
                "message_ts": "1234.5678",
            }),
            "state": {
                "values": {
                    "summary_block": {
                        "summary_input": {"value": "MTG"}
                    }
                }
            },
        }

        _handle_slot_modal_submit(ack, body, client, view)
        ack.assert_called_once()
        client.chat_postMessage.assert_called_once()
        assert "エラー" in client.chat_postMessage.call_args[1]["text"]


class TestHandleConfirmReschedule:
    @patch("handlers.interactive_handler.token_service")
    def test_no_credentials_sends_error(self, mock_token_service):
        from handlers.interactive_handler import _handle_confirm_reschedule

        mock_token_service.get_credentials.return_value = None

        ack = MagicMock()
        say = MagicMock()
        client = MagicMock()
        body = {
            "user": {"id": "U123"},
            "channel": {"id": "C123"},
            "actions": [{"value": json.dumps({
                "action": "confirm_reschedule",
                "event_id": "event123",
                "start": "2024-01-15T10:00:00+09:00",
                "end": "2024-01-15T11:00:00+09:00",
                "summary": "MTG",
            })}],
            "message": {"ts": "1234.5678"},
        }

        _handle_confirm_reschedule(ack, body, client, say)
        ack.assert_called_once()
        say.assert_called_once()
        assert "認証" in say.call_args[1]["text"]

    @patch("handlers.interactive_handler.CalendarService")
    @patch("handlers.interactive_handler.token_service")
    def test_successful_reschedule(self, mock_token_service, mock_cal_cls):
        from handlers.interactive_handler import _handle_confirm_reschedule

        mock_token_service.get_credentials.return_value = MagicMock()
        mock_cal = MagicMock()
        mock_cal_cls.return_value = mock_cal
        mock_cal.reschedule_event.return_value = {
            "id": "event123",
            "summary": "MTG",
            "start": {"dateTime": "2024-01-15T10:00:00+09:00"},
            "end": {"dateTime": "2024-01-15T11:00:00+09:00"},
            "attendees": [{"email": "a@test.com"}],
            "htmlLink": "https://calendar.google.com/event/123",
        }

        ack = MagicMock()
        say = MagicMock()
        client = MagicMock()
        client.users_lookupByEmail.return_value = {"user": {"id": "U999"}}
        body = {
            "user": {"id": "U123"},
            "channel": {"id": "C123"},
            "actions": [{"value": json.dumps({
                "action": "confirm_reschedule",
                "event_id": "event123",
                "start": "2024-01-15T10:00:00+09:00",
                "end": "2024-01-15T11:00:00+09:00",
                "summary": "MTG",
            })}],
            "message": {"ts": "1234.5678"},
        }

        _handle_confirm_reschedule(ack, body, client, say)
        ack.assert_called_once()
        client.chat_update.assert_called_once()
        # Verify mention is posted as a new thread message
        client.chat_postMessage.assert_called_once()
        mention_kwargs = client.chat_postMessage.call_args[1]
        assert mention_kwargs["thread_ts"] == "1234.5678"
        assert "<@U999>" in mention_kwargs["text"]

    def test_invalid_action_value(self):
        from handlers.interactive_handler import _handle_confirm_reschedule

        ack = MagicMock()
        say = MagicMock()
        client = MagicMock()
        body = {
            "user": {"id": "U123"},
            "channel": {"id": "C123"},
            "actions": [{"value": "invalid-json"}],
            "message": {"ts": "1234.5678"},
        }

        _handle_confirm_reschedule(ack, body, client, say)
        ack.assert_called_once()
        say.assert_called_once()
        assert "エラー" in say.call_args[1]["text"]


class TestHandleConfirmCreate:
    @patch("handlers.interactive_handler.build_create_confirmation_modal")
    def test_opens_modal(self, mock_build_modal):
        from handlers.interactive_handler import _handle_confirm_create

        mock_build_modal.return_value = {"type": "modal"}

        ack = MagicMock()
        say = MagicMock()
        client = MagicMock()
        body = {
            "user": {"id": "U123"},
            "channel": {"id": "C123"},
            "trigger_id": "trigger123",
            "actions": [{"value": json.dumps({
                "action": "confirm_create",
                "summary": "MTG",
                "start_time": "2024-01-15T14:00:00+09:00",
                "end_time": "2024-01-15T14:30:00+09:00",
                "attendees": ["a@test.com"],
                "description": "",
            })}],
            "message": {"ts": "1234.5678"},
        }

        _handle_confirm_create(ack, body, client, say)
        ack.assert_called_once()
        client.views_open.assert_called_once_with(
            trigger_id="trigger123", view={"type": "modal"}
        )

    def test_invalid_action_value(self):
        from handlers.interactive_handler import _handle_confirm_create

        ack = MagicMock()
        say = MagicMock()
        client = MagicMock()
        body = {
            "user": {"id": "U123"},
            "channel": {"id": "C123"},
            "actions": [{"value": "invalid-json"}],
            "message": {"ts": "1234.5678"},
        }

        _handle_confirm_create(ack, body, client, say)
        ack.assert_called_once()
        say.assert_called_once()
        assert "エラー" in say.call_args[1]["text"]

    def test_no_trigger_id(self):
        from handlers.interactive_handler import _handle_confirm_create

        ack = MagicMock()
        say = MagicMock()
        client = MagicMock()
        body = {
            "user": {"id": "U123"},
            "channel": {"id": "C123"},
            "actions": [{"value": json.dumps({
                "summary": "MTG",
                "start_time": "2024-01-15T14:00:00+09:00",
                "end_time": "2024-01-15T14:30:00+09:00",
            })}],
            "message": {"ts": "1234.5678"},
        }

        _handle_confirm_create(ack, body, client, say)
        ack.assert_called_once()
        say.assert_called_once()
        assert "モーダル" in say.call_args[1]["text"]


class TestHandleCreateModalSubmit:
    @patch("handlers.interactive_handler.CalendarService")
    @patch("handlers.interactive_handler.token_service")
    def test_successful_event_creation(self, mock_token_service, mock_cal_cls):
        from handlers.interactive_handler import _handle_create_modal_submit

        mock_token_service.get_credentials.return_value = MagicMock()
        mock_cal = MagicMock()
        mock_cal_cls.return_value = mock_cal
        mock_cal.create_event.return_value = {
            "id": "event123",
            "summary": "カスタムMTG",
            "start": {"dateTime": "2024-01-15T14:00:00+09:00"},
            "end": {"dateTime": "2024-01-15T14:30:00+09:00"},
            "attendees": [{"email": "a@test.com"}],
            "htmlLink": "https://calendar.google.com/event/123",
        }

        ack = MagicMock()
        client = MagicMock()
        body = {"user": {"id": "U123"}}
        view = {
            "private_metadata": json.dumps({
                "start_time": "2024-01-15T14:00:00+09:00",
                "end_time": "2024-01-15T14:30:00+09:00",
                "attendees": ["a@test.com"],
                "description": "テスト",
                "channel_id": "C123",
                "message_ts": "1234.5678",
            }),
            "state": {
                "values": {
                    "summary_block": {
                        "summary_input": {"value": "カスタムMTG"}
                    }
                }
            },
        }

        _handle_create_modal_submit(ack, body, client, view)
        ack.assert_called_once()
        mock_cal.create_event.assert_called_once()
        assert mock_cal.create_event.call_args[1]["summary"] == "カスタムMTG"
        assert mock_cal.create_event.call_args[1]["description"] == "テスト"
        client.chat_update.assert_called_once()

    @patch("handlers.interactive_handler.token_service")
    def test_no_credentials_sends_error(self, mock_token_service):
        from handlers.interactive_handler import _handle_create_modal_submit

        mock_token_service.get_credentials.return_value = None

        ack = MagicMock()
        client = MagicMock()
        body = {"user": {"id": "U123"}}
        view = {
            "private_metadata": json.dumps({
                "start_time": "2024-01-15T14:00:00+09:00",
                "end_time": "2024-01-15T14:30:00+09:00",
                "attendees": ["a@test.com"],
                "channel_id": "C123",
                "message_ts": "1234.5678",
            }),
            "state": {
                "values": {
                    "summary_block": {
                        "summary_input": {"value": "MTG"}
                    }
                }
            },
        }

        _handle_create_modal_submit(ack, body, client, view)
        ack.assert_called_once()
        client.chat_postMessage.assert_called_once()
        assert "認証" in client.chat_postMessage.call_args[1]["text"]

    @patch("handlers.interactive_handler.CalendarService")
    @patch("handlers.interactive_handler.token_service")
    def test_calendar_error_sends_message(self, mock_token_service, mock_cal_cls):
        from handlers.interactive_handler import _handle_create_modal_submit

        mock_token_service.get_credentials.return_value = MagicMock()
        mock_cal = MagicMock()
        mock_cal_cls.return_value = mock_cal
        mock_cal.create_event.side_effect = Exception("API error")

        ack = MagicMock()
        client = MagicMock()
        body = {"user": {"id": "U123"}}
        view = {
            "private_metadata": json.dumps({
                "start_time": "2024-01-15T14:00:00+09:00",
                "end_time": "2024-01-15T14:30:00+09:00",
                "attendees": ["a@test.com"],
                "channel_id": "C123",
                "message_ts": "1234.5678",
            }),
            "state": {
                "values": {
                    "summary_block": {
                        "summary_input": {"value": "MTG"}
                    }
                }
            },
        }

        _handle_create_modal_submit(ack, body, client, view)
        ack.assert_called_once()
        client.chat_postMessage.assert_called_once()
        assert "エラー" in client.chat_postMessage.call_args[1]["text"]


class TestHandleOAuthButton:
    def test_acknowledges(self):
        from handlers.interactive_handler import _handle_oauth_button

        ack = MagicMock()
        body = {}
        _handle_oauth_button(ack, body)
        ack.assert_called_once()
