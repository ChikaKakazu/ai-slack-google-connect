# ai-slack-google-connect

Slack Bot + AWS Bedrock Claude + Google Calendar 連携による AI MTGスケジュール調整システム。

## 技術スタック

- **Runtime**: Python 3.11 / AWS Lambda
- **AI**: AWS Bedrock Claude (Tool Use)
- **Slack**: Slack Bolt for Python
- **Calendar**: Google Calendar API
- **IaC**: Terraform (AWS + GCP)
- **Storage**: DynamoDB (会話状態 / OAuthトークン)
- **パッケージ管理**: uv

## コマンド

```bash
# テスト実行
uv run pytest tests/ -v --cov=src --cov-report=term-missing

# デプロイ
./scripts/deploy.sh
```

## アーキテクチャ概要

### ツール (Bedrock Tool Use)

| ツール名 | 機能 | フロー |
|---------|------|-------|
| `search_free_slots` | 空き時間検索 | → 候補ボタン表示 → モーダル → 作成 |
| `create_event` | イベント作成 | → 確認ボタン表示 → モーダル → 作成 |
| `suggest_reschedule` | リスケ候補提案 | → 候補ボタン表示 → 即リスケ実行 |
| `reschedule_event` | リスケ実行 | → 完了メッセージ |

### インタラクティブフロー

- **イベント作成系** (search_free_slots / create_event): ボタン → モーダル（イベント名編集可能）→ 作成
- **リスケジュール** (suggest_reschedule): ボタン → 即実行（イベント名は既存のまま）

### 主要ファイル

- `src/handlers/message_handler.py` - メンション処理 + Bedrock Tool Useループ
- `src/handlers/interactive_handler.py` - Button/Modal ハンドラ
- `src/handlers/oauth_handler.py` - Google OAuth + 自動再実行
- `src/tools/tool_executor.py` - ツール実行エンジン
- `src/utils/slack_utils.py` - Block Kit UI / Modal生成

## Ensemble AI Orchestration

This project uses Ensemble for AI-powered development orchestration.

### Quick Start
- `/go <task>` - Start a task with automatic planning and execution
- `/go-light <task>` - Lightweight execution for simple changes
- `/status` - View current progress

### Communication Protocol
- Agent communication via file-based queue (.ensemble/queue/)
- Dashboard updates in .ensemble/status/dashboard.md

For more information, see the [Ensemble documentation](https://github.com/ChikaKakazu/ensemble).
