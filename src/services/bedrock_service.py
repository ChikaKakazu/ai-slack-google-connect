"""AWS Bedrock Claude service for natural language understanding and tool use."""

import json
import logging
import os

import boto3

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """あなたはSlack上で動作するMTGスケジュール調整アシスタントです。
ユーザーからの自然言語リクエストを理解し、以下のツールを使って対応してください。

役割:
- 参加者の空き時間を検索する
- 最適なミーティング時間を提案する
- カレンダーにイベントを作成する
- 既存のイベントをリスケジュールする

応答ルール:
- 日本語で応答すること
- 丁寧かつ簡潔に応答すること
- 複数の候補時間がある場合はリスト形式で提案すること
- 不明な情報がある場合はユーザーに確認すること
"""


class BedrockService:
    """Service for interacting with AWS Bedrock Claude model."""

    def __init__(self, model_id: str | None = None, region: str | None = None):
        self.model_id = model_id or os.environ.get(
            "BEDROCK_MODEL_ID", "apac.anthropic.claude-3-5-sonnet-20241022-v2:0"
        )
        self.region = region or os.environ.get("BEDROCK_REGION", "ap-northeast-1")
        self.client = boto3.client("bedrock-runtime", region_name=self.region)

    def invoke(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        max_tokens: int = 1024,
    ) -> dict:
        """Invoke Bedrock Claude model with messages and optional tools.

        Args:
            messages: Conversation messages in Bedrock format.
            tools: Tool definitions for tool use.
            max_tokens: Maximum tokens in response.

        Returns:
            Model response dict containing content and stop_reason.
        """
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "system": SYSTEM_PROMPT,
            "messages": messages,
        }

        if tools:
            request_body["tools"] = tools

        logger.info("Invoking Bedrock model=%s messages=%d", self.model_id, len(messages))

        response = self.client.invoke_model(
            modelId=self.model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(request_body),
        )

        response_body = json.loads(response["body"].read())
        logger.info("Bedrock response stop_reason=%s", response_body.get("stop_reason"))

        return response_body

    def extract_text_response(self, response: dict) -> str:
        """Extract text content from Bedrock response.

        Args:
            response: Raw Bedrock response dict.

        Returns:
            Concatenated text from all text content blocks.
        """
        texts = []
        for block in response.get("content", []):
            if block.get("type") == "text":
                texts.append(block["text"])
        return "\n".join(texts)

    def extract_tool_use(self, response: dict) -> list[dict]:
        """Extract tool use blocks from Bedrock response.

        Args:
            response: Raw Bedrock response dict.

        Returns:
            List of tool use blocks with id, name, and input.
        """
        tool_uses = []
        for block in response.get("content", []):
            if block.get("type") == "tool_use":
                tool_uses.append(block)
        return tool_uses
