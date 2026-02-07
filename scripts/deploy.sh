#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${SCRIPT_DIR}/.."
INFRA_DIR="${PROJECT_DIR}/infra/aws"
FUNCTION_NAME="ai-slack-google-connect-dev"

# --- Build Lambda zip ---
echo "=== Building Lambda deployment package ==="

TEMP_DIR=$(mktemp -d)
trap 'rm -rf "${TEMP_DIR}"' EXIT

uv export --no-dev --no-hashes -o "${TEMP_DIR}/requirements.txt"
uv pip install \
  --target "${TEMP_DIR}" \
  --platform manylinux2014_x86_64 \
  --python-version 3.11 \
  --only-binary :all: \
  -r "${TEMP_DIR}/requirements.txt" \
  --quiet
rm "${TEMP_DIR}/requirements.txt"

cp -r "${PROJECT_DIR}/src/"* "${TEMP_DIR}/"

cd "${TEMP_DIR}"
zip -r "${PROJECT_DIR}/lambda.zip" . -q

echo "=== Lambda package created: lambda.zip ==="

# --- Deploy ---
if [ "${1:-}" = "--infra" ]; then
  # Full deploy: Terraform + Lambda code update
  cd "${INFRA_DIR}"
  terraform init
  terraform apply -auto-approve
  echo "=== Terraform apply complete ==="
fi

# Update Lambda function code
aws lambda update-function-code \
  --function-name "${FUNCTION_NAME}" \
  --zip-file "fileb://${PROJECT_DIR}/lambda.zip" \
  --no-cli-pager

echo "=== Lambda function updated: ${FUNCTION_NAME} ==="
