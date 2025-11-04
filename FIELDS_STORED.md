# What Fields Are Stored in DynamoDB?

## Quick Answer

**YES! ALL calculated analytics are automatically written to DynamoDB.**

Every stock record contains **40-66 fields** including:
- ✅ All raw market data
- ✅ Intraday metrics
- ✅ Gap analysis
- ✅ Time window analytics (for 1, 5, 15, 30, 60, 120 minutes)
- ✅ Moving averages (5, 15, 30, 60 minutes)
- ✅ **Momentum**
- ✅ **Volatility** (regular and annualized)
- ✅ **Price acceleration**
- ✅ Trading signals with reasons

## How It Works

The code automatically stores everything:

```python
# 1. analytics.py calculates ALL metrics
analytics = {
    'symbol': symbol,
    'current_price': current_price,
    # ... raw data
    # ... intraday metrics
    # ... time window analytics
    # ... moving averages
    'momentum': momentum,              # ✅ STORED
    'volatility': volatility,          # ✅ STORED
    'price_acceleration': acceleration, # ✅ STORED
    'trading_signal': signal,          # ✅ STORED
    # ... everything
}

# 2. lambda_function.py adds to batch
analytics_batch.append(analytics)

# 3. dynamodb_writer.py writes ENTIRE dictionary
dynamodb_writer.batch_write_analytics(analytics_batch)
```

Nothing is filtered out - **every field gets written**.

## Verify What's Being Written

### 1. Check CloudWatch Logs

After deployment, logs will show:
```
Wrote 62 fields to DynamoDB for AAPL at 2025-11-03T17:19:39
Batch write completed: 10 records written, 0 failed, avg 61 fields per record
```

### 2. Inspect DynamoDB Data

```bash
# View detailed analytics with ALL fields
./scripts/inspect_analytics.sh AAPL 1
```

This will show:
```
📊 Basic Information
  Symbol:           AAPL
  Timestamp:        2025-11-03T17:19:39.193597
  Current Price:    $268.04

📈 Raw Market Data
  Change:           -2.33
  Change %:         -0.86%
  High:             $270.85
  Low:              $266.25

🕐 Intraday Metrics
  Change from Open:        -1.66
  Change from Open %:      -0.62%
  Gap:                     -0.67
  Gap %:                   -0.25%

⏱️  Time Window Analytics
  1min: change=0.15, change%=0.06, high=268.10, low=267.95, vol=3
  5min: change=1.04, change%=0.39, high=268.50, low=267.00, vol=12
  15min: change=1.54, change%=0.58, high=268.85, low=266.50, vol=35
  ...

📉 Moving Averages
  MA-5min:         $267.51
  MA-15min:        $267.25
  MA-30min:        $268.10
  MA-60min:        $268.50

🎯 Volatility & Momentum
  Volatility:              0.0123    ✅ STORED
  Volatility (Annualized): 0.1953    ✅ STORED
  Momentum:                0.0089    ✅ STORED
  Price Acceleration:      0.0012    ✅ STORED

🚦 Trading Signal
  Signal:    HOLD
  Reason:    Stable price action within normal parameters

Total Fields Stored: 62
```

### 3. Query DynamoDB Directly

```bash
aws dynamodb get-item \
  --table-name stock-analytics \
  --key '{"symbol":{"S":"AAPL"},"timestamp":{"S":"2025-11-03T17:19:39.193597"}}' \
  --return-consumed-capacity TOTAL
```

## Complete Field List

See **[docs/DYNAMODB_SCHEMA.md](docs/DYNAMODB_SCHEMA.md)** for the complete schema with:
- All 40-66 fields documented
- Data types
- Example values
- Query patterns
- Storage considerations

## Field Categories

| Category | Fields | Examples |
|----------|--------|----------|
| **Primary Keys** | 2 | `symbol`, `timestamp` |
| **Basic Info** | 2 | `date`, `current_price` |
| **Raw Market Data** | 6 | `change`, `high`, `low`, `open` |
| **Intraday Metrics** | 2+ | `intraday_change_from_open`, `gap` |
| **Time Window Analytics** | 36 | `change_5min`, `high_15min`, `volume_30min` |
| **Moving Averages** | 4 | `ma_5min`, `ma_15min`, `ma_30min`, `ma_60min` |
| **Volatility & Momentum** | 4 | `momentum`, `volatility`, `price_acceleration` |
| **Trading Signals** | 2 | `trading_signal`, `signal_reason` |
| **Metadata** | 1 | `ttl` |

## Enhanced Logging

The code now logs exactly what's being written:

```python
# In dynamodb_writer.py
logger.info(
    f"Wrote {field_count} fields to DynamoDB for {symbol} - "
    f"Signal: {trading_signal}, "
    f"Momentum: {momentum:.4f}, "
    f"Volatility: {volatility:.4f}"
)

logger.debug(f"Fields written: {', '.join(sorted(item.keys()))}")
```

## Scripts Available

| Script | Purpose |
|--------|---------|
| `./scripts/query_analytics.sh AAPL 10` | Summary view of latest records |
| `./scripts/inspect_analytics.sh AAPL 1` | **Detailed view with ALL fields** |
| `./scripts/monitor_logs.sh processor` | Watch real-time processing logs |

## Adding More Fields

Want to add custom fields? Easy!

1. **Add to analytics.py:**
   ```python
   def calculate_all_analytics(...):
       analytics.update({
           'my_custom_metric': calculate_my_metric(...)
       })
   ```

2. **Deploy:**
   ```bash
   ./scripts/deploy.sh
   ```

3. **It's automatically stored** - no schema changes needed!

## Summary

✅ **All metrics ARE being written** - nothing is filtered
✅ **Enhanced logging** shows field counts and what's written
✅ **Inspection script** shows all fields in human-readable format
✅ **Complete documentation** in [docs/DYNAMODB_SCHEMA.md](docs/DYNAMODB_SCHEMA.md)
✅ **Easy to verify** - just deploy and check logs/DynamoDB

**Your momentum, volatility, and all other analytics are being stored!** 🎉
