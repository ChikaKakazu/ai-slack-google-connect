"""AWS Secrets Manager utility for retrieving secrets."""

import json
import logging
import os

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

_secrets_cache: dict[str, dict] = {}


def get_secret(secret_name: str) -> dict:
    """Retrieve a secret from AWS Secrets Manager with caching.

    Args:
        secret_name: The name or ARN of the secret.

    Returns:
        Parsed JSON secret as a dictionary.

    Raises:
        ClientError: If the secret cannot be retrieved.
    """
    if secret_name in _secrets_cache:
        return _secrets_cache[secret_name]

    region = os.environ.get("AWS_REGION", "ap-northeast-1")
    client = boto3.client("secretsmanager", region_name=region)

    try:
        response = client.get_secret_value(SecretId=secret_name)
        secret = json.loads(response["SecretString"])
        _secrets_cache[secret_name] = secret
        return secret
    except ClientError:
        logger.exception("Failed to retrieve secret: %s", secret_name)
        raise


def get_slack_secrets() -> dict:
    """Retrieve Slack secrets (bot_token, signing_secret)."""
    secret_name = os.environ["SECRETS_NAME"]
    return get_secret(secret_name)


def get_google_secrets() -> dict:
    """Retrieve Google OAuth secrets (client_id, client_secret)."""
    secret_name = os.environ["GOOGLE_SECRETS_NAME"]
    return get_secret(secret_name)


def clear_cache() -> None:
    """Clear the secrets cache (useful for testing)."""
    _secrets_cache.clear()
