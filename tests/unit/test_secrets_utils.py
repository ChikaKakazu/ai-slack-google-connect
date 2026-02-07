"""Tests for secrets_utils module."""

import json
import os

import boto3
import pytest
from moto import mock_aws

from utils.secrets_utils import clear_cache, get_secret, get_slack_secrets


@pytest.fixture(autouse=True)
def _clear_secrets_cache():
    clear_cache()
    yield
    clear_cache()


@pytest.fixture
def aws_env(monkeypatch):
    monkeypatch.setenv("AWS_REGION", "ap-northeast-1")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "ap-northeast-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")


@mock_aws
def test_get_secret(aws_env):
    client = boto3.client("secretsmanager", region_name="ap-northeast-1")
    secret_value = {"bot_token": "xoxb-test", "signing_secret": "test-secret"}
    client.create_secret(
        Name="test-secret",
        SecretString=json.dumps(secret_value),
    )

    result = get_secret("test-secret")
    assert result == secret_value


@mock_aws
def test_get_secret_caches(aws_env):
    client = boto3.client("secretsmanager", region_name="ap-northeast-1")
    client.create_secret(
        Name="cached-secret",
        SecretString=json.dumps({"key": "value"}),
    )

    result1 = get_secret("cached-secret")
    result2 = get_secret("cached-secret")
    assert result1 is result2  # Same object from cache


@mock_aws
def test_get_slack_secrets(aws_env, monkeypatch):
    monkeypatch.setenv("SECRETS_NAME", "slack-secrets")

    client = boto3.client("secretsmanager", region_name="ap-northeast-1")
    client.create_secret(
        Name="slack-secrets",
        SecretString=json.dumps({"bot_token": "xoxb-test", "signing_secret": "sign"}),
    )

    result = get_slack_secrets()
    assert result["bot_token"] == "xoxb-test"
    assert result["signing_secret"] == "sign"
