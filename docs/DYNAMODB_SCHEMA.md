# DynamoDB Schema - Stock Analytics

This document details all the fields stored in the DynamoDB table for stock analytics.

## Table Overview

- **Table Name**: `stock-analytics` (configurable)
- **Partition Key**: `symbol` (String)
- **Sort Key**: `timestamp` (String, ISO 8601 format)
- **TTL Attribute**: `ttl` (Number, Unix timestamp)
- **Retention**: 7 days (configurable)

## Global Secondary Index

- **Index Name**: `DateIndex`
- **Partition Key**: `symbol` (String)
- **Sort Key**: `date` (String, YYYY-MM-DD format)

## Complete Field List

### 1. Primary Keys (Required)

| Field | Type | Example | Description |
|-------|------|---------|-------------|
| `symbol` | String | `"AAPL"` | Stock ticker symbol |
| `timestamp` | String | `"2025-11-03T17:19:39.193597"` | ISO 8601 timestamp |

### 2. Basic Information

| Field | Type | Example | Description |
|-------|------|---------|-------------|
| `date` | String | `"2025-11-03"` | Trading date (YYYY-MM-DD) |
| `current_price` | Number | `268.04` | Current stock price |

### 3. Raw Market Data (from Kinesis)

| Field | Type | Example | Description |
|-------|------|---------|-------------|
| `change` | Number | `-2.33` | Price change from previous close |
| `change_percent` | String | `"-0.86"` | Percentage change |
| `high` | Number | `270.85` | Day's high price |
| `low` | Number | `266.25` | Day's low price |
| `open` | Number | `269.7` | Opening price |
| `previous_close` | Number | `270.37` | Previous day's closing price |

### 4. Intraday Metrics

| Field | Type | Example | Description |
|-------|------|---------|-------------|
| `intraday_change_from_open` | Number | `-1.66` | Change from today's open |
| `intraday_change_from_open_percent` | Number | `-0.62` | Percentage change from open |

### 5. Gap Analysis (if previous day data available)

| Field | Type | Example | Description |
|-------|------|---------|-------------|
| `gap` | Number | `-0.67` | Gap between today's open and yesterday's close |
| `gap_percent` | Number | `-0.25` | Gap as percentage |
| `gap_type` | String | `"gap_down"` | Type: `gap_up`, `gap_down`, or `no_gap` |
| `breakout_above_prev_high` | Boolean | `true` | Price broke above yesterday's high |
| `breakout_percent` | Number | `1.2` | Breakout percentage |
| `breakdown_below_prev_low` | Boolean | `true` | Price broke below yesterday's low |
| `breakdown_percent` | Number | `1.5` | Breakdown percentage |

### 6. Time Window Analytics

For each configured time window (default: 1, 5, 15, 30, 60, 120 minutes):

| Field Pattern | Type | Example | Description |
|---------------|------|---------|-------------|
| `change_Xmin` | Number | `1.04` | Price change over X minutes |
| `change_Xmin_percent` | Number | `0.39` | Percentage change over X minutes |
| `high_Xmin` | Number | `268.5` | Highest price in X minute window |
| `low_Xmin` | Number | `266.8` | Lowest price in X minute window |
| `range_Xmin` | Number | `1.7` | Price range in X minute window |
| `volume_Xmin` | Number | `42` | Number of updates in X minute window |

**Example fields:**
- `change_5min`, `change_5min_percent`, `high_5min`, `low_5min`, `range_5min`, `volume_5min`
- `change_15min`, `change_15min_percent`, `high_15min`, `low_15min`, `range_15min`, `volume_15min`
- `change_30min`, `change_30min_percent`, etc.
- `change_60min`, `change_60min_percent`, etc.
- `change_120min`, `change_120min_percent`, etc.

### 7. Moving Averages

For each configured MA window (default: 5, 15, 30, 60 minutes):

| Field Pattern | Type | Example | Description |
|---------------|------|---------|-------------|
| `ma_Xmin` | Number | `267.51` | Moving average over X minutes |

**Example fields:**
- `ma_5min` - 5-minute moving average
- `ma_15min` - 15-minute moving average
- `ma_30min` - 30-minute moving average
- `ma_60min` - 60-minute moving average (1 hour)

### 8. Volatility & Momentum Indicators

| Field | Type | Example | Description |
|-------|------|---------|-------------|
| `volatility` | Number | `0.0123` | Standard deviation of returns |
| `volatility_annualized` | Number | `0.1953` | Annualized volatility |
| `momentum` | Number | `0.0089` | Rate of change (momentum) |
| `price_acceleration` | Number | `0.0012` | Second derivative (acceleration) |

### 9. Trading Signals

| Field | Type | Example | Description |
|-------|------|---------|-------------|
| `trading_signal` | String | `"BUY"` | Signal: `BUY`, `HOLD`, or `SELL` |
| `signal_reason` | String | `"Positive momentum..."` | Human-readable reason for signal |

### 10. Metadata

| Field | Type | Example | Description |
|-------|------|---------|-------------|
| `ttl` | Number | `1730923179` | Unix timestamp for TTL expiration |

## Total Fields

**Typical record contains 40-60+ fields** depending on:
- Whether historical data is available (adds gap analysis fields)
- Number of time windows configured
- Number of MA windows configured
- Breakout/breakdown conditions met

### Field Count Breakdown

