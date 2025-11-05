#!/bin/bash

# Stock ECS Consumer - Manually Start Service

set -e

# Colors for output
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}Starting ECS Service${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# Configuration
STACK_NAME="${STACK_NAME:-stock-ecs-consumer}"
AWS_REGION="${AWS_REGION:-us-east-1}"

# Get cluster and service names
echo -e "${GREEN}Getting service info...${NC}"
CLUSTER_NAME=$(aws cloudformation describe-stacks \
    --stack-name "${STACK_NAME}" \
    --query "Stacks[0].Outputs[?OutputKey=='ECSClusterName'].OutputValue" \
    --output text \
    --region "${AWS_REGION}")

SERVICE_NAME=$(aws cloudformation describe-stacks \
    --stack-name "${STACK_NAME}" \
    --query "Stacks[0].Outputs[?OutputKey=='ECSServiceName'].OutputValue" \
    --output text \
    --region "${AWS_REGION}")

echo -e "${GREEN}Cluster: ${CLUSTER_NAME}${NC}"
echo -e "${GREEN}Service: ${SERVICE_NAME}${NC}"
echo ""

# Start service
echo -e "${GREEN}Setting desired count to 1...${NC}"
aws ecs update-service \
    --cluster "${CLUSTER_NAME}" \
    --service "${SERVICE_NAME}" \
    --desired-count 1 \
    --region "${AWS_REGION}" \
    > /dev/null

echo ""
echo -e "${GREEN}Service started!${NC}"
echo ""
echo -e "${CYAN}Monitor status:${NC}"
echo -e "  ./scripts/ecs_status.sh"
echo ""
echo -e "${CYAN}View logs:${NC}"
echo -e "  ./scripts/view_ecs_logs.sh"
echo ""
