#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${SCRIPT_DIR}/.."
INFRA_DIR="${PROJECT_DIR}/infra/aws"

echo "=== Building Lambda deployment package ==="

TEMP_DIR=$(mktemp -d)
trap 'rm -rf "${TEMP_DIR}"' EXIT

# Install dependencies
pip install -r "${PROJECT_DIR}/requirements.txt" -t "${TEMP_DIR}" --quiet

# Copy source code
cp -r "${PROJECT_DIR}/src/"* "${TEMP_DIR}/"

# Create zip
cd "${TEMP_DIR}"
zip -r "${PROJECT_DIR}/lambda.zip" . -q

echo "=== Lambda package created: lambda.zip ==="

# Deploy with Terraform
cd "${INFRA_DIR}"
terraform init
terraform apply -auto-approve \
  -var="lambda_source_changed=true"

echo "=== Deployment complete ==="

# Update Lambda function code directly for faster iteration
FUNCTION_NAME=$(terraform output -raw lambda_function_name)
aws lambda update-function-code \
  --function-name "${FUNCTION_NAME}" \
  --zip-file "fileb://${PROJECT_DIR}/lambda.zip" \
  --no-cli-pager

echo "=== Lambda function updated: ${FUNCTION_NAME} ==="
