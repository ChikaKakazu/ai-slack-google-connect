# 手動セットアップ作業ログ

このドキュメントは、システム構築時に手動で行った作業を記録したものです。

## 1. GCPプロジェクト作成

- GCPコンソールで新規プロジェクトを作成
- プロジェクト名: `ai-slack-cal-connect`
  - ※ "google" を含む名前（ai-slack-google-connect）は禁止されているため変更
- Terraform で Calendar API を有効化:
  ```bash
  cd infra/gcp
  terraform init
  terraform apply -var="gcp_project_id=ai-slack-cal-connect"
  ```

## 2. GCP OAuth Client ID 作成

- [GCP Console](https://console.cloud.google.com/apis/credentials) → 認証情報
- 「認証情報を作成」→「OAuth クライアント ID」
- アプリケーションの種類: ウェブアプリケーション
- 承認済みリダイレクト URI:
  - terraformで作成したAWS API GatewayのURL + `oauth/google/callback`
  ```
  https://us9ijlot20.execute-api.ap-northeast-1.amazonaws.com/oauth/google/callback
  ```
- 作成された `client_id` と `client_secret` を控える

## 3. Slack App 作成・設定

### 3.1 App 作成
- [Slack API](https://api.slack.com/apps) で Bot アプリを作成

### 3.2 Bot Token Scopes 設定
- OAuth & Permissions → Bot Token Scopes に以下を追加:
  - `app_mentions:read`
  - `chat:write`

### 3.3 Event Subscriptions 設定
- Enable Events を **On** に設定
- Request URL:
  - terraformで作成したAWS API GatewayのURL + `slack/events`
  ```
  https://us9ijlot20.execute-api.ap-northeast-1.amazonaws.com/slack/events
  ```
- Subscribe to bot events に `app_mention` を追加
- Save Changes

### 3.4 Interactivity & Shortcuts 設定
- Interactivity を **On** に設定
- Request URL:
  - terraformで作成したAWS API GatewayのURL + `slack/interactive`
  ```
  https://us9ijlot20.execute-api.ap-northeast-1.amazonaws.com/slack/interactive
  ```

### 3.5 App をワークスペースにインストール
- OAuth & Permissions → Install to Workspace
- Bot User OAuth Token (`xoxb-...`) と Signing Secret を控える

## 4. AWS Secrets Manager にシークレット登録

### 4.1 Slack シークレット
```bash
aws secretsmanager put-secret-value \
  --secret-id ai-slack-google-connect/slack-prod \
  --secret-string '{"bot_token":"xoxb-...","signing_secret":"..."}' \
  --no-cli-pager
```

### 4.2 Google シークレット
```bash
aws secretsmanager put-secret-value \
  --secret-id ai-slack-google-connect/google-prod \
  --secret-string '{"client_id":"....apps.googleusercontent.com","client_secret":"..."}' \
  --no-cli-pager
```

## 5. Amazon Bedrock モデルアクセス有効化

- AWS コンソール → Amazon Bedrock → Model catalog
- Anthropic Claude 3.5 Sonnet v2 を選択
- Use case details フォームを提出（初回のみ必要）
  - Company name: 個人名等
  - Use case description: Slack bot for meeting scheduling
- 承認後（通常即時〜15分）、モデルが利用可能に

## 6. Terraform backend 構築

```bash
./scripts/setup_backend.sh
```

## 7. AWS インフラデプロイ

```bash
cd infra/aws
terraform init
terraform apply
```

## 8. Lambda デプロイ

```bash
./scripts/deploy.sh
```

## 作業順序まとめ

```
1. GCP プロジェクト作成 + Calendar API 有効化 (Terraform)
2. GCP OAuth Client ID 作成 (手動)
3. Slack App 作成・設定 (手動)
4. Terraform backend 構築 (スクリプト)
5. AWS インフラデプロイ (Terraform)
6. AWS Secrets Manager にシークレット登録 (AWS CLI)
7. Amazon Bedrock Use case details 提出 (手動)
8. Lambda デプロイ (スクリプト)
9. Slack Event Subscriptions / Interactivity URL 設定 (手動)
10. 動作確認: Slack でボットにメンション
```
