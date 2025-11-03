# Quick Start Guide - Stock Lambda Consumer

This guide will get you up and running in 5 minutes.

## Prerequisites

You must have already deployed the Stock Lambda Producer. If not:

```bash
cd ../StockLambdaProducer
export FINNHUB_API_KEY="your-api-key"
./scripts/deploy.sh
```

## 1. Deploy the Consumer

The deployment script automatically fetches the Kinesis stream information from your producer stack:

```bash
# Deploy with defaults
./scripts/deploy.sh

# Or with custom settings
export TEST_MODE=true                    # Optional: bypass market hours
export DATA_RETENTION_DAYS=14            # Optional: retain data longer
export NO_DATA_TIMEOUT_MINUTES=15        # Optional: longer timeout
export BATCH_WRITE_INTERVAL_MINUTES=10   # Optional: flush batch every 10 min
export BATCH_MAX_SIZE=300                # Optional: smaller batch size
./scripts/deploy.sh
```

## 2. Verify Deployment

Check that everything is running:

```bash
# Check stack status
aws cloudformation describe-stacks --stack-name stock-lambda-consumer

# Check Kinesis event source mapping
aws lambda list-event-source-mappings --function-name stock-lambda-consumer-StockAnalyticsProcessor
```

## 3. Monitor Real-Time Processing

```bash
# Watch processor logs (real-time analytics)
./scripts/monitor_logs.sh processor

# Watch monitor logs (auto-shutdown mechanism)
./scripts/monitor_logs.sh monitor
```

## 4. Query Analytics

```bash
# Get latest 10 analytics records for AAPL
./scripts/query_analytics.sh AAPL 10

# Get latest 20 analytics records for GOOGL
./scripts/query_analytics.sh GOOGL 20
```

## 5. Understanding the Output

When you query analytics, you'll see:

- **trading_signal**: BUY, HOLD, or SELL
- **signal_reason**: Why that signal was generated
- **momentum**: Rate of price change
- **volatility**: Price volatility measure
- **ma_5min, ma_15min, etc.**: Moving averages
- **gap**: Gap from previous day's close
- **change_5min_percent**: % change over 5 minutes
- And much more!

## Example Analytics Record

```json
{
  "symbol": "AAPL",
  "current_price": 268.04,
  "trading_signal": "BUY",
  "signal_reason": "Positive momentum (0.0089); Low volatility (0.0123); Price below 15min MA",
  "momentum": 0.0089,
  "volatility": 0.0123,
  "ma_5min": 267.51,
  "ma_15min": 268.50,
  "gap": -0.67,
  "gap_type": "gap_down",
  "intraday_change_from_open_percent": -0.62
}
```

## Trading Signal Interpretation

- **BUY**: Price has positive momentum, low volatility, and is below moving average (potential bounce opportunity)
- **SELL**: Price has negative momentum, high volatility, and is above moving average (potential reversal)
- **HOLD**: Normal price action, no strong signals

## Common Tasks

### Enable Test Mode (24/7 Operation)

```bash
export TEST_MODE=true
./scripts/deploy.sh
```

### Check Why Consumer is Disabled

```bash
./scripts/monitor_logs.sh monitor
# Look for lines like "Disabling consumer: Market closed: Weekend"
```

### Clean Up Everything

```bash
./scripts/teardown.sh
```

## Troubleshooting

### No analytics data appearing?

1. Check producer is running:
   ```bash
   cd ../StockLambdaProducer
   ./scripts/monitor_logs.sh
   ```

2. Check event source mapping is enabled:
   ```bash
   aws lambda list-event-source-mappings --function-name stock-lambda-consumer-StockAnalyticsProcessor
   ```

3. Check processor logs for errors:
   ```bash
   ./scripts/monitor_logs.sh processor
   ```

### Consumer keeps disabling itself?

This is normal! The monitor automatically disables the consumer:
- Outside market hours (9:30 AM - 4:00 PM ET, Mon-Fri)
- When no data received for 10+ minutes
- On market holidays

To keep it running 24/7 for testing:
```bash
export TEST_MODE=true
./scripts/deploy.sh
```

## Next Steps

1. **Customize Analytics**: Edit `configs/config.example.json` to adjust thresholds
2. **Add More Symbols**: Add them in the producer configuration
3. **Build Dashboards**: Use the DynamoDB data to create visualizations
4. **Set Up Alerts**: Create CloudWatch alarms for specific trading signals
5. **Export Data**: Query DynamoDB and export to CSV for analysis

## Cost Estimate

With 8 symbols, 5-second polling during market hours (~6.5 hours/day):
- **Lambda**: $5-10/month
- **DynamoDB**: $5-15/month
- **Total**: ~$10-25/month

The auto-shutdown feature significantly reduces costs by only running during market hours.

## Resources

- Full documentation: [README.md](README.md)
- Producer app: [../StockLambdaProducer](../StockLambdaProducer)
- AWS SAM docs: https://docs.aws.amazon.com/serverless-application-model/

## Need Help?

1. Check logs: `./scripts/monitor_logs.sh processor`
2. Review README.md troubleshooting section
3. Check AWS CloudWatch console for detailed metrics
