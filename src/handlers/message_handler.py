"""Slack message handler for bot mentions with Bedrock Claude integration."""

import json
import logging
import os
import re

from slack_bolt import App

from services.bedrock_service import BedrockService
from services.conversation_service import ConversationService
from services.token_service import TokenService
from tools.calendar_tools import get_tool_definitions
from tools.tool_executor import ToolExecutor
from utils.slack_utils import (
    build_create_confirmation_blocks,
    build_event_created_blocks,
    build_oauth_prompt_blocks,
    build_reschedule_suggestion_blocks,
    build_schedule_suggestion_blocks,
    post_attendee_mentions,
    resolve_user_mentions,
)

logger = logging.getLogger(__name__)

bedrock = BedrockService()
conversation = ConversationService()
tool_executor = ToolExecutor()
token_service = TokenService()


def register_message_handlers(app: App) -> None:
    """Register message-related event handlers on the Slack Bolt app."""

    @app.event("app_mention")
    def handle_mention(event: dict, say, client) -> None:
        """Handle @bot mentions - process through Bedrock Claude with Tool Use."""
        user_id = event.get("user", "")
        text = event.get("text", "")
        channel_id = event.get("channel", "")
        thread_ts = event.get("thread_ts") or event.get("ts", "")

        cleaned_text = _clean_mention_text(text)

        if not cleaned_text.strip():
            say(
                text="何かお手伝いできることはありますか？MTGのスケジュール調整などお気軽にどうぞ！",
                thread_ts=thread_ts,
            )
            return

        # Resolve <@USER_ID> mentions to email addresses
        cleaned_text = resolve_user_mentions(cleaned_text, client)

        logger.info("Mention from user=%s text=%s", user_id, cleaned_text[:100])

        # Add user message to conversation history
        messages = conversation.append_message(user_id, thread_ts, "user", cleaned_text)

        # Get tool definitions
        tools = get_tool_definitions()

        try:
            # Invoke Bedrock with conversation history and tools
            response = bedrock.invoke(messages=messages, tools=tools)
            logger.error("DEBUG Bedrock response stop_reason=%s content_types=%s",
                         response.get("stop_reason"),
                         [b.get("type") for b in response.get("content", [])])

            # Handle tool use loop
            response, oauth_sent = _handle_tool_use_loop(
                user_id=user_id,
                thread_ts=thread_ts,
                channel_id=channel_id,
                original_text=cleaned_text,
                messages=messages,
                response=response,
                tools=tools,
                say=say,
                client=client,
            )

            if oauth_sent:
                return

            # Extract and send final text response
            text_response = bedrock.extract_text_response(response)
            if text_response:
                say(text=text_response, thread_ts=thread_ts)

                # Save assistant response
                conversation.append_message(user_id, thread_ts, "assistant", response["content"])

        except Exception:
            logger.exception("Error processing mention from user=%s", user_id)
            say(
                text="申し訳ありません、処理中にエラーが発生しました。もう一度お試しください。",
                thread_ts=thread_ts,
            )


