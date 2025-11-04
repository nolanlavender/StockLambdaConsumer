#!/bin/bash

# Stock ECS Consumer - View CloudWatch Logs

# Colors for output
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
STACK_NAME="${STACK_NAME:-stock-ecs-consumer}"
AWS_REGION="${AWS_REGION:-us-east-1}"
DURATION="${1:-10m}"

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}ECS Consumer Logs${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# Get log group from CloudFormation
LOG_GROUP=$(aws cloudformation describe-stacks \
    --stack-name "${STACK_NAME}" \
    --query "Stacks[0].Outputs[?OutputKey=='LogGroupName'].OutputValue" \
    --output text \
    --region "${AWS_REGION}")

echo -e "${GREEN}Log Group: ${LOG_GROUP}${NC}"
echo -e "${GREEN}Duration: ${DURATION}${NC}"
echo ""

# Tail logs
aws logs tail "${LOG_GROUP}" \
    --since "${DURATION}" \
    --follow \
    --format short \
    --region "${AWS_REGION}"
