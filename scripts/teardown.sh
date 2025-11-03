#!/bin/bash

# Stock Lambda Consumer - Teardown Script
# Deletes the CloudFormation stack and all resources

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${RED}========================================${NC}"
echo -e "${RED}Stock Lambda Consumer - Teardown${NC}"
echo -e "${RED}========================================${NC}"
echo ""

# Configuration
STACK_NAME="${STACK_NAME:-stock-lambda-consumer}"
AWS_REGION="${AWS_REGION:-us-east-1}"

echo -e "${YELLOW}WARNING: This will delete the following:${NC}"
echo "  - CloudFormation stack: ${STACK_NAME}"
echo "  - Lambda functions"
echo "  - DynamoDB table and all data"
echo "  - CloudWatch log groups"
echo "  - IAM roles and policies"
echo ""

read -p "Are you sure you want to continue? (yes/no): " -r
echo

if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo -e "${GREEN}Teardown cancelled${NC}"
    exit 0
fi

echo -e "${YELLOW}Deleting stack...${NC}"

aws cloudformation delete-stack \
    --stack-name "${STACK_NAME}" \
    --region "${AWS_REGION}"

echo -e "${YELLOW}Waiting for stack deletion...${NC}"

aws cloudformation wait stack-delete-complete \
    --stack-name "${STACK_NAME}" \
    --region "${AWS_REGION}"

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}Stack deleted successfully!${NC}"
    echo -e "${GREEN}========================================${NC}"
else
    echo -e "${RED}Stack deletion failed!${NC}"
    echo -e "${YELLOW}Check the CloudFormation console for details${NC}"
    exit 1
fi
