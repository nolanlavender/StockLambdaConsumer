# Stock Lambda Consumer

A real-time stock analytics processor that consumes from Kinesis Data Streams and generates actionable trading signals using advanced analytics.

## Features

- Real-time stock price analytics from Kinesis streams
- Historical context loading (previous day's data for gap analysis)
- Time-window based analytics (1min, 5min, 15min, 30min, 1hr, 2hr)
- Moving averages and volatility calculations
- Automated trading signals (BUY/HOLD/SELL)
- Auto-shutdown when no data received or outside market hours
- DynamoDB storage with 7-day TTL
- Comprehensive logging and testing
- Infrastructure as Code with AWS SAM

## Architecture

```
Kinesis Stream → Lambda Consumer → Analytics Engine
                      ↓                    ↓
                 DynamoDB ← Historical Data Loader
                      ↓
                 Trading Signals

EventBridge (5min) → Monitor Lambda
                      ↓
                 Auto-enable/disable Consumer
```

## Analytics Generated

### Price Metrics
- Intraday change from open (%, absolute)
- Gap analysis (vs previous day's close)
- Price changes over multiple time windows
- High/Low tracking per time period
- Breakout/breakdown detection (vs previous day's levels)

### Technical Indicators
- Moving averages (5min, 15min, 30min, 1hr)
- Volatility (standard deviation of returns)
- Momentum (rate of change)
- Price acceleration (velocity of momentum)

### Trading Signals
- **BUY**: Strong upward momentum + low volatility + price below MA
- **SELL**: Downward momentum + high volatility + price above MA
- **HOLD**: Stable price action within normal parameters

## Directory Structure

```
StockLambdaConsumer/
├── src/                           # Source code
│   ├── lambda_function.py         # Main Kinesis consumer
│   ├── monitor.py                 # Auto-shutdown monitor
│   ├── analytics.py               # Analytics calculator
│   ├── historical_data.py         # Historical data loader
│   ├── dynamodb_writer.py         # DynamoDB writer
│   ├── config.py                  # Configuration management
│   └── market_hours.py            # Market hours checker
├── scripts/                       # Utility scripts
│   ├── deploy.sh                  # Deployment script
│   ├── run_tests.sh               # Test runner
│   ├── teardown.sh                # Cleanup script
│   ├── query_analytics.sh         # Query DynamoDB
│   └── monitor_logs.sh            # CloudWatch logs monitor
├── configs/                       # Configuration files
│   ├── config.example.json        # Example configuration
│   └── .env.example               # Environment variables example
├── tests/                         # Test suite
│   ├── test_*.py                  # Test files
│   └── test_config.json           # Test configuration
├── template.yaml                  # AWS SAM template
├── requirements.txt               # Python dependencies
├── test_requirements.txt          # Test dependencies
└── README.md                      # This file
```

## Prerequisites

1. **AWS CLI** - [Install Guide](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
2. **SAM CLI** - [Install Guide](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
3. **Python 3.11+**
4. **Stock Lambda Producer** - Must be deployed first to create Kinesis stream

## Quick Start

### 1. Deploy the Producer (if not already done)

```bash
cd ../StockLambdaProducer
./scripts/deploy.sh
```

### 2. Deploy the Consumer

```bash
cd StockLambdaConsumer

# The deploy script will automatically fetch Kinesis stream info from producer
./scripts/deploy.sh
```

### 3. Monitor the Application

```bash
# Monitor processor logs
./scripts/monitor_logs.sh processor

# Monitor auto-shutdown logs
./scripts/monitor_logs.sh monitor

# Query analytics for a symbol
./scripts/query_analytics.sh AAPL 20
```

## Configuration

### Environment Variables

Set these before deployment to customize behavior:

```bash
# Required (or auto-detected from producer stack)
export KINESIS_STREAM_NAME=stock-prices-stream
export KINESIS_STREAM_ARN=arn:aws:kinesis:...

# Optional
export STACK_NAME=stock-lambda-consumer
export AWS_REGION=us-east-1
export DYNAMODB_TABLE_NAME=stock-analytics
export DATA_RETENTION_DAYS=7
export ENFORCE_MARKET_HOURS=true
export TEST_MODE=false
export NO_DATA_TIMEOUT_MINUTES=10
export CHECK_INTERVAL_MINUTES=5

# Batch Write Configuration (prevents memory buildup)
export BATCH_WRITE_INTERVAL_MINUTES=15  # Flush to DynamoDB every 15 minutes
export BATCH_MAX_SIZE=500               # Force flush if batch reaches 500 items
```

### Analytics Configuration

Edit `configs/config.example.json`:

```json
{
  "analytics": {
    "time_windows_minutes": [1, 5, 15, 30, 60, 120],
    "moving_average_windows_minutes": [5, 15, 30, 60],
    "volatility_threshold": 0.02,
    "momentum_threshold": 0.015
  },
  "batch": {
    "write_interval_minutes": 15,
    "max_size": 500
  }
}
```

## Data Format

### Input (from Kinesis)

```json
{
  "symbol": "AAPL",
  "price": 268.04,
  "change": -2.33,
  "change_percent": "-0.86",
  "high": 270.85,
  "low": 266.25,
  "open": 269.7,
  "previous_close": 270.37,
  "timestamp": "2025-11-03T17:19:39.193597"
}
```

### Output (to DynamoDB)

```json
{
  "symbol": "AAPL",
  "timestamp": "2025-11-03T17:19:39.193597",
  "date": "2025-11-03",
  "current_price": 268.04,
  "intraday_change_from_open": -1.66,
  "intraday_change_from_open_percent": -0.62,
  "gap": -0.67,
  "gap_percent": -0.25,
  "gap_type": "gap_down",
  "change_5min": 1.04,
  "change_5min_percent": 0.39,
  "ma_5min": 267.51,
  "ma_15min": 267.25,
  "volatility": 0.0123,
  "momentum": 0.0089,
  "trading_signal": "HOLD",
  "signal_reason": "Stable price action within normal parameters",
  "ttl": 1730923179
}
```

## Batch Write Management

To prevent memory buildup during long-running Lambda executions, the consumer implements intelligent batch flushing:

### Automatic Flush Triggers

1. **Time-Based Flush** (default: every 15 minutes):
   - Periodically flushes analytics to DynamoDB
   - Prevents memory accumulation during extended processing
   - Configurable via `BATCH_WRITE_INTERVAL_MINUTES`

2. **Size-Based Flush** (default: 500 items):
   - Forces flush when batch reaches maximum size
   - Safety mechanism for high-volume scenarios
   - Configurable via `BATCH_MAX_SIZE`

3. **End-of-Execution Flush**:
   - Always flushes remaining items at end of Lambda invocation
   - Ensures no data loss

### Benefits

- **Memory Efficiency**: Prevents Lambda from running out of memory
- **Data Safety**: Ensures analytics are written regularly
- **Flexibility**: Configurable based on your data volume
- **Cost Optimization**: Batches writes for efficiency

### Configuration Example

```bash
# For high-volume streams, flush more frequently
export BATCH_WRITE_INTERVAL_MINUTES=5
export BATCH_MAX_SIZE=250

# For low-volume streams, batch more for efficiency
export BATCH_WRITE_INTERVAL_MINUTES=30
export BATCH_MAX_SIZE=1000
```

## Auto-Shutdown Mechanism

The monitor Lambda runs every 5 minutes and:

1. **Checks market hours** (if enforced):
   - Disables consumer outside market hours
   - Enables consumer during market hours

2. **Checks data flow**:
   - Disables consumer if no data received in 10+ minutes
   - Prevents unnecessary Lambda invocations and costs

3. **Respects test mode**:
   - In test mode, consumer stays enabled regardless of market hours

## Testing

### Run Full Test Suite

```bash
./scripts/run_tests.sh
```

### Run Specific Tests

```bash
# Unit tests only
pytest tests/ -m unit -v

# Integration tests
pytest tests/ -m integration -v

# Specific test file
pytest tests/test_analytics.py -v

# With coverage
pytest tests/ --cov=src --cov-report=html
```

## Monitoring

### CloudWatch Logs

```bash
# Processor logs
aws logs tail /aws/lambda/StockAnalyticsProcessor --follow

# Monitor logs
aws logs tail /aws/lambda/StockAnalyticsMonitor --follow
```

### CloudWatch Alarms

The stack creates alarms for:
- Processor errors (> 5 in 5 minutes)
- Processor throttles (> 10 in 5 minutes)

### DynamoDB Queries

```bash
# Query latest analytics for AAPL
aws dynamodb query \
    --table-name stock-analytics \
    --key-condition-expression "symbol = :s" \
    --expression-attribute-values '{":s":{"S":"AAPL"}}' \
    --scan-index-forward false \
    --limit 10

# Query by date (using GSI)
aws dynamodb query \
    --table-name stock-analytics \
    --index-name DateIndex \
    --key-condition-expression "symbol = :s AND #d = :date" \
    --expression-attribute-names '{"#d":"date"}' \
    --expression-attribute-values '{":s":{"S":"AAPL"},":date":{"S":"2025-11-03"}}'
```

## Historical Context Feature

The application loads previous day's data on startup to provide better analytics:

- **Gap Analysis**: Compares today's open vs yesterday's close
- **Breakout Detection**: Identifies when price breaks yesterday's high/low
- **Better Baselines**: More meaningful comparisons for trading signals

## Cost Optimization

- **Auto-shutdown**: Stops processing when no data or outside market hours
- **DynamoDB TTL**: Automatically deletes data after 7 days
- **Batch Processing**: Processes up to 100 Kinesis records at once
- **On-demand Billing**: DynamoDB scales automatically

Estimated monthly cost (for 8 symbols, 5-second intervals, market hours only):
- Lambda: ~$5-10
- DynamoDB: ~$5-15
- Kinesis: Covered by producer stack
- Total: ~$10-25/month

## Troubleshooting

### No Data in DynamoDB

1. Check Kinesis event source mapping status:
   ```bash
   aws lambda list-event-source-mappings \
       --function-name StockAnalyticsProcessor
   ```

2. Check processor logs:
   ```bash
   ./scripts/monitor_logs.sh processor
   ```

3. Verify producer is running:
   ```bash
   aws stepfunctions list-executions \
       --state-machine-arn <producer-state-machine-arn>
   ```

### Consumer Keeps Disabling

1. Check monitor logs:
   ```bash
   ./scripts/monitor_logs.sh monitor
   ```

2. Verify market hours or enable test mode:
   ```bash
   export TEST_MODE=true
   ./scripts/deploy.sh
   ```

### Lambda Errors

1. Check function logs for stack traces
2. Verify IAM permissions
3. Check DynamoDB table exists
4. Verify Kinesis stream ARN is correct

## Cleanup

To remove all resources:

```bash
./scripts/teardown.sh
```

This will delete:
- Lambda functions
- DynamoDB table and all data
- CloudWatch log groups
- IAM roles and policies
- Event source mappings

## Advanced Usage

### Custom Analytics Thresholds

Modify trading signal thresholds:

```python
# In src/analytics.py
analytics = StockAnalytics(
    volatility_threshold=0.03,  # Higher threshold = less sensitive
    momentum_threshold=0.02     # Higher threshold = stronger signals needed
)
```

### Extend Time Windows

Add custom time windows:

```bash
export TIME_WINDOWS_MINUTES=1,5,15,30,60,120,240
export MOVING_AVERAGE_WINDOWS_MINUTES=5,15,30,60,120
./scripts/deploy.sh
```

### Query Patterns

```bash
# Get all BUY signals for a symbol
aws dynamodb query \
    --table-name stock-analytics \
    --key-condition-expression "symbol = :s" \
    --filter-expression "trading_signal = :signal" \
    --expression-attribute-values '{":s":{"S":"AAPL"},":signal":{"S":"BUY"}}'
```

## Security

- All AWS resources use least-privilege IAM roles
- DynamoDB encryption at rest enabled by default
- Point-in-time recovery enabled for DynamoDB
- No sensitive data logged

## Contributing

1. Run tests before committing: `./scripts/run_tests.sh`
2. Follow existing code style
3. Add tests for new features
4. Update documentation

## License

MIT License - see LICENSE file for details.

## Related Projects

- [Stock Lambda Producer](../StockLambdaProducer) - Fetches and streams stock data to Kinesis

## Support

For issues or questions:
1. Check CloudWatch logs
2. Review troubleshooting section
3. Check AWS SAM documentation
4. Review code comments and docstrings
