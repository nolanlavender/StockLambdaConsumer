#!/bin/bash

# Stock Lambda Consumer - Log Monitoring Script
# Tails CloudWatch logs for the Lambda functions

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
STACK_NAME="${STACK_NAME:-stock-lambda-consumer}"
AWS_REGION="${AWS_REGION:-us-east-1}"
FUNCTION_TYPE="${1:-processor}"

if [ "$FUNCTION_TYPE" = "monitor" ]; then
    LOG_GROUP="/aws/lambda/${STACK_NAME}-StockAnalyticsMonitor-"
else
    LOG_GROUP="/aws/lambda/${STACK_NAME}-StockAnalyticsProcessor-"
fi

# Find the actual log group name
ACTUAL_LOG_GROUP=$(aws logs describe-log-groups \
    --log-group-name-prefix "${LOG_GROUP}" \
    --query 'logGroups[0].logGroupName' \
    --output text \
    --region "${AWS_REGION}" 2>/dev/null || echo "")

if [ -z "$ACTUAL_LOG_GROUP" ] || [ "$ACTUAL_LOG_GROUP" = "None" ]; then
    echo -e "${YELLOW}Log group not found. Trying alternative...${NC}"
    # Try without stack name prefix
    if [ "$FUNCTION_TYPE" = "monitor" ]; then
        ACTUAL_LOG_GROUP="/aws/lambda/StockAnalyticsMonitor"
    else
        ACTUAL_LOG_GROUP="/aws/lambda/StockAnalyticsProcessor"
    fi
fi

echo -e "${GREEN}Monitoring logs for ${FUNCTION_TYPE}...${NC}"
echo -e "${YELLOW}Log Group: ${ACTUAL_LOG_GROUP}${NC}"
echo ""

aws logs tail "${ACTUAL_LOG_GROUP}" \
    --follow \
    --region "${AWS_REGION}" \
    --format short

echo ""
echo -e "${YELLOW}Usage: $0 <processor|monitor>${NC}"
