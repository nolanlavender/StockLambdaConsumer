#!/bin/bash

# Stock ECS Consumer - Build and Push Docker Image

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}Docker Build and Push to ECR${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# Configuration
STACK_NAME="${STACK_NAME:-stock-ecs-consumer}"
AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Get ECR repository URI from CloudFormation stack
echo -e "${GREEN}Getting ECR repository URI...${NC}"
ECR_URI=$(aws cloudformation describe-stacks \
    --stack-name "${STACK_NAME}" \
    --query "Stacks[0].Outputs[?OutputKey=='ECRRepositoryUri'].OutputValue" \
    --output text \
    --region "${AWS_REGION}" 2>/dev/null || echo "")

if [ -z "$ECR_URI" ]; then
    echo -e "${RED}Could not get ECR URI from stack. Make sure stack is deployed first.${NC}"
    echo -e "${YELLOW}Run: ./scripts/deploy_ecs.sh${NC}"
    exit 1
fi

echo -e "${GREEN}ECR Repository: ${ECR_URI}${NC}"
echo ""

# Login to ECR
echo -e "${GREEN}Logging in to ECR...${NC}"
aws ecr get-login-password --region "${AWS_REGION}" | \
    docker login --username AWS --password-stdin "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

# Build Docker image
echo ""
echo -e "${GREEN}Building Docker image...${NC}"
docker build -t "${STACK_NAME}:latest" -f Dockerfile .

# Tag image for ECR
echo ""
echo -e "${GREEN}Tagging image...${NC}"
docker tag "${STACK_NAME}:latest" "${ECR_URI}:latest"
docker tag "${STACK_NAME}:latest" "${ECR_URI}:$(date +%Y%m%d-%H%M%S)"

# Push to ECR
echo ""
echo -e "${GREEN}Pushing to ECR...${NC}"
docker push "${ECR_URI}:latest"
docker push "${ECR_URI}:$(date +%Y%m%d-%H%M%S)"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Build and push complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${CYAN}Image pushed to: ${ECR_URI}${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo -e "  1. Update ECS service: ./scripts/update_ecs_service.sh"
echo -e "  2. View logs: ./scripts/view_ecs_logs.sh"
