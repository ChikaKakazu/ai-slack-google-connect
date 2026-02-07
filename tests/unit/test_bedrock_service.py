"""Tests for bedrock_service module."""

import json
from unittest.mock import MagicMock, patch

import pytest

from services.bedrock_service import BedrockService


@pytest.fixture
def bedrock_service():
    with patch("services.bedrock_service.boto3") as mock_boto3:
        service = BedrockService(model_id="test-model", region="us-east-1")
        yield service, mock_boto3


class TestBedrockService:
    def test_invoke_sends_correct_request(self, bedrock_service):
        service, mock_boto3 = bedrock_service

        mock_body = MagicMock()
        mock_body.read.return_value = json.dumps({
            "content": [{"type": "text", "text": "Hello"}],
            "stop_reason": "end_turn",
        }).encode()

        service.client.invoke_model.return_value = {"body": mock_body}

        messages = [{"role": "user", "content": "Hi"}]
        response = service.invoke(messages=messages)

        service.client.invoke_model.assert_called_once()
        call_kwargs = service.client.invoke_model.call_args[1]
        assert call_kwargs["modelId"] == "test-model"

        body = json.loads(call_kwargs["body"])
        assert body["messages"] == messages
        assert "system" in body

    def test_invoke_with_tools(self, bedrock_service):
        service, _ = bedrock_service

        mock_body = MagicMock()
        mock_body.read.return_value = json.dumps({
            "content": [{"type": "text", "text": "Using tool"}],
            "stop_reason": "tool_use",
        }).encode()

        service.client.invoke_model.return_value = {"body": mock_body}

        tools = [{"name": "test_tool", "description": "test", "input_schema": {"type": "object"}}]
        response = service.invoke(messages=[{"role": "user", "content": "test"}], tools=tools)

        body = json.loads(service.client.invoke_model.call_args[1]["body"])
        assert body["tools"] == tools

    def test_extract_text_response(self, bedrock_service):
        service, _ = bedrock_service

        response = {
            "content": [
                {"type": "text", "text": "Hello "},
                {"type": "text", "text": "World"},
            ]
        }
        assert service.extract_text_response(response) == "Hello \nWorld"

    def test_extract_text_response_empty(self, bedrock_service):
        service, _ = bedrock_service
        assert service.extract_text_response({"content": []}) == ""

    def test_extract_tool_use(self, bedrock_service):
        service, _ = bedrock_service

        response = {
            "content": [
                {"type": "text", "text": "Let me search"},
                {"type": "tool_use", "id": "t1", "name": "search", "input": {"q": "test"}},
            ]
        }
        tools = service.extract_tool_use(response)
        assert len(tools) == 1
        assert tools[0]["name"] == "search"
        assert tools[0]["input"] == {"q": "test"}

    def test_extract_tool_use_none(self, bedrock_service):
        service, _ = bedrock_service
        response = {"content": [{"type": "text", "text": "No tools"}]}
        assert service.extract_tool_use(response) == []
