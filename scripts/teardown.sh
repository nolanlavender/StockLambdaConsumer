#!/bin/bash

# Stock ECS Consumer - Teardown Script
# WARNING: This will DELETE all resources and data!

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${RED}========================================${NC}"
echo -e "${RED}Stock ECS Consumer - TEARDOWN${NC}"
echo -e "${RED}========================================${NC}"
echo ""
echo -e "${RED}WARNING: This will DELETE:${NC}"
echo -e "  • ECS Service and Tasks"
echo -e "  • ECS Cluster"
echo -e "  • ECR Repository and all images"
echo -e "  • S3 Bucket and all state files"
echo -e "  • DynamoDB Table and ALL data"
echo -e "  • VPC, Subnets, Security Groups"
echo -e "  • CloudWatch Log Groups"
echo -e "  • IAM Roles"
echo -e "  • EventBridge Schedulers"
echo ""
echo -e "${RED}This action CANNOT be undone!${NC}"
echo ""

# Confirmation
read -p "Are you sure you want to proceed? (type 'yes' to confirm): " confirmation

if [ "$confirmation" != "yes" ]; then
    echo -e "${GREEN}Teardown cancelled.${NC}"
    exit 0
fi

echo ""
read -p "Really delete ALL data including DynamoDB analytics? (type 'DELETE' to confirm): " confirmation2

if [ "$confirmation2" != "DELETE" ]; then
    echo -e "${GREEN}Teardown cancelled.${NC}"
    exit 0
fi

# Configuration
STACK_NAME="${STACK_NAME:-stock-ecs-consumer}"
AWS_REGION="${AWS_REGION:-us-east-1}"

echo ""
echo -e "${YELLOW}Proceeding with teardown...${NC}"
echo ""

# Step 1: Stop ECS Service (set desired count to 0)
echo -e "${GREEN}Step 1/5: Stopping ECS service...${NC}"

CLUSTER_NAME=$(aws cloudformation describe-stacks \
    --stack-name "${STACK_NAME}" \
    --query "Stacks[0].Outputs[?OutputKey=='ECSClusterName'].OutputValue" \
    --output text \
    --region "${AWS_REGION}" 2>/dev/null || echo "")

SERVICE_NAME=$(aws cloudformation describe-stacks \
    --stack-name "${STACK_NAME}" \
    --query "Stacks[0].Outputs[?OutputKey=='ECSServiceName'].OutputValue" \
    --output text \
    --region "${AWS_REGION}" 2>/dev/null || echo "")

if [ -n "$CLUSTER_NAME" ] && [ -n "$SERVICE_NAME" ]; then
    echo "Stopping service ${SERVICE_NAME}..."
    aws ecs update-service \
        --cluster "${CLUSTER_NAME}" \
        --service "${SERVICE_NAME}" \
        --desired-count 0 \
        --region "${AWS_REGION}" > /dev/null 2>&1 || true

    echo "Waiting for tasks to stop..."
    sleep 10
else
    echo "Service not found, skipping..."
fi

# Step 2: Empty S3 Bucket
echo ""
echo -e "${GREEN}Step 2/5: Emptying S3 bucket...${NC}"

BUCKET_NAME=$(aws cloudformation describe-stacks \
    --stack-name "${STACK_NAME}" \
    --query "Stacks[0].Outputs[?OutputKey=='StateBucketName'].OutputValue" \
    --output text \
    --region "${AWS_REGION}" 2>/dev/null || echo "")

if [ -n "$BUCKET_NAME" ] && [ "$BUCKET_NAME" != "None" ]; then
    echo "Deleting objects from s3://${BUCKET_NAME}..."
    aws s3 rm s3://${BUCKET_NAME} --recursive --region "${AWS_REGION}" 2>/dev/null || true
    echo "S3 bucket emptied"
else
    echo "S3 bucket not found, skipping..."
fi

# Step 3: Delete ECR Images
echo ""
echo -e "${GREEN}Step 3/5: Deleting ECR images...${NC}"

ECR_REPO=$(aws cloudformation describe-stacks \
    --stack-name "${STACK_NAME}" \
    --query "Stacks[0].Outputs[?OutputKey=='ECRRepositoryUri'].OutputValue" \
    --output text \
    --region "${AWS_REGION}" 2>/dev/null | cut -d'/' -f2 || echo "")

if [ -n "$ECR_REPO" ] && [ "$ECR_REPO" != "None" ]; then
    echo "Deleting images from repository ${ECR_REPO}..."

    # Get image IDs
    IMAGE_IDS=$(aws ecr list-images \
        --repository-name "${ECR_REPO}" \
        --query 'imageIds[*]' \
        --output json \
        --region "${AWS_REGION}" 2>/dev/null || echo "[]")

    if [ "$IMAGE_IDS" != "[]" ]; then
        aws ecr batch-delete-image \
            --repository-name "${ECR_REPO}" \
            --image-ids "${IMAGE_IDS}" \
            --region "${AWS_REGION}" > /dev/null 2>&1 || true
        echo "ECR images deleted"
    else
        echo "No images to delete"
    fi
else
    echo "ECR repository not found, skipping..."
fi

# Step 4: Delete CloudFormation Stack
echo ""
echo -e "${GREEN}Step 4/5: Deleting CloudFormation stack...${NC}"

echo "Deleting stack ${STACK_NAME}..."
aws cloudformation delete-stack \
    --stack-name "${STACK_NAME}" \
    --region "${AWS_REGION}"

echo "Waiting for stack deletion to complete (this may take 5-10 minutes)..."
aws cloudformation wait stack-delete-complete \
    --stack-name "${STACK_NAME}" \
    --region "${AWS_REGION}" 2>&1 || {
    echo -e "${YELLOW}Stack deletion may still be in progress. Check AWS Console.${NC}"
}

# Step 5: Delete CloudWatch Log Groups (in case stack deletion didn't clean them up)
echo ""
echo -e "${GREEN}Step 5/5: Cleaning up CloudWatch logs...${NC}"

LOG_GROUP="/ecs/${STACK_NAME}-consumer"
aws logs delete-log-group \
    --log-group-name "${LOG_GROUP}" \
    --region "${AWS_REGION}" 2>/dev/null || echo "Log group already deleted"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Teardown Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${CYAN}All resources have been deleted:${NC}"
echo -e "  ${GREEN}✓${NC} ECS Service stopped and deleted"
echo -e "  ${GREEN}✓${NC} ECS Cluster deleted"
echo -e "  ${GREEN}✓${NC} ECR Repository and images deleted"
echo -e "  ${GREEN}✓${NC} S3 Bucket and state files deleted"
echo -e "  ${GREEN}✓${NC} DynamoDB Table and data deleted"
echo -e "  ${GREEN}✓${NC} VPC and networking resources deleted"
echo -e "  ${GREEN}✓${NC} IAM Roles deleted"
echo -e "  ${GREEN}✓${NC} EventBridge Schedulers deleted"
echo -e "  ${GREEN}✓${NC} CloudWatch Log Groups deleted"
echo ""
echo -e "${YELLOW}Note: It may take a few minutes for all AWS resources to fully terminate.${NC}"
echo ""
