#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AWS_REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-}}"
STACK_NAME="${STACK_NAME:-nyay-vision-serverless}"
FRONTEND_ORIGINS="${FRONTEND_ORIGINS:-${FRONTEND_ORIGIN:-}}"
OPENAI_SECRET_ARN="${OPENAI_SECRET_ARN:-}"

if [[ -z "$AWS_REGION" || -z "$OPENAI_SECRET_ARN" || -z "$FRONTEND_ORIGINS" ]]; then
  echo "Set AWS_REGION, OPENAI_SECRET_ARN, and FRONTEND_ORIGINS (comma-separated exact origins)." >&2
  exit 2
fi
for tool in aws sam docker; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "Required command not found: $tool" >&2
    exit 2
  fi
done

COMMIT_TAG="$(git -C "$ROOT_DIR" rev-parse --short HEAD 2>/dev/null || echo local)"
IMAGE_TAG="${COMMIT_TAG}-$(date -u +%Y%m%d%H%M%S)"
DEPLOY_TEMPLATE="$ROOT_DIR/aws/.template-deploy.yaml"
sed "s/DockerTag: release/DockerTag: ${IMAGE_TAG}/" "$ROOT_DIR/aws/template.yaml" > "$DEPLOY_TEMPLATE"
trap 'rm -f "$DEPLOY_TEMPLATE"' EXIT

sam build --template-file "$DEPLOY_TEMPLATE" --use-container
sam deploy \
  --template-file "$ROOT_DIR/.aws-sam/build/template.yaml" \
  --stack-name "$STACK_NAME" \
  --capabilities CAPABILITY_IAM \
  --resolve-s3 \
  --resolve-image-repos \
  --parameter-overrides \
    "OpenAISecretArn=$OPENAI_SECRET_ARN" \
    "FrontendOrigins=$FRONTEND_ORIGINS" \
  --region "$AWS_REGION" \
  --no-confirm-changeset \
  --no-fail-on-empty-changeset

aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue | [0]" \
  --output text \
  --region "$AWS_REGION"
