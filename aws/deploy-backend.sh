#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AWS_REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-}}"
STACK_NAME="${STACK_NAME:-nyay-vision-backend}"
ECR_REPOSITORY="${ECR_REPOSITORY:-nyay-vision-backend}"
SERVICE_NAME="${SERVICE_NAME:-nyay-vision-api}"
FRONTEND_ORIGIN="${FRONTEND_ORIGIN:-}"

if [[ -z "$AWS_REGION" || -z "${OPENAI_SECRET_ARN:-}" ]]; then
  echo "Set AWS_REGION and OPENAI_SECRET_ARN first. The secret must contain the OpenAI key as SecretString." >&2
  exit 2
fi
for tool in aws docker; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "Required command not found: $tool" >&2
    exit 2
  fi
done

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text --region "$AWS_REGION")"
REGISTRY="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
COMMIT_TAG="$(git -C "$ROOT_DIR" rev-parse --short HEAD 2>/dev/null || echo local)"
IMAGE_TAG="${COMMIT_TAG}-$(date -u +%Y%m%d%H%M%S)"
IMAGE_URI="${REGISTRY}/${ECR_REPOSITORY}:${IMAGE_TAG}"

if ! aws ecr describe-repositories --repository-names "$ECR_REPOSITORY" --region "$AWS_REGION" >/dev/null 2>&1; then
  aws ecr create-repository \
    --repository-name "$ECR_REPOSITORY" \
    --image-scanning-configuration scanOnPush=true \
    --image-tag-mutability IMMUTABLE \
    --region "$AWS_REGION" >/dev/null
fi

aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$REGISTRY"
docker build --platform linux/amd64 -f "$ROOT_DIR/backend/Dockerfile" -t "$IMAGE_URI" "$ROOT_DIR/backend"
docker push "$IMAGE_URI"

aws cloudformation deploy \
  --template-file "$ROOT_DIR/aws/app-runner-backend.yaml" \
  --stack-name "$STACK_NAME" \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides \
    "ContainerImage=$IMAGE_URI" \
    "OpenAISecretArn=$OPENAI_SECRET_ARN" \
    "FrontendOrigin=$FRONTEND_ORIGIN" \
    "ServiceName=$SERVICE_NAME" \
  --region "$AWS_REGION"

aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue | [0]" \
  --output text \
  --region "$AWS_REGION"
