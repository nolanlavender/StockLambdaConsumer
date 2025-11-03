#!/bin/bash

# Stock Lambda Consumer - Query Analytics Script
# Queries recent analytics from DynamoDB

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
TABLE_NAME="${DYNAMODB_TABLE_NAME:-stock-analytics}"
AWS_REGION="${AWS_REGION:-us-east-1}"
SYMBOL="${1:-AAPL}"
LIMIT="${2:-10}"

echo -e "${GREEN}Querying analytics for ${SYMBOL} (last ${LIMIT} records)...${NC}"
echo ""

aws dynamodb query \
    --table-name "${TABLE_NAME}" \
    --key-condition-expression "symbol = :symbol" \
    --expression-attribute-values "{\":symbol\":{\"S\":\"${SYMBOL}\"}}" \
    --scan-index-forward false \
    --limit "${LIMIT}" \
    --region "${AWS_REGION}" \
    --output table

echo ""
echo -e "${YELLOW}Usage: $0 <SYMBOL> <LIMIT>${NC}"
echo "Example: $0 AAPL 20"
