#!/bin/bash

# Stock Lambda Consumer - Analytics Inspector
# Shows detailed analytics data from DynamoDB

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
TABLE_NAME="${DYNAMODB_TABLE_NAME:-stock-analytics}"
AWS_REGION="${AWS_REGION:-us-east-1}"
SYMBOL="${1:-AAPL}"
LIMIT="${2:-1}"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Stock Analytics Inspector${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

echo -e "${CYAN}Fetching latest analytics for ${SYMBOL}...${NC}"
echo ""

# Query the latest record
QUERY_OUTPUT=$(aws dynamodb query \
    --table-name "${TABLE_NAME}" \
    --key-condition-expression "symbol = :symbol" \
    --expression-attribute-values "{\":symbol\":{\"S\":\"${SYMBOL}\"}}" \
    --scan-index-forward false \
    --limit "${LIMIT}" \
    --region "${AWS_REGION}" \
    --output json 2>&1)

if [ $? -ne 0 ]; then
    echo -e "${YELLOW}Error querying DynamoDB:${NC}"
    echo "$QUERY_OUTPUT"
    exit 1
fi

# Parse and display the results
echo "$QUERY_OUTPUT" | python3 -c "
import json
import sys
from datetime import datetime

try:
    data = json.load(sys.stdin)
    items = data.get('Items', [])

    if not items:
        print('No data found for symbol: ${SYMBOL}')
        sys.exit(0)

    for idx, item in enumerate(items):
        print(f'${GREEN}Record #{idx+1}${NC}')
        print('=' * 80)

        # Basic Info
        print(f'\n${CYAN}📊 Basic Information${NC}')
        print(f'  Symbol:           {item.get(\"symbol\", {}).get(\"S\", \"N/A\")}')
        print(f'  Timestamp:        {item.get(\"timestamp\", {}).get(\"S\", \"N/A\")}')
        print(f'  Date:             {item.get(\"date\", {}).get(\"S\", \"N/A\")}')
        print(f'  Current Price:    \${item.get(\"current_price\", {}).get(\"N\", \"N/A\")}')

        # Raw Data
        print(f'\n${CYAN}📈 Raw Market Data${NC}')
        print(f'  Change:           {item.get(\"change\", {}).get(\"N\", \"N/A\")}')
        print(f'  Change %:         {item.get(\"change_percent\", {}).get(\"S\", \"N/A\")}%')
        print(f'  High:             \${item.get(\"high\", {}).get(\"N\", \"N/A\")}')
        print(f'  Low:              \${item.get(\"low\", {}).get(\"N\", \"N/A\")}')
        print(f'  Open:             \${item.get(\"open\", {}).get(\"N\", \"N/A\")}')
        print(f'  Previous Close:   \${item.get(\"previous_close\", {}).get(\"N\", \"N/A\")}')

        # Intraday Metrics
        print(f'\n${CYAN}🕐 Intraday Metrics${NC}')
        print(f'  Change from Open:        {item.get(\"intraday_change_from_open\", {}).get(\"N\", \"N/A\")}')
        print(f'  Change from Open %:      {item.get(\"intraday_change_from_open_percent\", {}).get(\"N\", \"N/A\")}%')
        if 'gap' in item:
            print(f'  Gap:                     {item.get(\"gap\", {}).get(\"N\", \"N/A\")}')
            print(f'  Gap %:                   {item.get(\"gap_percent\", {}).get(\"N\", \"N/A\")}%')
            print(f'  Gap Type:                {item.get(\"gap_type\", {}).get(\"S\", \"N/A\")}')

        # Time Window Analytics
        print(f'\n${CYAN}⏱️  Time Window Analytics${NC}')
        windows = ['1', '5', '15', '30', '60', '120']
        for w in windows:
            change_key = f'change_{w}min'
            if change_key in item:
                change = item.get(change_key, {}).get('N', 'N/A')
                change_pct = item.get(f'change_{w}min_percent', {}).get('N', 'N/A')
                high = item.get(f'high_{w}min', {}).get('N', 'N/A')
                low = item.get(f'low_{w}min', {}).get('N', 'N/A')
                volume = item.get(f'volume_{w}min', {}).get('N', 'N/A')
                print(f'  {w}min: change={change}, change%={change_pct}, high={high}, low={low}, vol={volume}')

        # Moving Averages
        print(f'\n${CYAN}📉 Moving Averages${NC}')
        ma_windows = ['5', '15', '30', '60']
        for w in ma_windows:
            ma_key = f'ma_{w}min'
            if ma_key in item:
                ma = item.get(ma_key, {}).get('N', 'N/A')
                print(f'  MA-{w}min:        \${ma}')

        # Volatility & Momentum
        print(f'\n${CYAN}🎯 Volatility & Momentum${NC}')
        print(f'  Volatility:              {item.get(\"volatility\", {}).get(\"N\", \"N/A\")}')
        print(f'  Volatility (Annualized): {item.get(\"volatility_annualized\", {}).get(\"N\", \"N/A\")}')
        print(f'  Momentum:                {item.get(\"momentum\", {}).get(\"N\", \"N/A\")}')
        print(f'  Price Acceleration:      {item.get(\"price_acceleration\", {}).get(\"N\", \"N/A\")}')

        # Trading Signal
        print(f'\n${CYAN}🚦 Trading Signal${NC}')
        signal = item.get('trading_signal', {}).get('S', 'N/A')
        signal_color = '${GREEN}' if signal == 'BUY' else '${YELLOW}' if signal == 'HOLD' else '\033[0;31m'
        print(f'  Signal:    {signal_color}{signal}${NC}')
        print(f'  Reason:    {item.get(\"signal_reason\", {}).get(\"S\", \"N/A\")}')

        # TTL
        print(f'\n${CYAN}⚙️  Metadata${NC}')
        ttl = item.get('ttl', {}).get('N', 'N/A')
        if ttl != 'N/A':
            ttl_date = datetime.fromtimestamp(int(ttl))
            print(f'  TTL Expiry:       {ttl_date.strftime(\"%Y-%m-%d %H:%M:%S\")}')

        # Count total fields
        total_fields = len(item)
        print(f'\n${CYAN}Total Fields Stored: {total_fields}${NC}')
        print('=' * 80)
        print()

except json.JSONDecodeError as e:
    print(f'Error parsing JSON: {e}')
    sys.exit(1)
except Exception as e:
    print(f'Error: {e}')
    sys.exit(1)
"

echo ""
echo -e "${GREEN}To see all fields in raw format:${NC}"
echo "  aws dynamodb get-item --table-name ${TABLE_NAME} --key '{\"symbol\":{\"S\":\"${SYMBOL}\"},\"timestamp\":{\"S\":\"TIMESTAMP\"}}' --region ${AWS_REGION}"
echo ""
echo -e "${YELLOW}Usage: $0 <SYMBOL> <LIMIT>${NC}"
echo "  Example: $0 AAPL 3"
