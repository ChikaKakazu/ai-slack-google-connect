#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="${SCRIPT_DIR}/../infra/backend"

echo "=== Setting up Terraform state backend ==="

cd "${BACKEND_DIR}"

terraform init
terraform plan
terraform apply

echo "=== Backend setup complete ==="
echo "S3 bucket and DynamoDB lock table are ready."