| Category | Typical Count |
|----------|---------------|
| Primary Keys | 2 |
| Basic Info | 2 |
| Raw Market Data | 6 |
| Intraday Metrics | 2 |
| Gap Analysis | 0-7 (conditional) |
| Time Window Analytics | 36 (6 windows × 6 metrics) |
| Moving Averages | 4 |
| Volatility & Momentum | 4 |
| Trading Signals | 2 |
| Metadata | 1 |
| **Total** | **~59-66 fields** |

## Example Record (JSON)

```json
{
  "symbol": "AAPL",
  "timestamp": "2025-11-03T17:19:39.193597",
  "date": "2025-11-03",
  "current_price": 268.04,

  "change": -2.33,
  "change_percent": "-0.86",
  "high": 270.85,
  "low": 266.25,
  "open": 269.7,
  "previous_close": 270.37,

  "intraday_change_from_open": -1.66,
  "intraday_change_from_open_percent": -0.62,

  "gap": -0.67,
  "gap_percent": -0.25,
  "gap_type": "gap_down",

  "change_1min": 0.15,
  "change_1min_percent": 0.06,
  "high_1min": 268.10,
  "low_1min": 267.95,
  "range_1min": 0.15,
  "volume_1min": 3,

  "change_5min": 1.04,
  "change_5min_percent": 0.39,
  "high_5min": 268.50,
  "low_5min": 267.00,
  "range_5min": 1.50,
  "volume_5min": 12,

  "change_15min": 1.54,
  "change_15min_percent": 0.58,
  "high_15min": 268.85,
  "low_15min": 266.50,
  "range_15min": 2.35,
  "volume_15min": 35,

  "ma_5min": 267.51,
  "ma_15min": 267.25,
  "ma_30min": 268.10,
  "ma_60min": 268.50,

  "volatility": 0.0123,
  "volatility_annualized": 0.1953,
  "momentum": 0.0089,
  "price_acceleration": 0.0012,

  "trading_signal": "HOLD",
  "signal_reason": "Stable price action within normal parameters",

  "ttl": 1730923179
}
```

## Query Patterns

### 1. Get Latest Analytics for a Symbol

```bash
aws dynamodb query \
  --table-name stock-analytics \
  --key-condition-expression "symbol = :s" \
  --expression-attribute-values '{":s":{"S":"AAPL"}}' \
  --scan-index-forward false \
  --limit 10
```

### 2. Get Analytics for a Specific Date (using GSI)

```bash
aws dynamodb query \
  --table-name stock-analytics \
  --index-name DateIndex \
  --key-condition-expression "symbol = :s AND #d = :date" \
  --expression-attribute-names '{"#d":"date"}' \
  --expression-attribute-values '{":s":{"S":"AAPL"},":date":{"S":"2025-11-03"}}'
```

### 3. Get Analytics with Specific Fields Only

```bash
aws dynamodb query \
  --table-name stock-analytics \
  --key-condition-expression "symbol = :s" \
  --expression-attribute-values '{":s":{"S":"AAPL"}}' \
  --projection-expression "symbol,timestamp,current_price,trading_signal,momentum,volatility" \
  --limit 10
```

## Inspecting Data

Use the provided script to view detailed analytics:

```bash
# View latest record for AAPL
./scripts/inspect_analytics.sh AAPL 1

# View latest 5 records for GOOGL
./scripts/inspect_analytics.sh GOOGL 5
```

## Data Verification

To verify all fields are being written:

1. **Check CloudWatch Logs** (after deployment):
   ```bash
   ./scripts/monitor_logs.sh processor
   ```

   Look for log entries like:
   ```
   Wrote 62 fields to DynamoDB for AAPL at 2025-11-03T17:19:39.193597
   Batch write completed: 10 records written, 0 failed, avg 61 fields per record
   ```

2. **Query DynamoDB**:
   ```bash
   ./scripts/query_analytics.sh AAPL 1
   ```

3. **Inspect Detailed Record**:
   ```bash
   ./scripts/inspect_analytics.sh AAPL 1
   ```

## Storage Considerations

### Item Size
- **Average item size**: ~2-3 KB per record
- **Maximum item size**: 400 KB (DynamoDB limit)
- Current schema is well within limits

### Cost Estimation
With 8 symbols updating every 5 seconds during market hours (~6.5 hours):
- **Records per day**: ~37,440
- **Storage (7 days)**: ~262,080 records
- **Storage size**: ~524-786 MB
- **Estimated cost**: $5-15/month (on-demand billing)

### Optimization
- TTL automatically removes old data
- On-demand billing scales with usage
- GSI provides efficient date-based queries
- Batch writes optimize throughput

## Field Customization

To add/modify fields:

1. **Update Analytics Calculator** (`src/analytics.py`):
   ```python
   def calculate_all_analytics(...):
       analytics.update({
           'my_custom_field': calculated_value
       })
   ```

2. **Fields are automatically written** - no DynamoDB schema changes needed

3. **Deploy the update**:
   ```bash
   ./scripts/deploy.sh
   ```

## Summary

✅ **All calculated analytics are automatically stored in DynamoDB**
✅ **40-66 fields per record** including all metrics, indicators, and signals
✅ **Comprehensive logging** shows field counts and what's written
✅ **Easy inspection** with provided scripts
✅ **Flexible schema** - add fields without table changes
✅ **Cost optimized** with TTL and on-demand billing
