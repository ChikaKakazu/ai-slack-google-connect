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
                "指定された参加者のGoogle Calendarを確認します。"
                "予定の確認、空き時間の検索、スケジュールの確認に使用してください。"
                "「今日の予定を教えて」「空き時間を探して」などのリクエストに対して、"
                "このツールを必ず呼び出してください。"
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
                        "description": "検索対象の日付（例: '2024-01-15', '明日', '今日'）。省略時は今日の日付が使用されます。",
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
                        "description": "ミーティングの所要時間（分）。デフォルト60分",
                        "default": 60,
                    },
                    "summary": {
                        "type": "string",
                        "description": "予定のタイトル（件名）。省略時は「ミーティング」",
                        "default": "ミーティング",
                    },
                },
                "required": ["attendees"],
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
        {
            "name": "suggest_reschedule",
            "description": (
                "既存のイベントの参加者を自動取得し、空き時間候補を最大3つ提案します。"
                "「このMTGをリスケして」「時間を変更して」などのリクエストに使用してください。"
                "具体的な新しい時間が指定されていない場合はこのツールを使ってください。"
                "event_titleでイベントを検索できます。event_idが分かっている場合はevent_idを使用してください。"
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "event_id": {
                        "type": "string",
                        "description": "リスケ対象のイベントID（event_titleと排他。IDが分かっている場合のみ使用）",
                    },
                    "event_title": {
                        "type": "string",
                        "description": "リスケ対象のイベントタイトル（部分一致で検索。例: 'MTG被りテスト'、'定例会議'）",
                    },
                    "date": {
                        "type": "string",
                        "description": "リスケ候補を検索する日付（例: '2024-01-15', '明日', '今日'）。省略時は元のイベントと同じ日。",
                    },
                    "duration_minutes": {
                        "type": "integer",
                        "description": "ミーティングの所要時間（分）。省略時は元のイベントの長さを使用。",
                    },
                },
                "required": [],
            },
        },
    ]
