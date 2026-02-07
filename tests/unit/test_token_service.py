"""Tests for token_service module."""

import json
from unittest.mock import MagicMock, patch

import boto3
import pytest
from moto import mock_aws

from services.token_service import TokenService


@pytest.fixture
def aws_env(monkeypatch):
    monkeypatch.setenv("AWS_REGION", "ap-northeast-1")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "ap-northeast-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")


@mock_aws
def test_save_and_get_credentials(aws_env):
    dynamodb = boto3.resource("dynamodb", region_name="ap-northeast-1")
    dynamodb.create_table(
        TableName="test-tokens",
        KeySchema=[{"AttributeName": "user_id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "user_id", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )

    service = TokenService(table_name="test-tokens")

    mock_creds = MagicMock()
    mock_creds.token = "access-token"
    mock_creds.refresh_token = "refresh-token"
    mock_creds.token_uri = "https://oauth2.googleapis.com/token"
    mock_creds.client_id = "client-id"
    mock_creds.client_secret = "client-secret"
    mock_creds.scopes = ["https://www.googleapis.com/auth/calendar"]

    service.save_credentials("U123", mock_creds)

    # Verify data was saved
    table = dynamodb.Table("test-tokens")
    response = table.get_item(Key={"user_id": "U123"})
    assert "Item" in response
    token_data = json.loads(response["Item"]["token_data"])
    assert token_data["token"] == "access-token"
    assert token_data["refresh_token"] == "refresh-token"


@mock_aws
def test_get_credentials_returns_none_for_unknown_user(aws_env):
    dynamodb = boto3.resource("dynamodb", region_name="ap-northeast-1")
    dynamodb.create_table(
        TableName="test-tokens2",
        KeySchema=[{"AttributeName": "user_id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "user_id", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )

    service = TokenService(table_name="test-tokens2")
    result = service.get_credentials("UUNKNOWN")
    assert result is None


@mock_aws
def test_delete_credentials(aws_env):
    dynamodb = boto3.resource("dynamodb", region_name="ap-northeast-1")
    dynamodb.create_table(
        TableName="test-tokens3",
        KeySchema=[{"AttributeName": "user_id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "user_id", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )

    service = TokenService(table_name="test-tokens3")

    # Save then delete
    mock_creds = MagicMock()
    mock_creds.token = "token"
    mock_creds.refresh_token = "refresh"
    mock_creds.token_uri = "uri"
    mock_creds.client_id = "id"
    mock_creds.client_secret = "secret"
    mock_creds.scopes = ["scope"]

    service.save_credentials("U123", mock_creds)
    service.delete_credentials("U123")

    result = service.get_credentials("U123")
    assert result is None


@patch("services.token_service.get_google_secrets")
@patch("google_auth_oauthlib.flow.Flow.from_client_config")
def test_get_oauth_url(mock_from_config, mock_secrets, aws_env):
    mock_secrets.return_value = {
        "client_id": "test-client-id",
        "client_secret": "test-client-secret",
    }

    mock_flow = MagicMock()
    mock_from_config.return_value = mock_flow
    mock_flow.authorization_url.return_value = ("https://accounts.google.com/o/oauth2/auth?...", "state")

    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="ap-northeast-1")
        dynamodb.create_table(
            TableName="test-tokens4",
            KeySchema=[{"AttributeName": "user_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "user_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )

        service = TokenService(table_name="test-tokens4")
        url = service.get_oauth_url("U123", "https://example.com/callback")

        assert "accounts.google.com" in url
        mock_flow.authorization_url.assert_called_once()
