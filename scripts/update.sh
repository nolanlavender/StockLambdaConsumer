#!/bin/bash

# Stock Lambda Consumer - Update Script
# Updates the existing stack with code/configuration changes
# NO teardown needed - preserves DynamoDB data and all resources

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}Stock Lambda Consumer - Update${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

echo -e "${GREEN}This script updates your existing stack WITHOUT tearing down resources.${NC}"
echo ""
echo -e "${GREEN}What will be updated:${NC}"
echo "  ✓ Lambda function code"
echo "  ✓ Lambda configuration (memory, timeout, env vars)"
echo "  ✓ CloudWatch log settings"
echo "  ✓ EventBridge rules"
echo ""
echo -e "${GREEN}What will NOT be changed:${NC}"
echo "  ✓ DynamoDB table (data is preserved)"
echo "  ✓ Kinesis event source mapping (keeps state)"
echo "  ✓ IAM roles and permissions"
echo "  ✓ S3 deployment bucket"
echo ""

# Check if stack exists
STACK_NAME="${STACK_NAME:-stock-lambda-consumer}"
AWS_REGION="${AWS_REGION:-us-east-1}"

STACK_STATUS=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --query "Stacks[0].StackStatus" \
    --output text \
    --region "$AWS_REGION" 2>/dev/null || echo "NOT_FOUND")

if [ "$STACK_STATUS" = "NOT_FOUND" ]; then
    echo -e "${YELLOW}⚠ Stack '${STACK_NAME}' not found.${NC}"
    echo ""
    echo "This appears to be a fresh deployment. Use deploy.sh instead:"
    echo "  ./scripts/deploy.sh"
    echo ""
    exit 1
fi

echo -e "${GREEN}Existing stack found:${NC} ${STACK_NAME} (${STACK_STATUS})"
echo ""

# Ask for confirmation
read -p "Continue with update? (yes/no): " -r
echo

if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo -e "${YELLOW}Update cancelled${NC}"
    exit 0
fi

echo ""
echo -e "${CYAN}Starting update...${NC}"
echo ""

# Call the deploy script (which handles updates)
./scripts/deploy.sh

UPDATE_EXIT_CODE=$?

if [ $UPDATE_EXIT_CODE -eq 0 ]; then
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}Update successful!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "${GREEN}Your changes have been deployed.${NC}"
    echo ""
    echo -e "${CYAN}Next steps:${NC}"
    echo "  1. Monitor logs to see changes in action:"
    echo "     ./scripts/monitor_logs.sh processor"
    echo ""
    echo "  2. Verify Lambda function was updated:"
    echo "     aws lambda get-function --function-name stock-lambda-consumer-StockAnalyticsProcessor"
    echo ""
    echo "  3. Check DynamoDB data is still intact:"
    echo "     ./scripts/query_analytics.sh AAPL 5"
    echo ""
else
    echo ""
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}Update failed!${NC}"
    echo -e "${RED}========================================${NC}"
    echo ""
    echo -e "${YELLOW}Don't worry - your existing resources are safe.${NC}"
    echo ""
    echo "To retry, simply run:"
    echo "  ./scripts/update.sh"
    echo ""
    echo "To rollback to previous version:"
    echo "  git checkout <previous-commit>"
    echo "  ./scripts/update.sh"
    echo ""
    exit 1
fi
