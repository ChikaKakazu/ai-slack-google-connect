"""Lambda handler entry point for Slack Bot + Google Calendar integration."""

import logging
import os

from slack_bolt import App
from slack_bolt.adapter.aws_lambda import SlackRequestHandler

from handlers.interactive_handler import register_interactive_handlers
from handlers.message_handler import register_message_handlers
from handlers.oauth_handler import handle_oauth_callback
from utils.secrets_utils import get_slack_secrets

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_app: App | None = None
_handler: SlackRequestHandler | None = None


def _get_app() -> App:
    """Lazily initialize and return the Slack Bolt app."""
    global _app, _handler

    if _app is not None:
        return _app

    secrets = get_slack_secrets()

    _app = App(
        token=secrets["bot_token"],
        signing_secret=secrets["signing_secret"],
        process_before_response=True,
    )

    register_message_handlers(_app)
    register_interactive_handlers(_app)

    _handler = SlackRequestHandler(app=_app)
    logger.info("Slack Bolt app initialized")

    return _app


def _get_handler() -> SlackRequestHandler:
    """Lazily initialize and return the request handler."""
    _get_app()
    assert _handler is not None
    return _handler


def handler(event: dict, context) -> dict:
    """AWS Lambda handler routing API Gateway events.

    Routes:
        POST /slack/events     -> Slack Bolt (mentions, messages)
        POST /slack/interactive -> Slack Bolt (buttons, actions)
        GET  /oauth/google/callback -> Google OAuth callback
    """
    raw_path = event.get("rawPath", "")
    logger.info("Received event: path=%s", raw_path)

    # Handle Google OAuth callback directly (not a Slack event)
    if raw_path.endswith("/oauth/google/callback"):
        return handle_oauth_callback(event)

    # All other routes go through Slack Bolt
    slack_handler = _get_handler()
    return slack_handler.handle(event, context)
