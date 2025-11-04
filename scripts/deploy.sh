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

    # Check if producer stack exists
    STACK_STATUS=$(aws cloudformation describe-stacks \
        --stack-name "$PRODUCER_STACK_NAME" \
        --query "Stacks[0].StackStatus" \
        --output text \
        --region "$AWS_REGION" 2>/dev/null || echo "NOT_FOUND")

    if [ "$STACK_STATUS" = "NOT_FOUND" ]; then
        echo -e "${RED}Error: Producer stack '${PRODUCER_STACK_NAME}' not found${NC}"
        echo ""
        echo -e "${YELLOW}Please do ONE of the following:${NC}"
        echo ""
        echo "1. Deploy the producer stack first:"
        echo "   cd ../StockLambdaProducer"
        echo "   export FINNHUB_API_KEY=your-api-key"
        echo "   ./scripts/deploy.sh"
        echo "   cd ../StockLambdaConsumer"
        echo "   ./scripts/deploy.sh"
        echo ""
        echo "2. OR manually set the Kinesis stream information:"
        echo "   export KINESIS_STREAM_NAME=stock-prices-stream"
        echo "   export KINESIS_STREAM_ARN=arn:aws:kinesis:${AWS_REGION}:ACCOUNT_ID:stream/stock-prices-stream"
        echo "   ./scripts/deploy.sh"
        echo ""
        echo "3. OR specify a different producer stack name:"
        echo "   export PRODUCER_STACK_NAME=my-producer-stack"
        echo "   ./scripts/deploy.sh"
        exit 1
    fi

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

    # Check if outputs were found
    if [ -z "$KINESIS_STREAM_NAME" ] || [ "$KINESIS_STREAM_NAME" = "None" ]; then
        echo -e "${RED}Error: Producer stack exists but has no KinesisStreamName output${NC}"
        echo ""
        echo "Available outputs from producer stack:"
        aws cloudformation describe-stacks \
            --stack-name "$PRODUCER_STACK_NAME" \
            --query "Stacks[0].Outputs[*].[OutputKey,OutputValue]" \
            --output table \
            --region "$AWS_REGION"
        echo ""
        echo "Please manually set the Kinesis stream information:"
        echo "  export KINESIS_STREAM_NAME=stock-prices-stream"
        echo "  export KINESIS_STREAM_ARN=arn:aws:kinesis:${AWS_REGION}:ACCOUNT_ID:stream/stock-prices-stream"
        exit 1
    fi
fi

# Validate required parameters
if [ -z "$KINESIS_STREAM_NAME" ] || [ -z "$KINESIS_STREAM_ARN" ]; then
    echo -e "${RED}Error: Could not determine Kinesis stream information${NC}"
    echo -e "${YELLOW}Please set KINESIS_STREAM_NAME and KINESIS_STREAM_ARN environment variables${NC}"
    echo ""
    echo "Example:"
    echo "  export KINESIS_STREAM_NAME=stock-prices-stream"
    echo "  export KINESIS_STREAM_ARN=arn:aws:kinesis:${AWS_REGION}:ACCOUNT_ID:stream/stock-prices-stream"
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

# Validate parameters one more time before deploy
echo -e "${GREEN}Validating parameters...${NC}"
if [ -z "$KINESIS_STREAM_ARN" ] || [ "$KINESIS_STREAM_ARN" = "None" ]; then
    echo -e "${RED}Error: KINESIS_STREAM_ARN is empty or None${NC}"
    echo "Current value: '${KINESIS_STREAM_ARN}'"
    exit 1
fi

echo "  Kinesis Stream ARN: ${KINESIS_STREAM_ARN}"
echo "  Kinesis Stream Name: ${KINESIS_STREAM_NAME}"
echo ""

# Build the application
echo -e "${GREEN}Building SAM application...${NC}"
sam build --use-container 2>/dev/null || sam build

if [ $? -ne 0 ]; then
    echo -e "${RED}Build failed!${NC}"
    exit 1
fi

echo -e "${GREEN}Build successful!${NC}"
echo ""

# Deploy the application
echo -e "${GREEN}Deploying SAM application...${NC}"
echo "This may take several minutes..."
echo ""

sam deploy \
    --stack-name "${STACK_NAME}" \
    --s3-bucket "${S3_BUCKET}" \
    --capabilities CAPABILITY_IAM \
    --region "${AWS_REGION}" \
    --no-fail-on-empty-changeset \
    --parameter-overrides \
        KinesisStreamName="${KINESIS_STREAM_NAME}" \
        KinesisStreamArn="${KINESIS_STREAM_ARN}" \
        DynamoDBTableName="${DYNAMODB_TABLE_NAME:-stock-analytics}" \
        DataRetentionDays="${DATA_RETENTION_DAYS:-7}" \
        EnforceMarketHours="${ENFORCE_MARKET_HOURS:-true}" \
        TestMode="${TEST_MODE:-false}" \
        NoDataTimeoutMinutes="${NO_DATA_TIMEOUT_MINUTES:-10}" \
        CheckIntervalMinutes="${CHECK_INTERVAL_MINUTES:-5}"

DEPLOY_EXIT_CODE=$?

if [ $DEPLOY_EXIT_CODE -eq 0 ]; then
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
    echo "  1. Monitor CloudWatch Logs: ./scripts/monitor_logs.sh processor"
    echo "  2. Check DynamoDB table: ./scripts/query_analytics.sh AAPL 10"
    echo "  3. View logs: aws logs tail /aws/lambda/stock-lambda-consumer-StockAnalyticsProcessor --follow"
    echo ""
    echo -e "${GREEN}Deployment complete! Consumer is now processing data from Kinesis.${NC}"
    echo ""
else
    echo ""
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}Deployment failed!${NC}"
    echo -e "${RED}========================================${NC}"
    echo ""
    echo -e "${YELLOW}Troubleshooting:${NC}"
    echo ""
    echo "1. Check the error message above for specific issues"
    echo ""
    echo "2. Verify parameters are correct:"
    echo "   KINESIS_STREAM_NAME='${KINESIS_STREAM_NAME}'"
    echo "   KINESIS_STREAM_ARN='${KINESIS_STREAM_ARN}'"
    echo ""
    echo "3. Check CloudFormation events for detailed error:"
    echo "   aws cloudformation describe-stack-events --stack-name ${STACK_NAME} --max-items 10"
    echo ""
    echo "4. To retry deployment, simply run this script again:"
    echo "   ./scripts/deploy.sh"
    echo ""
    echo "5. Only run teardown if you want to delete everything:"
    echo "   ./scripts/teardown.sh"
    echo ""
    exit 1
fi
