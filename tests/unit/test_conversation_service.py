"""Tests for conversation_service module."""

import json
import os

import boto3
import pytest
from moto import mock_aws

from services.conversation_service import ConversationService


@pytest.fixture
def aws_env(monkeypatch):
    monkeypatch.setenv("AWS_REGION", "ap-northeast-1")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "ap-northeast-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")


@pytest.fixture
def conversations_table(aws_env):
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="ap-northeast-1")
        table = dynamodb.create_table(
            TableName="test-conversations",
            KeySchema=[
                {"AttributeName": "user_id", "KeyType": "HASH"},
                {"AttributeName": "thread_ts", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "user_id", "AttributeType": "S"},
                {"AttributeName": "thread_ts", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        table.meta.client.get_waiter("table_exists").wait(TableName="test-conversations")
        yield table


def test_save_and_get_messages(conversations_table):
    with mock_aws():
        # Re-create table inside mock context
        dynamodb = boto3.resource("dynamodb", region_name="ap-northeast-1")
        dynamodb.create_table(
            TableName="test-conv",
            KeySchema=[
                {"AttributeName": "user_id", "KeyType": "HASH"},
                {"AttributeName": "thread_ts", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "user_id", "AttributeType": "S"},
                {"AttributeName": "thread_ts", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        service = ConversationService(table_name="test-conv")
        messages = [{"role": "user", "content": "Hello"}]

        service.save_messages("U123", "1234.5678", messages)
        result = service.get_messages("U123", "1234.5678")

        assert result == messages


def test_get_messages_empty(conversations_table):
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="ap-northeast-1")
        dynamodb.create_table(
            TableName="test-conv2",
            KeySchema=[
                {"AttributeName": "user_id", "KeyType": "HASH"},
                {"AttributeName": "thread_ts", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "user_id", "AttributeType": "S"},
                {"AttributeName": "thread_ts", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        service = ConversationService(table_name="test-conv2")
        result = service.get_messages("U999", "9999.9999")
        assert result == []


def test_append_message(conversations_table):
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="ap-northeast-1")
        dynamodb.create_table(
            TableName="test-conv3",
            KeySchema=[
                {"AttributeName": "user_id", "KeyType": "HASH"},
                {"AttributeName": "thread_ts", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "user_id", "AttributeType": "S"},
                {"AttributeName": "thread_ts", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        service = ConversationService(table_name="test-conv3")

        msgs = service.append_message("U123", "1234.5678", "user", "Hello")
        assert len(msgs) == 1
        assert msgs[0]["role"] == "user"

        msgs = service.append_message("U123", "1234.5678", "assistant", "Hi there")
        assert len(msgs) == 2
        assert msgs[1]["role"] == "assistant"


def test_clear_conversation(conversations_table):
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="ap-northeast-1")
        dynamodb.create_table(
            TableName="test-conv4",
            KeySchema=[
                {"AttributeName": "user_id", "KeyType": "HASH"},
                {"AttributeName": "thread_ts", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "user_id", "AttributeType": "S"},
                {"AttributeName": "thread_ts", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        service = ConversationService(table_name="test-conv4")
        service.save_messages("U123", "1234.5678", [{"role": "user", "content": "test"}])
        service.clear_conversation("U123", "1234.5678")

        result = service.get_messages("U123", "1234.5678")
        assert result == []