def _handle_tool_use_loop(
    user_id: str,
    thread_ts: str,
    channel_id: str,
    original_text: str,
    messages: list[dict],
    response: dict,
    tools: list[dict],
    say,
    client=None,
    max_iterations: int = 5,
) -> tuple[dict, bool]:
    """Execute tool use loop until model stops requesting tools.

    Args:
        user_id: Slack user ID.
        thread_ts: Thread timestamp.
        channel_id: Slack channel ID.
        original_text: Original user request text (for OAuth re-execution).
        messages: Current conversation messages.
        response: Initial Bedrock response.
        tools: Tool definitions.
        say: Slack say function.
        client: Slack WebClient instance for resolving email to mentions.
        max_iterations: Max tool use iterations to prevent infinite loops.

    Returns:
        Tuple of (final Bedrock response, whether OAuth prompt was sent).
    """
    iteration = 0

    while response.get("stop_reason") == "tool_use" and iteration < max_iterations:
        iteration += 1
        tool_uses = bedrock.extract_tool_use(response)

        if not tool_uses:
            break

        # Save assistant response with tool use
        messages.append({"role": "assistant", "content": response["content"]})

        # Execute each tool and collect results
        tool_results = []
        for tool_use in tool_uses:
            logger.error("DEBUG Executing tool: %s (iteration %d)", tool_use["name"], iteration)

            result = tool_executor.execute(
                tool_name=tool_use["name"],
                tool_input=tool_use["input"],
                user_id=user_id,
            )
            logger.error("DEBUG Tool result: %s", result[:300])

            # Check tool result for special actions
            try:
                result_data = json.loads(result)
                if result_data.get("action") == "oauth_required":
                    logger.error("DEBUG OAuth required, generating URL for user=%s", user_id)
                    api_url = os.environ.get("API_GATEWAY_URL", "")
                    redirect_uri = f"{api_url}oauth/google/callback"
                    oauth_url = token_service.get_oauth_url(user_id, redirect_uri)
                    logger.error("DEBUG OAuth URL: %s", oauth_url[:100])
                    blocks = build_oauth_prompt_blocks(oauth_url)
                    say(blocks=blocks, text="Google認証が必要です", thread_ts=thread_ts)
                    conversation.save_pending_request(
                        user_id=user_id,
                        text=original_text,
                        thread_ts=thread_ts,
                        channel_id=channel_id,
                    )
                    logger.error("DEBUG OAuth blocks sent, pending request saved")
                    return response, True

                # For create suggestion, show confirmation button
                if result_data.get("status") == "suggest_create":
                    blocks = build_create_confirmation_blocks(result_data)
                    say(blocks=blocks, text="イベント作成確認", thread_ts=thread_ts)
                    return response, True

                if result_data.get("status") == "rescheduled":
                    say(
                        text=f"✅ 「{result_data.get('summary', '')}」をリスケジュールしました。\n"
                             f"📅 新しい時間: {result_data.get('start', '')} - {result_data.get('end', '')}\n"
                             f"<{result_data.get('html_link', '')}|Google Calendarで確認>",
                        thread_ts=thread_ts,
                    )
                    if client:
                        post_attendee_mentions(
                            client, channel_id, thread_ts,
                            result_data.get("summary", ""),
                            result_data.get("attendees", []),
                        )
                    return response, True

                if result_data.get("status") == "suggest_reschedule":
                    if result_data.get("no_slots_found"):
                        say(
                            text=f"😔 「{result_data.get('summary', '')}」のリスケ候補が見つかりませんでした。"
                                 f"別の日付を指定してお試しください。",
                            thread_ts=thread_ts,
                        )
                    else:
                        blocks = build_reschedule_suggestion_blocks(result_data)
                        say(
                            blocks=blocks,
                            text=f"🔄 {result_data.get('summary', '')} のリスケジュール候補",
                            thread_ts=thread_ts,
                        )
                    return response, True

                if result_data.get("status") == "suggest_schedule":
                    if not result_data.get("slots") or result_data.get("warning"):
                        say(
                            text=f"⚠️ {result_data.get('warning', '空き時間が見つかりませんでした。')}",
                            thread_ts=thread_ts,
                        )
                    else:
                        blocks = build_schedule_suggestion_blocks(result_data)
                        say(
                            blocks=blocks,
                            text="📅 空き時間候補",
                            thread_ts=thread_ts,
                        )
                    return response, True
            except (ValueError, TypeError) as e:
                logger.error("DEBUG JSON parse error: %s", e)

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_use["id"],
                "content": result,
            })

        # Add tool results as user message
        messages.append({"role": "user", "content": tool_results})

        # Save updated conversation
        conversation.save_messages(user_id, thread_ts, messages)

        # Re-invoke Bedrock with tool results
        response = bedrock.invoke(messages=messages, tools=tools)

    return response, False


def process_request(user_id: str, text: str, thread_ts: str, channel_id: str, client) -> None:
    """Process a user request through Bedrock (used for OAuth re-execution).

    Args:
        user_id: Slack user ID.
        text: Request text.
        thread_ts: Thread timestamp.
        channel_id: Slack channel ID.
        client: Slack WebClient instance.
    """
    logger.info("Processing request for user=%s text=%s", user_id, text[:100])

    # Clear old conversation for fresh re-execution
    conversation.clear_conversation(user_id, thread_ts)
    messages = conversation.append_message(user_id, thread_ts, "user", text)
    tools = get_tool_definitions()

    try:
        response = bedrock.invoke(messages=messages, tools=tools)

        response, oauth_sent = _handle_tool_use_loop(
            user_id=user_id,
            thread_ts=thread_ts,
            channel_id=channel_id,
            original_text=text,
            messages=messages,
            response=response,
            tools=tools,
            say=lambda **kwargs: client.chat_postMessage(channel=channel_id, **kwargs),
            client=client,
        )

        if oauth_sent:
            return

        text_response = bedrock.extract_text_response(response)
        if text_response:
            client.chat_postMessage(
                channel=channel_id,
                text=text_response,
                thread_ts=thread_ts,
            )
            conversation.append_message(user_id, thread_ts, "assistant", response["content"])

    except Exception:
        logger.exception("Error processing re-executed request for user=%s", user_id)
        client.chat_postMessage(
            channel=channel_id,
            text="申し訳ありません、処理中にエラーが発生しました。もう一度お試しください。",
            thread_ts=thread_ts,
        )


def _clean_mention_text(text: str) -> str:
    """Remove first bot mention tag from message text, preserving other user mentions."""
    return re.sub(r"<@[A-Z0-9]+>\s*", "", text, count=1).strip()
