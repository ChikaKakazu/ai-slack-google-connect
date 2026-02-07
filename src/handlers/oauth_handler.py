"""Google OAuth callback handler."""

import logging
import os

from google_auth_oauthlib.flow import Flow
from slack_bolt import App
from slack_sdk import WebClient

from services.conversation_service import ConversationService
from services.token_service import SCOPES, TokenService
from utils.secrets_utils import get_google_secrets, get_slack_secrets

logger = logging.getLogger(__name__)

token_service = TokenService()
conversation_service = ConversationService()


def register_oauth_handlers(app: App) -> None:
    """Register OAuth-related route handlers."""
    # OAuth callback is handled via API Gateway route, not Slack events.
    # See app.py for the route registration.
    pass


def handle_oauth_callback(event: dict) -> dict:
    """Handle Google OAuth callback from API Gateway.

    Args:
        event: API Gateway event with query parameters.

    Returns:
        HTTP response dict.
    """
    query_params = event.get("queryStringParameters", {}) or {}
    code = query_params.get("code")
    state = query_params.get("state")  # user_id
    error = query_params.get("error")

    if error:
        logger.error("OAuth error: %s", error)
        return {
            "statusCode": 400,
            "body": "認証がキャンセルされました。Slackから再度お試しください。",
            "headers": {"Content-Type": "text/plain; charset=utf-8"},
        }

    if not code or not state:
        return {
            "statusCode": 400,
            "body": "不正なリクエストです。",
            "headers": {"Content-Type": "text/plain; charset=utf-8"},
        }

    user_id = state
    redirect_uri = _get_redirect_uri(event)

    try:
        secrets = get_google_secrets()

        client_config = {
            "web": {
                "client_id": secrets["client_id"],
                "client_secret": secrets["client_secret"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        }

        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            redirect_uri=redirect_uri,
        )

        flow.fetch_token(code=code)
        credentials = flow.credentials

        token_service.save_credentials(user_id, credentials)

        logger.info("OAuth completed for user=%s", user_id)

        # Check for pending request and re-execute
        pending = conversation_service.get_pending_request(user_id)
        if pending:
            conversation_service.delete_pending_request(user_id)
            _execute_pending_request(user_id, pending)
            return {
                "statusCode": 200,
                "body": "Google Calendarの認証が完了しました！リクエストを自動的に処理しています。Slackをご確認ください。",
                "headers": {"Content-Type": "text/plain; charset=utf-8"},
            }

        return {
            "statusCode": 200,
            "body": "Google Calendarの認証が完了しました！Slackに戻って操作を続けてください。",
            "headers": {"Content-Type": "text/plain; charset=utf-8"},
        }

    except Exception:
        logger.exception("OAuth callback error for user=%s", user_id)
        return {
            "statusCode": 500,
            "body": "認証処理中にエラーが発生しました。再度お試しください。",
            "headers": {"Content-Type": "text/plain; charset=utf-8"},
        }


def _execute_pending_request(user_id: str, pending: dict) -> None:
    """Execute a pending request after OAuth completion.

    Args:
        user_id: Slack user ID.
        pending: Dict with text, thread_ts, channel_id.
    """
    from handlers.message_handler import process_request

    try:
        secrets = get_slack_secrets()
        client = WebClient(token=secrets["bot_token"])

        # Notify user that the request is being re-executed
        client.chat_postMessage(
            channel=pending["channel_id"],
            text="Google認証が完了しました！リクエストを処理しています...",
            thread_ts=pending["thread_ts"],
        )

        process_request(
            user_id=user_id,
            text=pending["text"],
            thread_ts=pending["thread_ts"],
            channel_id=pending["channel_id"],
            client=client,
        )
    except Exception:
        logger.exception("Failed to execute pending request for user=%s", user_id)


def _get_redirect_uri(event: dict) -> str:
    """Construct the OAuth redirect URI from the API Gateway event."""
    headers = event.get("headers", {})
    host = headers.get("host", "")
    stage = event.get("requestContext", {}).get("stage", "")

    if stage and stage != "$default":
        return f"https://{host}/{stage}/oauth/google/callback"
    return f"https://{host}/oauth/google/callback"
