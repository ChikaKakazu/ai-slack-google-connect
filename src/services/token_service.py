"""OAuth token management using DynamoDB."""

import json
import logging
import os
import time

import boto3
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from utils.secrets_utils import get_google_secrets

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar"]


class TokenService:
    """Manages Google OAuth tokens in DynamoDB."""

    def __init__(self, table_name: str | None = None):
        self.table_name = table_name or os.environ.get("OAUTH_TOKENS_TABLE_NAME", "oauth-tokens")
        dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "ap-northeast-1"))
        self.table = dynamodb.Table(self.table_name)

    def get_credentials(self, user_id: str) -> Credentials | None:
        """Get valid Google credentials for a user.

        Automatically refreshes expired tokens.

        Args:
            user_id: Slack user ID.

        Returns:
            Valid Credentials or None if not authorized.
        """
        try:
            response = self.table.get_item(Key={"user_id": user_id})
            item = response.get("Item")
            if not item:
                return None

            token_data = json.loads(item["token_data"])
            creds = Credentials.from_authorized_user_info(token_data, SCOPES)

            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                self.save_credentials(user_id, creds)

            if not creds.valid:
                return None

            return creds
        except Exception:
            logger.exception("Failed to get credentials for user=%s", user_id)
            return None

    def save_credentials(self, user_id: str, credentials: Credentials) -> None:
        """Save Google OAuth credentials to DynamoDB.

        Args:
            user_id: Slack user ID.
            credentials: Google OAuth Credentials object.
        """
        token_data = {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": list(credentials.scopes) if credentials.scopes else SCOPES,
        }

        try:
            self.table.put_item(
                Item={
                    "user_id": user_id,
                    "token_data": json.dumps(token_data),
                    "updated_at": int(time.time()),
                }
            )
        except Exception:
            logger.exception("Failed to save credentials for user=%s", user_id)

    def delete_credentials(self, user_id: str) -> None:
        """Delete stored credentials for a user."""
        try:
            self.table.delete_item(Key={"user_id": user_id})
        except Exception:
            logger.exception("Failed to delete credentials for user=%s", user_id)

    def get_oauth_url(self, user_id: str, redirect_uri: str) -> str:
        """Generate Google OAuth authorization URL.

        Args:
            user_id: Slack user ID (stored in state parameter).
            redirect_uri: OAuth callback URL.

        Returns:
            Authorization URL string.
        """
        from google_auth_oauthlib.flow import Flow

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

        auth_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
            state=user_id,
        )

        return auth_url
