"""Bedrock Claude Tool definitions for calendar operations."""


def get_tool_definitions() -> list[dict]:
    """Return tool definitions for Bedrock Claude Tool Use.

    These tools enable the AI to:
    - Search free time slots across multiple calendars
    - Create calendar events
    - Reschedule existing events
    """
    return [
        {
            "name": "search_free_slots",
            "description": (
                "指定された参加者全員の空き時間を検索します。"
                "Google Calendarの予定を確認し、全員が参加可能な時間帯を返します。"
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "attendees": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "参加者のメールアドレスのリスト（例: ['tanaka@example.com', 'sato@example.com']）",
                    },
                    "date": {
                        "type": "string",
                        "description": "検索対象の日付（例: '2024-01-15', '明日', '今日'）",
                    },
                    "time_min": {
                        "type": "string",
                        "description": "検索開始時刻（例: '09:00'）。省略時は営業時間開始（9:00）",
                    },
                    "time_max": {
                        "type": "string",
                        "description": "検索終了時刻（例: '18:00'）。省略時は営業時間終了（18:00）",
                    },
                    "duration_minutes": {
                        "type": "integer",
                        "description": "ミーティングの所要時間（分）。デフォルト30分",
                        "default": 30,
                    },
                },
                "required": ["attendees", "date"],
            },
        },
        {
            "name": "create_event",
            "description": (
                "Google Calendarにミーティングイベントを作成します。"
                "参加者全員に招待メールが送信されます。"
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "summary": {
                        "type": "string",
                        "description": "イベントのタイトル（例: '定例MTG'）",
                    },
                    "start_time": {
                        "type": "string",
                        "description": "開始日時（ISO 8601形式: '2024-01-15T14:00:00+09:00'）",
                    },
                    "end_time": {
                        "type": "string",
                        "description": "終了日時（ISO 8601形式: '2024-01-15T14:30:00+09:00'）",
                    },
                    "attendees": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "参加者のメールアドレスのリスト",
                    },
                    "description": {
                        "type": "string",
                        "description": "イベントの説明（省略可）",
                        "default": "",
                    },
                },
                "required": ["summary", "start_time", "end_time", "attendees"],
            },
        },
        {
            "name": "reschedule_event",
            "description": (
                "既存のカレンダーイベントを別の時間にリスケジュールします。"
                "参加者全員に変更通知が送信されます。"
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "event_id": {
                        "type": "string",
                        "description": "リスケ対象のイベントID",
                    },
                    "new_start_time": {
                        "type": "string",
                        "description": "新しい開始日時（ISO 8601形式）",
                    },
                    "new_end_time": {
                        "type": "string",
                        "description": "新しい終了日時（ISO 8601形式）",
                    },
                },
                "required": ["event_id", "new_start_time", "new_end_time"],
            },
        },
    ]
