"""Tests for app.py Lambda handler."""

from unittest.mock import MagicMock, patch

import pytest


class TestHandler:
    @patch("app.handle_oauth_callback")
    @patch("app._get_handler")
    def test_routes_oauth_callback(self, mock_get_handler, mock_oauth):
        from app import handler

        mock_oauth.return_value = {"statusCode": 200, "body": "OK"}

        event = {
            "rawPath": "/oauth/google/callback",
            "queryStringParameters": {"code": "auth", "state": "U123"},
        }

        result = handler(event, None)
        mock_oauth.assert_called_once_with(event)
        mock_get_handler.assert_not_called()
        assert result["statusCode"] == 200

    @patch("app._get_handler")
    def test_routes_slack_events(self, mock_get_handler):
        from app import handler

        mock_slack_handler = MagicMock()
        mock_slack_handler.handle.return_value = {"statusCode": 200}
        mock_get_handler.return_value = mock_slack_handler

        event = {"rawPath": "/slack/events"}
        result = handler(event, None)

        mock_slack_handler.handle.assert_called_once_with(event, None)

    @patch("app._get_handler")
    def test_routes_slack_interactive(self, mock_get_handler):
        from app import handler

        mock_slack_handler = MagicMock()
        mock_slack_handler.handle.return_value = {"statusCode": 200}
        mock_get_handler.return_value = mock_slack_handler

        event = {"rawPath": "/slack/interactive"}
        result = handler(event, None)

        mock_slack_handler.handle.assert_called_once()
