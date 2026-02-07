"""Conversation state management using DynamoDB."""

import json
import logging
import os
import time

import boto3
from boto3.dynamodb.conditions import Key

logger = logging.getLogger(__name__)


class ConversationService:
    """Manages conversation history in DynamoDB for multi-turn interactions."""

    def __init__(self, table_name: str | None = None):
        self.table_name = table_name or os.environ.get("CONVERSATIONS_TABLE_NAME", "conversations")
        dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "ap-northeast-1"))
        self.table = dynamodb.Table(self.table_name)
        self.ttl_hours = int(os.environ.get("CONVERSATION_TTL_HOURS", "24"))

    def get_messages(self, user_id: str, thread_ts: str) -> list[dict]:
        """Retrieve conversation messages for a thread.

        Args:
            user_id: Slack user ID.
            thread_ts: Thread timestamp as sort key.

        Returns:
            List of messages in Bedrock format.
        """
        try:
            response = self.table.get_item(
                Key={"user_id": user_id, "thread_ts": thread_ts}
            )
            item = response.get("Item")
            if item:
                return json.loads(item.get("messages", "[]"))
            return []
        except Exception:
            logger.exception("Failed to get conversation: user=%s thread=%s", user_id, thread_ts)
            return []

    def save_messages(self, user_id: str, thread_ts: str, messages: list[dict]) -> None:
        """Save conversation messages for a thread.

        Args:
            user_id: Slack user ID.
            thread_ts: Thread timestamp as sort key.
            messages: List of messages in Bedrock format.
        """
        ttl = int(time.time()) + (self.ttl_hours * 3600)

        try:
            self.table.put_item(
                Item={
                    "user_id": user_id,
                    "thread_ts": thread_ts,
                    "messages": json.dumps(messages, ensure_ascii=False),
                    "ttl": ttl,
                    "updated_at": int(time.time()),
                }
            )
        except Exception:
            logger.exception("Failed to save conversation: user=%s thread=%s", user_id, thread_ts)

    def append_message(self, user_id: str, thread_ts: str, role: str, content: str | list) -> list[dict]:
        """Append a message to the conversation and save.

        Args:
            user_id: Slack user ID.
            thread_ts: Thread timestamp.
            role: Message role ('user' or 'assistant').
            content: Message content (string or content blocks).

        Returns:
            Updated messages list.
        """
        messages = self.get_messages(user_id, thread_ts)

        if isinstance(content, str):
            messages.append({"role": role, "content": content})
        else:
            messages.append({"role": role, "content": content})

        self.save_messages(user_id, thread_ts, messages)
        return messages

    def clear_conversation(self, user_id: str, thread_ts: str) -> None:
        """Delete a conversation thread.

        Args:
            user_id: Slack user ID.
            thread_ts: Thread timestamp.
        """
        try:
            self.table.delete_item(
                Key={"user_id": user_id, "thread_ts": thread_ts}
            )
        except Exception:
            logger.exception("Failed to clear conversation: user=%s thread=%s", user_id, thread_ts)

    def save_pending_request(
        self, user_id: str, text: str, thread_ts: str, channel_id: str
    ) -> None:
        """Save a pending request to be re-executed after OAuth completion.

        Uses a special thread_ts key prefix to distinguish from normal conversations.

        Args:
            user_id: Slack user ID.
            text: Original request text.
            thread_ts: Thread timestamp.
            channel_id: Slack channel ID.
        """
        ttl = int(time.time()) + 600  # 10-minute TTL
        try:
            self.table.put_item(
                Item={
                    "user_id": user_id,
                    "thread_ts": "pending_oauth",
                    "messages": json.dumps({
                        "text": text,
                        "thread_ts": thread_ts,
                        "channel_id": channel_id,
                    }, ensure_ascii=False),
                    "ttl": ttl,
                    "updated_at": int(time.time()),
                }
            )
        except Exception:
            logger.exception("Failed to save pending request: user=%s", user_id)

    def get_pending_request(self, user_id: str) -> dict | None:
        """Get a pending request for a user after OAuth.

        Args:
            user_id: Slack user ID.

        Returns:
            Dict with text, thread_ts, channel_id or None.
        """
        try:
            response = self.table.get_item(
                Key={"user_id": user_id, "thread_ts": "pending_oauth"}
            )
            item = response.get("Item")
            if item:
                return json.loads(item.get("messages", "{}"))
            return None
        except Exception:
            logger.exception("Failed to get pending request: user=%s", user_id)
            return None

    def delete_pending_request(self, user_id: str) -> None:
        """Delete a pending request after it has been processed.

        Args:
            user_id: Slack user ID.
        """
        try:
            self.table.delete_item(
                Key={"user_id": user_id, "thread_ts": "pending_oauth"}
            )
        except Exception:
            logger.exception("Failed to delete pending request: user=%s", user_id)
