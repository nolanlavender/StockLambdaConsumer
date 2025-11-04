#!/bin/bash

# Stock ECS Consumer - Check Service Status

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
STACK_NAME="${STACK_NAME:-stock-ecs-consumer}"
AWS_REGION="${AWS_REGION:-us-east-1}"

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}ECS Service Status${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# Get cluster and service names
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

# Get service status
echo -e "${GREEN}Service Details:${NC}"
aws ecs describe-services \
    --cluster "${CLUSTER_NAME}" \
    --services "${SERVICE_NAME}" \
    --region "${AWS_REGION}" \
    --query 'services[0].{
        Status: status,
        DesiredCount: desiredCount,
        RunningCount: runningCount,
        PendingCount: pendingCount,
        LaunchType: launchType,
        CreatedAt: createdAt
    }' \
    --output table

echo ""
echo -e "${GREEN}Recent Events:${NC}"
aws ecs describe-services \
    --cluster "${CLUSTER_NAME}" \
    --services "${SERVICE_NAME}" \
    --region "${AWS_REGION}" \
    --query 'services[0].events[:5]' \
    --output table

echo ""
echo -e "${GREEN}Tasks:${NC}"
TASK_ARNS=$(aws ecs list-tasks \
    --cluster "${CLUSTER_NAME}" \
    --service-name "${SERVICE_NAME}" \
    --region "${AWS_REGION}" \
    --query 'taskArns' \
    --output text)

if [ -z "$TASK_ARNS" ]; then
    echo -e "${YELLOW}No tasks running${NC}"
else
    aws ecs describe-tasks \
        --cluster "${CLUSTER_NAME}" \
        --tasks ${TASK_ARNS} \
        --region "${AWS_REGION}" \
        --query 'tasks[].{
            TaskId: taskArn,
            Status: lastStatus,
            DesiredStatus: desiredStatus,
            CPU: cpu,
            Memory: memory,
            CreatedAt: createdAt
        }' \
        --output table
fi
