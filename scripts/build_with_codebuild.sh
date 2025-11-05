#!/bin/bash

# Stock ECS Consumer - Build Docker Image using AWS CodeBuild
# No local Docker required!

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}Build with AWS CodeBuild${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# Configuration
CODEBUILD_STACK_NAME="${CODEBUILD_STACK_NAME:-stock-ecs-consumer-codebuild}"
ECS_STACK_NAME="${ECS_STACK_NAME:-stock-ecs-consumer}"
AWS_REGION="${AWS_REGION:-us-east-1}"

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( cd "${SCRIPT_DIR}/.." && pwd )"

cd "${PROJECT_DIR}"

# Step 1: Deploy CodeBuild stack if it doesn't exist
echo -e "${GREEN}Step 1/5: Checking CodeBuild infrastructure...${NC}"

CODEBUILD_STACK_EXISTS=$(aws cloudformation describe-stacks \
    --stack-name "${CODEBUILD_STACK_NAME}" \
    --region "${AWS_REGION}" 2>/dev/null || echo "")

if [ -z "$CODEBUILD_STACK_EXISTS" ]; then
    echo "CodeBuild stack doesn't exist. Creating..."

    aws cloudformation create-stack \
        --stack-name "${CODEBUILD_STACK_NAME}" \
        --template-body file://template-codebuild.yaml \
        --capabilities CAPABILITY_IAM \
        --region "${AWS_REGION}" \
        --tags \
            Key=Application,Value=StockECSConsumer

    echo "Waiting for CodeBuild stack creation..."
    aws cloudformation wait stack-create-complete \
        --stack-name "${CODEBUILD_STACK_NAME}" \
        --region "${AWS_REGION}"

    echo -e "${GREEN}CodeBuild infrastructure created!${NC}"
else
    echo "CodeBuild stack already exists."
fi

echo ""

# Step 2: Get stack outputs
echo -e "${GREEN}Step 2/5: Getting configuration...${NC}"

PROJECT_NAME=$(aws cloudformation describe-stacks \
    --stack-name "${CODEBUILD_STACK_NAME}" \
    --query "Stacks[0].Outputs[?OutputKey=='CodeBuildProjectName'].OutputValue" \
    --output text \
    --region "${AWS_REGION}")

SOURCE_BUCKET=$(aws cloudformation describe-stacks \
    --stack-name "${CODEBUILD_STACK_NAME}" \
    --query "Stacks[0].Outputs[?OutputKey=='SourceBucketName'].OutputValue" \
    --output text \
    --region "${AWS_REGION}")

echo -e "${GREEN}CodeBuild Project: ${PROJECT_NAME}${NC}"
echo -e "${GREEN}Source Bucket: ${SOURCE_BUCKET}${NC}"
echo ""

# Step 3: Package source code
echo -e "${GREEN}Step 3/5: Packaging source code...${NC}"

# Create temporary directory
TEMP_DIR=$(mktemp -d)
echo "Using temp directory: ${TEMP_DIR}"

# Copy files to temp directory
cp -r src "${TEMP_DIR}/"
cp Dockerfile "${TEMP_DIR}/"
cp buildspec.yml "${TEMP_DIR}/"

# Create zip file
ZIP_FILE="${TEMP_DIR}/source.zip"
cd "${TEMP_DIR}"
zip -r source.zip . > /dev/null
cd "${PROJECT_DIR}"

echo -e "${GREEN}Source code packaged ($(du -h ${ZIP_FILE} | cut -f1))${NC}"
echo ""

# Step 4: Upload to S3
echo -e "${GREEN}Step 4/5: Uploading source to S3...${NC}"

aws s3 cp "${ZIP_FILE}" "s3://${SOURCE_BUCKET}/${CODEBUILD_STACK_NAME}-source.zip" \
    --region "${AWS_REGION}"

# Cleanup temp directory
rm -rf "${TEMP_DIR}"

echo -e "${GREEN}Source uploaded to S3${NC}"
echo ""

# Step 5: Trigger CodeBuild
echo -e "${GREEN}Step 5/5: Starting CodeBuild...${NC}"

BUILD_ID=$(aws codebuild start-build \
    --project-name "${PROJECT_NAME}" \
    --region "${AWS_REGION}" \
    --query 'build.id' \
    --output text)

echo -e "${GREEN}Build started: ${BUILD_ID}${NC}"
echo ""

# Wait for build to complete
echo -e "${YELLOW}Waiting for build to complete (this may take 3-5 minutes)...${NC}"
echo ""

while true; do
    BUILD_STATUS=$(aws codebuild batch-get-builds \
        --ids "${BUILD_ID}" \
        --region "${AWS_REGION}" \
        --query 'builds[0].buildStatus' \
        --output text)

    if [ "$BUILD_STATUS" == "SUCCEEDED" ]; then
        echo ""
        echo -e "${GREEN}========================================${NC}"
        echo -e "${GREEN}Build Successful!${NC}"
        echo -e "${GREEN}========================================${NC}"
        echo ""

        # Get ECR repository URI
        ECR_URI=$(aws cloudformation describe-stacks \
            --stack-name "${ECS_STACK_NAME}" \
            --query "Stacks[0].Outputs[?OutputKey=='ECRRepositoryUri'].OutputValue" \
            --output text \
            --region "${AWS_REGION}")

        echo -e "${CYAN}Docker image pushed to:${NC}"
        echo -e "  ${ECR_URI}:latest"
        echo ""

        echo -e "${YELLOW}Next step:${NC}"
        echo -e "  Update ECS service: ./scripts/update_ecs_service.sh"
        echo ""

        # Show CloudWatch logs link
        echo -e "${CYAN}View build logs:${NC}"
        LOG_GROUP="/aws/codebuild/${PROJECT_NAME}"
        echo -e "  aws logs tail ${LOG_GROUP} --follow --region ${AWS_REGION}"
        echo ""

        exit 0

    elif [ "$BUILD_STATUS" == "FAILED" ] || [ "$BUILD_STATUS" == "FAULT" ] || [ "$BUILD_STATUS" == "TIMED_OUT" ] || [ "$BUILD_STATUS" == "STOPPED" ]; then
        echo ""
        echo -e "${RED}========================================${NC}"
        echo -e "${RED}Build Failed: ${BUILD_STATUS}${NC}"
        echo -e "${RED}========================================${NC}"
        echo ""

        echo -e "${YELLOW}Check build logs:${NC}"
        LOG_GROUP="/aws/codebuild/${PROJECT_NAME}"
        echo -e "  aws logs tail ${LOG_GROUP} --since 10m --region ${AWS_REGION}"
        echo ""

        echo -e "${YELLOW}Or view in AWS Console:${NC}"
        echo -e "  https://console.aws.amazon.com/codesuite/codebuild/projects/${PROJECT_NAME}/history"
        echo ""

        exit 1

    else
        # Still in progress
        PHASE=$(aws codebuild batch-get-builds \
            --ids "${BUILD_ID}" \
            --region "${AWS_REGION}" \
            --query 'builds[0].currentPhase' \
            --output text)

        echo -e "${CYAN}Status: ${BUILD_STATUS} | Phase: ${PHASE}${NC}"
        sleep 10
    fi
done
