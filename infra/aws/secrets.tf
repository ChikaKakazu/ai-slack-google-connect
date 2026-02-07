resource "aws_secretsmanager_secret" "slack_secrets" {
  name                    = "${var.project_name}/slack-${var.environment}"
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret" "google_secrets" {
  name                    = "${var.project_name}/google-${var.environment}"
  recovery_window_in_days = 7
}
