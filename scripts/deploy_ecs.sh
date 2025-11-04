#!/bin/bash

# Stock ECS Consumer - Deploy CloudFormation Stack

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}Stock ECS Consumer - Deploy${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# Configuration
STACK_NAME="${STACK_NAME:-stock-ecs-consumer}"
AWS_REGION="${AWS_REGION:-us-east-1}"
TEMPLATE_FILE="template-ecs.yaml"

# Get Kinesis stream ARN from producer stack
echo -e "${GREEN}Getting Kinesis stream ARN...${NC}"
KINESIS_ARN=$(aws cloudformation describe-stacks \
    --stack-name "stock-lambda-producer" \
    --query "Stacks[0].Outputs[?OutputKey=='KinesisStreamArn'].OutputValue" \
    --output text \
    --region "${AWS_REGION}" 2>/dev/null || echo "")

if [ -z "$KINESIS_ARN" ]; then
    echo -e "${RED}Could not get Kinesis stream ARN from producer stack.${NC}"
    echo -e "${YELLOW}Please provide the ARN manually or deploy the producer first.${NC}"
    exit 1
fi

echo -e "${GREEN}Kinesis Stream ARN: ${KINESIS_ARN}${NC}"
echo ""

# Check if stack exists
STACK_EXISTS=$(aws cloudformation describe-stacks \
    --stack-name "${STACK_NAME}" \
    --region "${AWS_REGION}" 2>/dev/null || echo "")

if [ -z "$STACK_EXISTS" ]; then
    echo -e "${YELLOW}Stack does not exist. Creating new stack...${NC}"
    OPERATION="create-stack"
else
    echo -e "${YELLOW}Stack exists. Updating stack...${NC}"
    OPERATION="update-stack"
fi

echo ""
echo -e "${GREEN}Deploying CloudFormation stack...${NC}"
echo ""

# Deploy stack
if [ "$OPERATION" = "create-stack" ]; then
    aws cloudformation create-stack \
        --stack-name "${STACK_NAME}" \
        --template-body file://"${TEMPLATE_FILE}" \
        --parameters \
            ParameterKey=KinesisStreamArn,ParameterValue="${KINESIS_ARN}" \
            ParameterKey=KinesisStreamName,ParameterValue=stock-prices-stream \
        --capabilities CAPABILITY_IAM \
        --region "${AWS_REGION}" \
        --tags \
            Key=Application,Value=StockECSConsumer \
            Key=Environment,Value=Production

    echo ""
    echo -e "${GREEN}Stack creation initiated. Waiting for completion...${NC}"
    aws cloudformation wait stack-create-complete \
        --stack-name "${STACK_NAME}" \
        --region "${AWS_REGION}"

else
    aws cloudformation update-stack \
        --stack-name "${STACK_NAME}" \
        --template-body file://"${TEMPLATE_FILE}" \
        --parameters \
            ParameterKey=KinesisStreamArn,ParameterValue="${KINESIS_ARN}" \
            ParameterKey=KinesisStreamName,ParameterValue=stock-prices-stream \
        --capabilities CAPABILITY_IAM \
        --region "${AWS_REGION}" 2>&1 | grep -v "No updates are to be performed" || true

    echo ""
    echo -e "${GREEN}Stack update initiated. Waiting for completion...${NC}"
    aws cloudformation wait stack-update-complete \
        --stack-name "${STACK_NAME}" \
        --region "${AWS_REGION}" 2>&1 || true
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Display outputs
echo -e "${CYAN}Stack Outputs:${NC}"
aws cloudformation describe-stacks \
    --stack-name "${STACK_NAME}" \
    --query 'Stacks[0].Outputs' \
    --output table \
    --region "${AWS_REGION}"

echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo -e "  1. Build and push Docker image: ./scripts/build_and_push.sh"
echo -e "  2. Update ECS service: ./scripts/update_ecs_service.sh"
echo -e "  3. View logs: ./scripts/view_ecs_logs.sh"
echo -e "  4. Check service status: ./scripts/ecs_status.sh"
