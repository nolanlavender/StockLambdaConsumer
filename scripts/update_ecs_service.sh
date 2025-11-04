#!/bin/bash

# Stock ECS Consumer - Update ECS Service with New Image

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}Update ECS Service${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# Configuration
STACK_NAME="${STACK_NAME:-stock-ecs-consumer}"
AWS_REGION="${AWS_REGION:-us-east-1}"

# Get cluster and service names from CloudFormation
echo -e "${GREEN}Getting ECS service info...${NC}"
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

# Force new deployment
echo -e "${GREEN}Forcing new deployment...${NC}"
aws ecs update-service \
    --cluster "${CLUSTER_NAME}" \
    --service "${SERVICE_NAME}" \
    --force-new-deployment \
    --region "${AWS_REGION}" \
    > /dev/null

echo ""
echo -e "${GREEN}New deployment initiated!${NC}"
echo ""
echo -e "${YELLOW}Monitor deployment:${NC}"
echo -e "  ./scripts/ecs_status.sh"
echo ""
echo -e "${YELLOW}View logs:${NC}"
echo -e "  ./scripts/view_ecs_logs.sh"
