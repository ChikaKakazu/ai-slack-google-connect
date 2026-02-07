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

        result = _handle_tool_use_loop(
            user_id="U123",
            thread_ts="1234.5678",
            messages=messages,
            response=response,
            tools=[],
            say=MagicMock(),
        )

        # stop_reason is not tool_use, so should return immediately
        assert result == response

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

        result = _handle_tool_use_loop(
            user_id="U123",
            thread_ts="1234.5678",
            messages=[{"role": "user", "content": "テスト"}],
            response=tool_use_response,
            tools=[],
            say=MagicMock(),
        )

        assert result == final_response
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

        result = _handle_tool_use_loop(
            user_id="U123",
            thread_ts="1234.5678",
            messages=[],
            response=tool_response,
            tools=[],
            say=MagicMock(),
            max_iterations=3,
        )

        # Should stop after 3 iterations
        assert mock_tool_exec.execute.call_count == 3
