"""Google OAuth callback handler."""

import logging
import os

from google_auth_oauthlib.flow import Flow
from slack_bolt import App

from services.token_service import SCOPES, TokenService
from utils.secrets_utils import get_google_secrets

logger = logging.getLogger(__name__)

token_service = TokenService()


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


def _get_redirect_uri(event: dict) -> str:
    """Construct the OAuth redirect URI from the API Gateway event."""
    headers = event.get("headers", {})
    host = headers.get("host", "")
    stage = event.get("requestContext", {}).get("stage", "")

    if stage and stage != "$default":
        return f"https://{host}/{stage}/oauth/google/callback"
    return f"https://{host}/oauth/google/callback"
