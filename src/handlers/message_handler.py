"""Slack message handler for bot mentions with Bedrock Claude integration."""

import logging
import re

from slack_bolt import App

from services.bedrock_service import BedrockService
from services.conversation_service import ConversationService
from tools.calendar_tools import get_tool_definitions
from tools.tool_executor import ToolExecutor

logger = logging.getLogger(__name__)

bedrock = BedrockService()
conversation = ConversationService()
tool_executor = ToolExecutor()


def register_message_handlers(app: App) -> None:
    """Register message-related event handlers on the Slack Bolt app."""

    @app.event("app_mention")
    def handle_mention(event: dict, say, client) -> None:
        """Handle @bot mentions - process through Bedrock Claude with Tool Use."""
        user_id = event.get("user", "")
        text = event.get("text", "")
        thread_ts = event.get("thread_ts") or event.get("ts", "")

        cleaned_text = _clean_mention_text(text)

        if not cleaned_text.strip():
            say(
                text="何かお手伝いできることはありますか？MTGのスケジュール調整などお気軽にどうぞ！",
                thread_ts=thread_ts,
            )
            return

        logger.info("Mention from user=%s text=%s", user_id, cleaned_text[:100])

        # Add user message to conversation history
        messages = conversation.append_message(user_id, thread_ts, "user", cleaned_text)

        # Get tool definitions
        tools = get_tool_definitions()

        try:
            # Invoke Bedrock with conversation history and tools
            response = bedrock.invoke(messages=messages, tools=tools)

            # Handle tool use loop
            response = _handle_tool_use_loop(
                user_id=user_id,
                thread_ts=thread_ts,
                messages=messages,
                response=response,
                tools=tools,
                say=say,
            )

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
    messages: list[dict],
    response: dict,
    tools: list[dict],
    say,
    max_iterations: int = 5,
) -> dict:
    """Execute tool use loop until model stops requesting tools.

    Args:
        user_id: Slack user ID.
        thread_ts: Thread timestamp.
        messages: Current conversation messages.
        response: Initial Bedrock response.
        tools: Tool definitions.
        say: Slack say function.
        max_iterations: Max tool use iterations to prevent infinite loops.

    Returns:
        Final Bedrock response after all tool executions.
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
            logger.info("Executing tool: %s (iteration %d)", tool_use["name"], iteration)

            result = tool_executor.execute(
                tool_name=tool_use["name"],
                tool_input=tool_use["input"],
                user_id=user_id,
            )

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

    return response


def _clean_mention_text(text: str) -> str:
    """Remove bot mention tag from message text."""
    return re.sub(r"<@[A-Z0-9]+>\s*", "", text).strip()
