"""AWS Bedrock Claude service for natural language understanding and tool use."""

import json
import logging
import os
from datetime import datetime

import boto3

from utils.time_utils import JST

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_TEMPLATE = """あなたはSlack上で動作するMTGスケジュール調整アシスタントです。
ユーザーからの自然言語リクエストを理解し、提供されたツールを使って対応してください。

現在日時: {current_datetime}

重要: カレンダーに関するリクエスト（予定確認、空き時間検索、イベント作成、リスケジュール）を受けた場合は、
必ずツールを呼び出してください。認証状態の判断はあなたの役割ではありません。
ツールを実行すれば、認証が必要な場合はシステムが自動的に対応します。

役割:
- 参加者の空き時間を検索する (search_free_slots) — 空き時間検索・スケジュール確認に使用。ユーザーが件名を指定している場合はsummaryパラメータに渡すこと。
- カレンダーにイベントを作成する (create_event)
- 既存のイベントをリスケジュールする (reschedule_event) — 具体的な新しい時間が指定されている場合
- リスケジュール候補を提案する (suggest_reschedule) — 「リスケして」「時間変更して」など具体的な新時間指定がない場合

デフォルト動作:
- 日付が指定されていない場合は「今日」として扱うこと。ユーザーに日付を聞き返さないこと。
- メッセージ中にメールアドレス（例: tanaka@example.com）が含まれている場合、それは対象ユーザーのメールアドレスである。そのままattendeesパラメータに使用すること。ユーザーにメールアドレスを聞き返さないこと。
- 「件名は〇〇」「タイトルは〇〇」「〇〇という名前で」などの表現がある場合、それをcreate_eventのsummaryパラメータに使用すること。
- 件名が指定されていない場合は「ミーティング」をsummaryとして使用すること。
- 終了時刻が指定されていない場合は、開始時刻の1時間後を終了時刻とすること。
- 1つのメッセージに予定作成に必要な情報（参加者、時間、件名）がすべて含まれている場合は、確認せずに即座にcreate_eventツールを実行すること。search_free_slotsを事前に呼ぶ必要はない。

リスケジュール判定ルール:
- 「リスケして」「時間変更して」「別の時間にして」「ずらしたい」「いつがあいてますか」など、具体的な新時間の指定がない場合 → suggest_reschedule を使用
- 「14時に変更して」「明日の10時にリスケ」など、具体的な新時間が指定されている場合 → reschedule_event を使用
- ユーザーがイベント名（タイトル）を伝えた場合は、event_titleパラメータにそのタイトルを指定すること。event_idをユーザーに聞き返さないこと。
- 例: 「MTG被りテストの予定をずらしたい」→ suggest_reschedule(event_title="MTG被りテスト") を即座に実行

営業日ルール:
- 土日祝日は営業日外です。営業日外に予定作成・検索のリクエストがあった場合は、ユーザーに確認してください。

応答ルール:
- 日本語で応答すること
- 丁寧かつ簡潔に応答すること
- 複数の候補時間がある場合はリスト形式で提案すること
- カレンダー関連のリクエストでは必ずツールを使用すること
- 必要な情報が揃っている場合は確認せずに即座にツールを実行すること
"""


def _build_system_prompt() -> str:
    """Build system prompt with current datetime."""
    now = datetime.now(JST)
    return SYSTEM_PROMPT_TEMPLATE.format(
        current_datetime=now.strftime("%Y年%m月%d日 %H:%M (JST)")
    )


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
            "system": _build_system_prompt(),
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
