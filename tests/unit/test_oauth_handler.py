"""Tests for oauth_handler module."""

import json
from unittest.mock import MagicMock, patch

import pytest

from handlers.oauth_handler import handle_oauth_callback


class TestHandleOAuthCallback:
    def test_error_param_returns_400(self):
        event = {
            "queryStringParameters": {"error": "access_denied"},
        }
        result = handle_oauth_callback(event)
        assert result["statusCode"] == 400
        assert "キャンセル" in result["body"]

    def test_missing_code_returns_400(self):
        event = {
            "queryStringParameters": {"state": "U123"},
        }
        result = handle_oauth_callback(event)
        assert result["statusCode"] == 400

    def test_missing_state_returns_400(self):
        event = {
            "queryStringParameters": {"code": "auth_code"},
        }
        result = handle_oauth_callback(event)
        assert result["statusCode"] == 400

    def test_none_query_params_returns_400(self):
        event = {"queryStringParameters": None}
        result = handle_oauth_callback(event)
        assert result["statusCode"] == 400

    @patch("handlers.oauth_handler.token_service")
    @patch("handlers.oauth_handler.get_google_secrets")
    @patch("handlers.oauth_handler.Flow")
    def test_successful_oauth(self, mock_flow_cls, mock_get_secrets, mock_token_service):
        mock_get_secrets.return_value = {
            "client_id": "test-client-id",
            "client_secret": "test-client-secret",
        }

        mock_flow = MagicMock()
        mock_flow_cls.from_client_config.return_value = mock_flow
        mock_flow.credentials = MagicMock()

        event = {
            "queryStringParameters": {"code": "auth_code", "state": "U123"},
            "headers": {"host": "api.example.com"},
            "requestContext": {"stage": "$default"},
        }

        result = handle_oauth_callback(event)
        assert result["statusCode"] == 200
        assert "完了" in result["body"]
        mock_token_service.save_credentials.assert_called_once_with("U123", mock_flow.credentials)

    @patch("handlers.oauth_handler.get_google_secrets")
    def test_oauth_exception_returns_500(self, mock_get_secrets):
        mock_get_secrets.side_effect = Exception("Connection error")

        event = {
            "queryStringParameters": {"code": "auth_code", "state": "U123"},
            "headers": {"host": "api.example.com"},
            "requestContext": {"stage": "$default"},
        }

        result = handle_oauth_callback(event)
        assert result["statusCode"] == 500
