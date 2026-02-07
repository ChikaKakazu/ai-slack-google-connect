# ai-slack-google-connect

Slack Bot + AWS Bedrock Claude + Google Calendar 連携による AI MTGスケジュール調整システム。

## 概要

Slackでボットにメンションし、自然言語でMTGスケジュール調整を行うシステムです。

```
@bot 明日の14:00-17:00で、tanaka@example.com と sato@example.com の
ミーティングを30分で設定して
```

→ AIが参加者の空き時間を検索し、候補を提案 → ボタンクリックでカレンダーイベント作成

## アーキテクチャ

```
Slack (@bot メンション)
  ↓
API Gateway (HTTP API)
  ↓
Lambda (Python 3.11 / Slack Bolt)
  ├── Bedrock Claude (意図理解 + Tool Use)
  ├── Google Calendar API (FreeBusy / Events)
  ├── DynamoDB (会話状態 / OAuthトークン)
  └── Secrets Manager (Slack Token / Google OAuth)
```

## セットアップ

### 前提条件

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (パッケージマネージャ)
- Terraform >= 1.5
- AWS CLI (設定済み)
- GCP プロジェクト (Calendar API用)

### 1. 依存関係インストール

```bash
uv sync
uv pip install -e ".[dev]"
```

### 2. Terraform backend構築

```bash
./scripts/setup_backend.sh
```

### 3. Secrets設定

AWS Secrets Managerに以下のシークレットを設定:

**Slack secrets** (`ai-slack-google-connect/slack-dev`):
```json
{
  "bot_token": "xoxb-...",
  "signing_secret": "..."
}
```

**Google secrets** (`ai-slack-google-connect/google-dev`):
```json
{
  "client_id": "....apps.googleusercontent.com",
  "client_secret": "..."
}
```

### 4. インフラデプロイ

```bash
cd infra/aws
terraform init
terraform apply
```

### 5. Lambdaデプロイ

```bash
./scripts/deploy.sh
```

### 6. Slack App設定

1. [Slack API](https://api.slack.com/apps) でBotアプリを作成
2. Event Subscriptionsで `app_mention` を有効化
3. Request URLに API Gateway URL + `/slack/events` を設定
4. Interactivity URLに API Gateway URL + `/slack/interactive` を設定
5. Bot Token Scopeに `app_mentions:read`, `chat:write` を追加

## テスト

```bash
# 全テスト実行
uv run pytest tests/ -v --cov=src --cov-report=term-missing

# ユニットテストのみ
uv run pytest tests/unit/ -v
```

## プロジェクト構造

```
src/
├── app.py                     # Lambda handler
├── handlers/
│   ├── message_handler.py     # メンション処理 + Bedrock Tool Use
│   ├── oauth_handler.py       # Google OAuthコールバック
│   └── interactive_handler.py # Slack Button処理
├── services/
│   ├── bedrock_service.py     # Bedrock Claude呼び出し
│   ├── calendar_service.py    # Google Calendar API
│   ├── token_service.py       # OAuthトークン管理
│   └── conversation_service.py # 会話状態管理
├── tools/
│   ├── calendar_tools.py      # Bedrock Tool定義
│   └── tool_executor.py       # ツール実行エンジン
└── utils/
    ├── time_utils.py          # タイムゾーン・日時処理
    ├── slack_utils.py         # Block Kit UI生成
    └── secrets_utils.py       # Secrets Manager操作
```
