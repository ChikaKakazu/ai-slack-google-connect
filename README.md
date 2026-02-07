# ai-slack-google-connect

Slack Bot + AWS Bedrock Claude + Google Calendar 連携による AI MTGスケジュール調整システム。

## 概要

Slackでボットにメンションし、自然言語でMTGスケジュール調整を行うシステムです。

```
@bot 明日の14:00-17:00で、tanaka@example.com と sato@example.com の
ミーティングを30分で設定して
```

→ AIが参加者の空き時間を検索し、候補を提案 → ボタンクリック → モーダルでイベント名を確認・編集 → カレンダーイベント作成

## 主な機能

### 空き時間検索 & イベント作成
1. ボットにメンションで自然言語リクエスト
2. AIが参加者のカレンダーから空き時間を検索
3. 候補をボタン付きメッセージで表示
4. ボタンクリック → モーダルでイベント名を確認・編集 → 作成

### AI直接イベント作成
1. AIがcreate_eventツールを呼び出した場合
2. 確認ボタン付きメッセージを表示（即座には作成しない）
3. ボタンクリック → モーダルでイベント名を確認・編集 → 作成

### リスケジュール
1. 「○○のMTGをリスケして」とリクエスト
2. AIがイベントをタイトル検索し、参加者の空き時間から候補を提案
3. ボタンクリックで即座にリスケ実行
4. 翌営業日フォールバック対応

### その他
- **Slackメンション解決**: `<@USER_ID>` を自動でメールアドレスに変換
- **OAuth自動再実行**: 認証完了後、保留中のリクエストを自動で再実行
- **営業日判定**: 土日祝を自動判定し、営業日外の場合は警告

## アーキテクチャ

```
Slack (@bot メンション)
  ↓
API Gateway (HTTP API)
  ↓
Lambda (Python 3.11 / Slack Bolt)
  ├── Bedrock Claude (意図理解 + Tool Use)
  │     ├── search_free_slots  → 空き時間検索
  │     ├── create_event       → イベント作成（確認フロー経由）
  │     ├── reschedule_event   → リスケ実行
  │     └── suggest_reschedule → リスケ候補提案
  ├── Google Calendar API (FreeBusy / Events)
  ├── DynamoDB (会話状態 / OAuthトークン)
  └── Secrets Manager (Slack Token / Google OAuth)
```

### インタラクティブフロー

```
空き時間候補:
  候補ボタン → モーダル（イベント名編集）→「予約する」→ イベント作成

AI直接作成:
  ツール実行 → 確認ボタン → モーダル（イベント名編集）→「予約する」→ イベント作成

リスケジュール:
  候補ボタン → 即リスケ実行（イベント名は既存のまま）
```

## セットアップ

### 前提条件

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (パッケージマネージャ)
- Terraform >= 1.5
- AWS CLI (設定済み)
- GCP プロジェクト (Calendar API用)
- GCP CLI (`gcloud`) 設定済み

### 1. 依存関係インストール

```bash
uv sync --dev
```

### 2. Terraform backend構築

```bash
./scripts/setup_backend.sh
```

### 3. GCPセットアップ

Calendar APIの有効化はTerraformで管理しています:

```bash
cd infra/gcp
terraform init
terraform apply -var="gcp_project_id=YOUR_PROJECT_ID"
```

OAuth Client IDはGCP Consoleで手動作成が必要です:

1. [GCP Console](https://console.cloud.google.com/apis/credentials) → 認証情報
2. 「認証情報を作成」→「OAuthクライアントID」
3. アプリケーションの種類: 「ウェブアプリケーション」
4. 承認済みリダイレクトURIに `https://<API_GATEWAY_URL>/oauth/google/callback` を追加
5. 作成された `client_id` と `client_secret` を次のステップでSecrets Managerに設定

### 4. Secrets設定

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

### 5. AWSインフラデプロイ

```bash
cd infra/aws
terraform init
terraform apply
```

### 6. Lambdaデプロイ

```bash
./scripts/deploy.sh
```

### 7. Slack App設定

1. [Slack API](https://api.slack.com/apps) でBotアプリを作成
2. Event Subscriptionsで `app_mention` を有効化
3. Request URLに API Gateway URL + `/slack/events` を設定
4. Interactivity URLに API Gateway URL + `/slack/interactive` を設定
5. Bot Token Scopeに `app_mentions:read`, `chat:write`, `users:read`, `users:read.email` を追加

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
│   ├── oauth_handler.py       # Google OAuthコールバック + 自動再実行
│   └── interactive_handler.py # Slack Button/Modal処理
├── services/
│   ├── bedrock_service.py     # Bedrock Claude呼び出し
│   ├── calendar_service.py    # Google Calendar API
│   ├── token_service.py       # OAuthトークン管理
│   └── conversation_service.py # 会話状態管理
├── tools/
│   ├── calendar_tools.py      # Bedrock Tool定義
│   └── tool_executor.py       # ツール実行エンジン
└── utils/
    ├── time_utils.py          # タイムゾーン・日時・営業日処理
    ├── slack_utils.py         # Block Kit UI / Modal生成
    └── secrets_utils.py       # Secrets Manager操作
```
