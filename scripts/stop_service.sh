#!/bin/bash

# Stock ECS Consumer - Manually Stop Service

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}Stopping ECS Service${NC}"
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

# Stop service
echo -e "${GREEN}Setting desired count to 0...${NC}"
aws ecs update-service \
    --cluster "${CLUSTER_NAME}" \
    --service "${SERVICE_NAME}" \
    --desired-count 0 \
    --region "${AWS_REGION}" \
    > /dev/null

echo ""
echo -e "${GREEN}Service stopped!${NC}"
echo ""
echo -e "${YELLOW}Note: The container will save its state to S3 before shutting down.${NC}"
echo ""
echo -e "${CYAN}Monitor shutdown:${NC}"
echo -e "  ./scripts/view_ecs_logs.sh"
echo ""
echo -e "${CYAN}Check status:${NC}"
echo -e "  ./scripts/ecs_status.sh"
echo ""
