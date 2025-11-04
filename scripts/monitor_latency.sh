#!/bin/bash

# Stock Lambda Consumer - Latency Monitor
# Monitor processing latency from CloudWatch logs

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m' # No Color

FUNCTION_NAME="${1:-stock-lambda-consumer-StockAnalyticsProcessor}"
DURATION="${2:-5m}"

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}Processing Latency Monitor${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

echo -e "${GREEN}Monitoring latency for last ${DURATION}...${NC}"
echo ""

# Get full function name if partial match
FULL_FUNCTION_NAME=$(aws lambda list-functions \
    --query "Functions[?contains(FunctionName, '${FUNCTION_NAME}')].FunctionName" \
    --output text 2>/dev/null | head -1)

if [ -z "$FULL_FUNCTION_NAME" ]; then
    echo -e "${RED}Could not find function matching: ${FUNCTION_NAME}${NC}"
    exit 1
fi

LOG_GROUP="/aws/lambda/${FULL_FUNCTION_NAME}"

echo -e "${CYAN}Function: ${FULL_FUNCTION_NAME}${NC}"
echo -e "${CYAN}Log Group: ${LOG_GROUP}${NC}"
echo ""

# Extract latency statistics from logs
echo -e "${GREEN}=== Batch Latency Statistics ===${NC}"
aws logs tail "${LOG_GROUP}" \
    --since "${DURATION}" \
    --format short \
    --filter-pattern "Processing Latency" \
    | grep "⏱️" \
    | tail -20

echo ""
echo -e "${GREEN}=== Per-Record Latency (Last 20) ===${NC}"
aws logs tail "${LOG_GROUP}" \
    --since "${DURATION}" \
    --format short \
    --filter-pattern "latency=" \
    | grep "latency=" \
    | tail -20

echo ""
echo -e "${GREEN}=== High Latency Warnings ===${NC}"
aws logs tail "${LOG_GROUP}" \
    --since "${DURATION}" \
    --format short \
    --filter-pattern "High processing latency" \
    | grep "⚠️" \
    || echo -e "${GREEN}No high latency warnings${NC}"

echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${YELLOW}Usage: $0 [FUNCTION_NAME] [DURATION]${NC}"
echo "Examples:"
echo "  $0                           # Default: processor, 5m"
echo "  $0 processor 10m             # Last 10 minutes"
echo "  $0 processor 1h              # Last hour"
