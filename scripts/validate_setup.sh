#!/bin/bash

# Stock Lambda Consumer - Validation Script
# Validates the setup before deployment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Stock Lambda Consumer - Setup Validation${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

ERRORS=0
WARNINGS=0

# Check AWS CLI
echo -e "${GREEN}Checking AWS CLI...${NC}"
if command -v aws >/dev/null 2>&1; then
    AWS_VERSION=$(aws --version 2>&1 | head -1)
    echo -e "  ✓ AWS CLI installed: ${AWS_VERSION}"
else
    echo -e "  ${RED}✗ AWS CLI not found${NC}"
    ERRORS=$((ERRORS + 1))
fi

# Check SAM CLI
echo -e "${GREEN}Checking SAM CLI...${NC}"
if command -v sam >/dev/null 2>&1; then
    SAM_VERSION=$(sam --version 2>&1)
    echo -e "  ✓ SAM CLI installed: ${SAM_VERSION}"
else
    echo -e "  ${RED}✗ SAM CLI not found${NC}"
    ERRORS=$((ERRORS + 1))
fi

# Check AWS credentials
echo -e "${GREEN}Checking AWS credentials...${NC}"
if aws sts get-caller-identity >/dev/null 2>&1; then
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    CALLER_ARN=$(aws sts get-caller-identity --query Arn --output text)
    echo -e "  ✓ AWS credentials configured"
    echo -e "    Account: ${ACCOUNT_ID}"
    echo -e "    Identity: ${CALLER_ARN}"
else
    echo -e "  ${RED}✗ AWS credentials not configured${NC}"
    ERRORS=$((ERRORS + 1))
fi

# Check AWS region
echo -e "${GREEN}Checking AWS region...${NC}"
AWS_REGION="${AWS_REGION:-us-east-1}"
echo -e "  ✓ Region: ${AWS_REGION}"

# Check for producer stack
echo -e "${GREEN}Checking for producer stack...${NC}"
PRODUCER_STACK_NAME="${PRODUCER_STACK_NAME:-stock-lambda-producer}"
STACK_STATUS=$(aws cloudformation describe-stacks \
    --stack-name "$PRODUCER_STACK_NAME" \
    --query "Stacks[0].StackStatus" \
    --output text \
    --region "$AWS_REGION" 2>/dev/null || echo "NOT_FOUND")

if [ "$STACK_STATUS" = "NOT_FOUND" ]; then
    echo -e "  ${YELLOW}⚠ Producer stack '${PRODUCER_STACK_NAME}' not found${NC}"
    echo -e "    You'll need to set KINESIS_STREAM_NAME and KINESIS_STREAM_ARN manually"
    WARNINGS=$((WARNINGS + 1))
else
    echo -e "  ✓ Producer stack found: ${PRODUCER_STACK_NAME} (${STACK_STATUS})"

    # Get Kinesis stream info
    KINESIS_STREAM_NAME=$(aws cloudformation describe-stacks \
        --stack-name "$PRODUCER_STACK_NAME" \
        --query "Stacks[0].Outputs[?OutputKey=='KinesisStreamName'].OutputValue" \
        --output text \
        --region "$AWS_REGION" 2>/dev/null || echo "")

    KINESIS_STREAM_ARN=$(aws cloudformation describe-stacks \
        --stack-name "$PRODUCER_STACK_NAME" \
        --query "Stacks[0].Outputs[?OutputKey=='KinesisStreamArn'].OutputValue" \
        --output text \
        --region "$AWS_REGION" 2>/dev/null || echo "")

    if [ -n "$KINESIS_STREAM_NAME" ] && [ "$KINESIS_STREAM_NAME" != "None" ]; then
        echo -e "  ✓ Kinesis Stream Name: ${KINESIS_STREAM_NAME}"
        echo -e "  ✓ Kinesis Stream ARN: ${KINESIS_STREAM_ARN}"

        # Verify stream exists
        if aws kinesis describe-stream --stream-name "$KINESIS_STREAM_NAME" --region "$AWS_REGION" >/dev/null 2>&1; then
            echo -e "  ✓ Kinesis stream verified and accessible"
        else
            echo -e "  ${RED}✗ Kinesis stream not accessible${NC}"
            ERRORS=$((ERRORS + 1))
        fi
    else
        echo -e "  ${YELLOW}⚠ Producer stack has no Kinesis outputs${NC}"
        WARNINGS=$((WARNINGS + 1))
    fi
fi

# Check for existing consumer stack
echo -e "${GREEN}Checking for existing consumer stack...${NC}"
CONSUMER_STACK_NAME="${STACK_NAME:-stock-lambda-consumer}"
CONSUMER_STATUS=$(aws cloudformation describe-stacks \
    --stack-name "$CONSUMER_STACK_NAME" \
    --query "Stacks[0].StackStatus" \
    --output text \
    --region "$AWS_REGION" 2>/dev/null || echo "NOT_FOUND")

if [ "$CONSUMER_STATUS" = "NOT_FOUND" ]; then
    echo -e "  ✓ No existing consumer stack (fresh deployment)"
else
    echo -e "  ${YELLOW}⚠ Consumer stack already exists: ${CONSUMER_STACK_NAME} (${CONSUMER_STATUS})${NC}"
    echo -e "    Deployment will update the existing stack"
    WARNINGS=$((WARNINGS + 1))
fi

# Check S3 bucket
echo -e "${GREEN}Checking S3 deployment bucket...${NC}"
if [ -n "$S3_BUCKET" ]; then
    echo -e "  S3_BUCKET set to: ${S3_BUCKET}"
    if aws s3 ls "s3://${S3_BUCKET}" >/dev/null 2>&1; then
        echo -e "  ✓ S3 bucket exists and accessible"
    else
        echo -e "  ${YELLOW}⚠ S3 bucket not accessible (will be created)${NC}"
        WARNINGS=$((WARNINGS + 1))
    fi
else
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo "unknown")
    DEFAULT_BUCKET="sam-deployments-${ACCOUNT_ID}-${AWS_REGION}"
    echo -e "  S3_BUCKET not set (will use: ${DEFAULT_BUCKET})"

    if aws s3 ls "s3://${DEFAULT_BUCKET}" >/dev/null 2>&1; then
        echo -e "  ✓ Default bucket exists"
    else
        echo -e "  ${YELLOW}⚠ Default bucket will be created${NC}"
        WARNINGS=$((WARNINGS + 1))
    fi
fi

# Summary
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Validation Summary${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

if [ $ERRORS -gt 0 ]; then
    echo -e "${RED}✗ ${ERRORS} error(s) found${NC}"
    echo ""
    echo "Please fix the errors above before deploying."
    exit 1
elif [ $WARNINGS -gt 0 ]; then
    echo -e "${YELLOW}⚠ ${WARNINGS} warning(s) found${NC}"
    echo ""
    echo "You can proceed with deployment, but review the warnings above."
    echo ""
    echo "To deploy, run:"
    echo "  ./scripts/deploy.sh"
else
    echo -e "${GREEN}✓ All checks passed!${NC}"
    echo ""
    echo "Everything looks good. Ready to deploy!"
    echo ""
    echo "To deploy, run:"
    echo "  ./scripts/deploy.sh"
fi

echo ""
