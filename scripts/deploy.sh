#!/bin/bash

# Stock Lambda Consumer - Deployment Script
# Deploys the SAM application to AWS

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Stock Lambda Consumer - Deployment${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check for required tools
command -v sam >/dev/null 2>&1 || { echo -e "${RED}Error: AWS SAM CLI is not installed${NC}" >&2; exit 1; }
command -v aws >/dev/null 2>&1 || { echo -e "${RED}Error: AWS CLI is not installed${NC}" >&2; exit 1; }

# Configuration
STACK_NAME="${STACK_NAME:-stock-lambda-consumer}"
AWS_REGION="${AWS_REGION:-us-east-1}"
S3_BUCKET="${S3_BUCKET}"

# Get Kinesis stream info from producer stack or environment
PRODUCER_STACK_NAME="${PRODUCER_STACK_NAME:-stock-lambda-producer}"
KINESIS_STREAM_NAME="${KINESIS_STREAM_NAME}"
KINESIS_STREAM_ARN="${KINESIS_STREAM_ARN}"

# If not provided, try to get from producer stack
if [ -z "$KINESIS_STREAM_NAME" ] || [ -z "$KINESIS_STREAM_ARN" ]; then
    echo -e "${YELLOW}Fetching Kinesis stream info from producer stack...${NC}"

    KINESIS_STREAM_NAME=$(aws cloudformation describe-stacks \
        --stack-name "$PRODUCER_STACK_NAME" \
        --query "Stacks[0].Outputs[?OutputKey=='KinesisStreamName'].OutputValue" \
        --output text \
        --region "$AWS_REGION" 2>/dev/null || echo "")

    KINESIS_STREAM_ARN=$(aws cloudformation describe-stacks \
        --stack-name "$PRODUCER_STACK_NAME" \
        --query "Stacks[0].Outputs[?OutputKey=='KinesisStreamArn'].OutputValue" \
        --output text \
        --region "$AWS_REGION" 2>/dev/null || echo "")
fi

# Validate required parameters
if [ -z "$KINESIS_STREAM_NAME" ] || [ -z "$KINESIS_STREAM_ARN" ]; then
    echo -e "${RED}Error: Could not determine Kinesis stream information${NC}"
    echo -e "${YELLOW}Please set KINESIS_STREAM_NAME and KINESIS_STREAM_ARN environment variables${NC}"
    echo ""
    echo "Example:"
    echo "  export KINESIS_STREAM_NAME=stock-prices-stream"
    echo "  export KINESIS_STREAM_ARN=arn:aws:kinesis:us-east-1:123456789:stream/stock-prices-stream"
    exit 1
fi

# Check for S3 bucket
if [ -z "$S3_BUCKET" ]; then
    echo -e "${YELLOW}S3_BUCKET not set. Attempting to create one...${NC}"
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    S3_BUCKET="sam-deployments-${ACCOUNT_ID}-${AWS_REGION}"

    if ! aws s3 ls "s3://${S3_BUCKET}" 2>/dev/null; then
        echo "Creating S3 bucket: ${S3_BUCKET}"
        aws s3 mb "s3://${S3_BUCKET}" --region "${AWS_REGION}"
    fi
fi

echo -e "${GREEN}Configuration:${NC}"
echo "  Stack Name: ${STACK_NAME}"
echo "  AWS Region: ${AWS_REGION}"
echo "  S3 Bucket: ${S3_BUCKET}"
echo "  Kinesis Stream: ${KINESIS_STREAM_NAME}"
echo "  Kinesis ARN: ${KINESIS_STREAM_ARN}"
echo ""

# Build the application
echo -e "${GREEN}Building SAM application...${NC}"
sam build

if [ $? -ne 0 ]; then
    echo -e "${RED}Build failed!${NC}"
    exit 1
fi

# Deploy parameters
PARAMETERS=(
    "KinesisStreamName=${KINESIS_STREAM_NAME}"
    "KinesisStreamArn=${KINESIS_STREAM_ARN}"
    "DynamoDBTableName=${DYNAMODB_TABLE_NAME:-stock-analytics}"
    "DataRetentionDays=${DATA_RETENTION_DAYS:-7}"
    "EnforceMarketHours=${ENFORCE_MARKET_HOURS:-true}"
    "TestMode=${TEST_MODE:-false}"
    "NoDataTimeoutMinutes=${NO_DATA_TIMEOUT_MINUTES:-10}"
    "CheckIntervalMinutes=${CHECK_INTERVAL_MINUTES:-5}"
)

PARAM_OVERRIDES=$(IFS=, ; echo "${PARAMETERS[*]}")

# Deploy the application
echo -e "${GREEN}Deploying SAM application...${NC}"
sam deploy \
    --stack-name "${STACK_NAME}" \
    --s3-bucket "${S3_BUCKET}" \
    --capabilities CAPABILITY_IAM \
    --region "${AWS_REGION}" \
    --parameter-overrides ${PARAM_OVERRIDES} \
    --no-fail-on-empty-changeset

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}Deployment successful!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""

    # Get outputs
    echo -e "${GREEN}Stack Outputs:${NC}"
    aws cloudformation describe-stacks \
        --stack-name "${STACK_NAME}" \
        --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
        --output table \
        --region "${AWS_REGION}"

    echo ""
    echo -e "${GREEN}Next steps:${NC}"
    echo "  1. Monitor CloudWatch Logs for function execution"
    echo "  2. Check DynamoDB table for analytics data"
    echo "  3. View Kinesis event source mapping status"
    echo ""
else
    echo -e "${RED}Deployment failed!${NC}"
    exit 1
fi
