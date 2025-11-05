#!/bin/bash

# Stock ECS Consumer - Complete Deployment Script
# Deploys infrastructure, builds image, and starts service

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}Stock ECS Consumer - Full Deployment${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( cd "${SCRIPT_DIR}/.." && pwd )"

cd "${PROJECT_DIR}"

# Step 1: Deploy Infrastructure
echo -e "${GREEN}Step 1/3: Deploying infrastructure...${NC}"
echo ""
./scripts/deploy_ecs.sh

if [ $? -ne 0 ]; then
    echo -e "${RED}Infrastructure deployment failed!${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}Infrastructure deployed successfully!${NC}"
echo ""
sleep 2

# Step 2: Build and Push Docker Image
echo -e "${GREEN}Step 2/3: Building and pushing Docker image...${NC}"
echo ""
./scripts/build_and_push.sh

if [ $? -ne 0 ]; then
    echo -e "${RED}Docker build/push failed!${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}Docker image built and pushed successfully!${NC}"
echo ""
sleep 2

# Step 3: Update ECS Service
echo -e "${GREEN}Step 3/3: Updating ECS service...${NC}"
echo ""
./scripts/update_ecs_service.sh

if [ $? -ne 0 ]; then
    echo -e "${RED}ECS service update failed!${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Get stack info
STACK_NAME="${STACK_NAME:-stock-ecs-consumer}"
AWS_REGION="${AWS_REGION:-us-east-1}"

echo -e "${CYAN}Stack Outputs:${NC}"
aws cloudformation describe-stacks \
    --stack-name "${STACK_NAME}" \
    --query 'Stacks[0].Outputs' \
    --output table \
    --region "${AWS_REGION}" 2>/dev/null || echo "Could not retrieve stack outputs"

echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo ""
echo -e "  ${GREEN}✓${NC} Infrastructure deployed"
echo -e "  ${GREEN}✓${NC} Docker image built and pushed"
echo -e "  ${GREEN}✓${NC} ECS service updated"
echo ""
echo -e "${YELLOW}Monitor your deployment:${NC}"
echo -e "  1. View logs:    ./scripts/view_ecs_logs.sh"
echo -e "  2. Check status: ./scripts/ecs_status.sh"
echo -e "  3. Query data:   ./scripts/query_analytics.sh AAPL 10"
echo ""
echo -e "${YELLOW}Service Schedule:${NC}"
echo -e "  • Starts: 9:15 AM ET (Monday-Friday)"
echo -e "  • Stops:  4:15 PM ET (Monday-Friday)"
echo ""
echo -e "${YELLOW}Manual control:${NC}"
echo -e "  • Start now:  ./scripts/start_service.sh"
echo -e "  • Stop now:   ./scripts/stop_service.sh"
echo ""
