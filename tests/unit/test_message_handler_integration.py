"""Integration-level tests for message_handler with mocked services."""

import json
from unittest.mock import MagicMock, patch

import pytest


class TestHandleMention:
    @patch("handlers.message_handler.tool_executor")
    @patch("handlers.message_handler.conversation")
    @patch("handlers.message_handler.bedrock")
    def test_empty_message_returns_help(self, mock_bedrock, mock_conv, mock_tool_exec):
        from handlers.message_handler import register_message_handlers

        app = MagicMock()
        register_message_handlers(app)

        # Get the registered handler
        handler_func = app.event.call_args[0][0] if app.event.call_args else None
        # Access via decorator - get the actual function
        mention_handler = app.event("app_mention").__enter__()

    @patch("handlers.message_handler.tool_executor")
    @patch("handlers.message_handler.conversation")
    @patch("handlers.message_handler.bedrock")
    def test_mention_invokes_bedrock(self, mock_bedrock, mock_conv, mock_tool_exec):
        mock_conv.append_message.return_value = [{"role": "user", "content": "テスト"}]
        mock_bedrock.invoke.return_value = {
            "content": [{"type": "text", "text": "テスト応答"}],
            "stop_reason": "end_turn",
        }
        mock_bedrock.extract_text_response.return_value = "テスト応答"
        mock_bedrock.extract_tool_use.return_value = []

        # Import the internal function for direct testing
        from handlers.message_handler import _handle_tool_use_loop

        messages = [{"role": "user", "content": "テスト"}]
        response = {
            "content": [{"type": "text", "text": "応答"}],
            "stop_reason": "end_turn",
        }

        result, oauth_sent = _handle_tool_use_loop(
            user_id="U123",
            thread_ts="1234.5678",
            channel_id="C001",
            original_text="テスト",
            messages=messages,
            response=response,
            tools=[],
            say=MagicMock(),
        )

        # stop_reason is not tool_use, so should return immediately
        assert result == response
        assert oauth_sent is False

    @patch("handlers.message_handler.tool_executor")
    @patch("handlers.message_handler.conversation")
    @patch("handlers.message_handler.bedrock")
    def test_tool_use_loop_executes_tools(self, mock_bedrock, mock_conv, mock_tool_exec):
        # First response: tool use
        tool_use_response = {
            "content": [
                {"type": "text", "text": "検索します"},
                {"type": "tool_use", "id": "t1", "name": "search_free_slots", "input": {"attendees": ["a@test.com"], "date": "明日"}},
            ],
            "stop_reason": "tool_use",
        }

        # Second response: final text
        final_response = {
            "content": [{"type": "text", "text": "候補が見つかりました"}],
            "stop_reason": "end_turn",
        }

        mock_bedrock.extract_tool_use.return_value = [
            {"type": "tool_use", "id": "t1", "name": "search_free_slots", "input": {"attendees": ["a@test.com"], "date": "明日"}},
        ]
        mock_bedrock.invoke.return_value = final_response
        mock_tool_exec.execute.return_value = json.dumps({"slots": [], "total_slots": 0})

        from handlers.message_handler import _handle_tool_use_loop

        result, oauth_sent = _handle_tool_use_loop(
            user_id="U123",
            thread_ts="1234.5678",
            channel_id="C001",
            original_text="テスト",
            messages=[{"role": "user", "content": "テスト"}],
            response=tool_use_response,
            tools=[],
            say=MagicMock(),
        )

        assert result == final_response
        assert oauth_sent is False
        mock_tool_exec.execute.assert_called_once()
        mock_bedrock.invoke.assert_called_once()

    @patch("handlers.message_handler.tool_executor")
    @patch("handlers.message_handler.conversation")
    @patch("handlers.message_handler.bedrock")
    def test_tool_use_loop_max_iterations(self, mock_bedrock, mock_conv, mock_tool_exec):
        # Always return tool_use
        tool_response = {
            "content": [
                {"type": "tool_use", "id": "t1", "name": "search", "input": {}},
            ],
            "stop_reason": "tool_use",
        }

        mock_bedrock.extract_tool_use.return_value = [
            {"type": "tool_use", "id": "t1", "name": "search", "input": {}},
        ]
        mock_bedrock.invoke.return_value = tool_response
        mock_tool_exec.execute.return_value = json.dumps({"result": "ok"})

        from handlers.message_handler import _handle_tool_use_loop

        result, oauth_sent = _handle_tool_use_loop(
            user_id="U123",
            thread_ts="1234.5678",
            channel_id="C001",
            original_text="テスト",
            messages=[],
            response=tool_response,
            tools=[],
            say=MagicMock(),
            max_iterations=3,
        )

        # Should stop after 3 iterations
        assert mock_tool_exec.execute.call_count == 3

    @patch("handlers.message_handler.tool_executor")
    @patch("handlers.message_handler.conversation")
    @patch("handlers.message_handler.bedrock")
    def test_suggest_reschedule_sends_blocks(self, mock_bedrock, mock_conv, mock_tool_exec):
        tool_use_response = {
            "content": [
                {"type": "tool_use", "id": "t1", "name": "suggest_reschedule", "input": {"event_id": "event123"}},
            ],
            "stop_reason": "tool_use",
        }

        mock_bedrock.extract_tool_use.return_value = [
            {"type": "tool_use", "id": "t1", "name": "suggest_reschedule", "input": {"event_id": "event123"}},
        ]
        mock_tool_exec.execute.return_value = json.dumps({
            "status": "suggest_reschedule",
            "event_id": "event123",
            "summary": "定例MTG",
            "original_start": "2024-01-15T14:00:00+09:00",
            "original_end": "2024-01-15T15:00:00+09:00",
            "attendees": ["a@test.com"],
            "duration_minutes": 60,
            "candidates": [
                {"start": "2024-01-15T10:00:00+09:00", "end": "2024-01-15T11:00:00+09:00"},
            ],
            "searched_date": "2024-01-15",
            "fallback_used": False,
        })

        from handlers.message_handler import _handle_tool_use_loop

        say = MagicMock()
        result, oauth_sent = _handle_tool_use_loop(
            user_id="U123",
            thread_ts="1234.5678",
            channel_id="C001",
            original_text="このMTGをリスケして",
            messages=[{"role": "user", "content": "このMTGをリスケして"}],
            response=tool_use_response,
            tools=[],
            say=say,
        )

        assert oauth_sent is True  # Blocks are sent directly, so returns True
        say.assert_called_once()
        call_kwargs = say.call_args[1]
        assert "blocks" in call_kwargs

    @patch("handlers.message_handler.tool_executor")
    @patch("handlers.message_handler.conversation")
    @patch("handlers.message_handler.bedrock")
    def test_suggest_reschedule_no_slots_sends_text(self, mock_bedrock, mock_conv, mock_tool_exec):
        tool_use_response = {
            "content": [
                {"type": "tool_use", "id": "t1", "name": "suggest_reschedule", "input": {"event_id": "event123"}},
            ],
            "stop_reason": "tool_use",
        }

        mock_bedrock.extract_tool_use.return_value = [
            {"type": "tool_use", "id": "t1", "name": "suggest_reschedule", "input": {"event_id": "event123"}},
        ]
        mock_tool_exec.execute.return_value = json.dumps({
            "status": "suggest_reschedule",
            "no_slots_found": True,
            "event_id": "event123",
            "summary": "定例MTG",
            "attendees": ["a@test.com"],
            "duration_minutes": 60,
            "searched_date": "2024-01-15",
        })

        from handlers.message_handler import _handle_tool_use_loop

        say = MagicMock()
        result, oauth_sent = _handle_tool_use_loop(
            user_id="U123",
            thread_ts="1234.5678",
            channel_id="C001",
            original_text="このMTGをリスケして",
            messages=[{"role": "user", "content": "このMTGをリスケして"}],
            response=tool_use_response,
            tools=[],
            say=say,
        )

        assert oauth_sent is True
        say.assert_called_once()
        call_kwargs = say.call_args[1]
        assert "blocks" not in call_kwargs
        assert "見つかりませんでした" in call_kwargs["text"]

    @patch("handlers.message_handler.tool_executor")
    @patch("handlers.message_handler.conversation")
    @patch("handlers.message_handler.bedrock")
    def test_suggest_schedule_sends_blocks(self, mock_bedrock, mock_conv, mock_tool_exec):
        tool_use_response = {
            "content": [
                {"type": "tool_use", "id": "t1", "name": "search_free_slots", "input": {"attendees": ["a@test.com"]}},
            ],
            "stop_reason": "tool_use",
        }

        mock_bedrock.extract_tool_use.return_value = [
            {"type": "tool_use", "id": "t1", "name": "search_free_slots", "input": {"attendees": ["a@test.com"]}},
        ]
        mock_tool_exec.execute.return_value = json.dumps({
            "status": "suggest_schedule",
            "slots": [
                {"start": "2024-01-15T14:00:00+09:00", "end": "2024-01-15T15:00:00+09:00"},
            ],
            "attendees": ["a@test.com"],
            "summary": "ミーティング",
            "duration_minutes": 60,
            "date": "2024-01-15",
            "total_slots": 1,
        })

        from handlers.message_handler import _handle_tool_use_loop

        say = MagicMock()
        result, oauth_sent = _handle_tool_use_loop(
            user_id="U123",
            thread_ts="1234.5678",
            channel_id="C001",
            original_text="明日の空き時間を探して",
            messages=[{"role": "user", "content": "明日の空き時間を探して"}],
            response=tool_use_response,
            tools=[],
            say=say,
        )

        assert oauth_sent is True
        say.assert_called_once()
        call_kwargs = say.call_args[1]
        assert "blocks" in call_kwargs

    @patch("handlers.message_handler.tool_executor")
    @patch("handlers.message_handler.conversation")
    @patch("handlers.message_handler.bedrock")
    def test_suggest_schedule_warning_sends_text(self, mock_bedrock, mock_conv, mock_tool_exec):
        tool_use_response = {
            "content": [
                {"type": "tool_use", "id": "t1", "name": "search_free_slots", "input": {"attendees": ["a@test.com"]}},
            ],
            "stop_reason": "tool_use",
        }

        mock_bedrock.extract_tool_use.return_value = [
            {"type": "tool_use", "id": "t1", "name": "search_free_slots", "input": {"attendees": ["a@test.com"]}},
        ]
        mock_tool_exec.execute.return_value = json.dumps({
            "status": "suggest_schedule",
            "warning": "土曜日 は営業日外（土日祝）です。営業日を指定してください。",
            "slots": [],
            "attendees": ["a@test.com"],
            "summary": "ミーティング",
            "duration_minutes": 60,
            "date": "土曜日",
            "total_slots": 0,
        })

        from handlers.message_handler import _handle_tool_use_loop

        say = MagicMock()
        result, oauth_sent = _handle_tool_use_loop(
            user_id="U123",
            thread_ts="1234.5678",
            channel_id="C001",
            original_text="土曜日の空き時間を探して",
            messages=[{"role": "user", "content": "土曜日の空き時間を探して"}],
            response=tool_use_response,
            tools=[],
            say=say,
        )

        assert oauth_sent is True
        say.assert_called_once()
        call_kwargs = say.call_args[1]
        assert "blocks" not in call_kwargs
        assert "営業日外" in call_kwargs["text"]
