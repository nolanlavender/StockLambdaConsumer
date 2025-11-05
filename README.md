# Stock ECS Consumer

A **stateful, real-time stock analytics processor** that runs on **ECS/Fargate** with in-memory rolling windows for sub-second latency analytics.

## Overview

This consumer processes stock price data from Kinesis Data Streams and generates comprehensive trading analytics using **in-memory rolling time windows**. Unlike serverless Lambda functions, this runs as a continuously-running container that maintains state across records, eliminating the need for DynamoDB queries on every record.

## Key Features

- **Stateful In-Memory Processing**: Maintains rolling windows in memory (no DB queries per record)
- **Sub-Second Latency**: ~10ms per record vs ~1 second with Lambda
- **State Persistence**: Saves/restores rolling windows to S3
- **Market Hours Scheduling**: Automatically starts at 9:15 AM ET, stops at 4:15 PM ET
- **Graceful Shutdown**: Saves state before container termination
- **Comprehensive Analytics**: 40-66 fields per stock including momentum, volatility, MAs, and trading signals

## Architecture

```
┌──────────────┐
│   Kinesis    │
│    Stream    │
└──────┬───────┘
       │ Continuous polling
       ▼
┌────────────────────────────────────┐
│    ECS/Fargate Container           │
│  ┌──────────────────────────────┐  │
│  │   In-Memory Rolling Windows  │  │
│  │  • 1min:  deque(~60 points)  │  │
│  │  • 5min:  deque(~300 points) │  │
│  │  • 15min: deque(~900 points) │  │
│  │  • 30min: deque(~1800 points)│  │
│  │  • 60min: deque(~3600 points)│  │
│  │  • 120min:deque(~7200 points)│  │
│  └──────────────────────────────┘  │
│                                    │
│  Per Record (~10ms):               │
│   1. Add to deques                 │
│   2. Evict old data                │
│   3. Calculate analytics           │
│   4. Batch write to DynamoDB       │
└────────────┬───────────────────────┘
             │
             ├──────────► DynamoDB (Analytics Results)
             │
             └──────────► S3 (State Persistence)

┌────────────────────────────────────┐
│     EventBridge Scheduler          │
│  • 9:15 AM ET: Set desired count=1│
│  • 4:15 PM ET: Set desired count=0│
│  (Monday-Friday only)              │
└────────────────────────────────────┘
```

## Why ECS over Lambda?

| Aspect | Lambda (Old) | ECS/Fargate (New) |
|--------|-------------|-------------------|
| **State** | Stateless | Stateful (in-memory rolling windows) |
| **DB Queries** | 6 queries per record | 0 queries per record |
| **Latency** | ~1 second per record | ~10ms per record |
| **Processing Model** | Event-driven batches | Continuous polling |
| **Cost** | ~$10/month | ~$30/month |
| **Startup** | Every 5 seconds | Once per day |
| **Memory** | Lost between invocations | Persisted across records |

## Directory Structure

```
StockLambdaConsumer/
├── src/                           # Source code
│   ├── consumer_main.py           # Main ECS consumer (continuous polling)
│   ├── rolling_windows.py         # In-memory rolling window data structures
│   ├── state_persistence.py      # S3 state save/restore
│   ├── analytics.py               # Analytics calculator
│   ├── historical_data.py         # DynamoDB historical data loader
│   ├── dynamodb_writer.py         # DynamoDB writer
│   ├── config.py                  # Configuration management
│   ├── market_hours.py            # Market hours checker
│   └── requirements.txt           # Python dependencies
├── scripts/                       # Deployment & monitoring scripts
│   ├── deploy_ecs.sh              # Deploy ECS stack
│   ├── build_and_push.sh          # Build & push Docker image
│   ├── update_ecs_service.sh      # Update running service
│   ├── view_ecs_logs.sh           # View CloudWatch logs
│   ├── ecs_status.sh              # Check service status
│   ├── query_analytics.sh         # Query DynamoDB results
│   └── inspect_analytics.sh       # Detailed analytics inspection
├── docs/                          # Documentation
│   ├── ECS_MIGRATION_GUIDE.md     # Complete migration guide
│   ├── DYNAMODB_SCHEMA.md         # DynamoDB schema documentation
│   └── UPDATE_GUIDE.md            # Update procedures
├── Dockerfile                     # Container definition
├── template-ecs.yaml              # CloudFormation template (ECS/Fargate)
└── README.md                      # This file
```

## Prerequisites

1. **Docker** - For building container images
2. **AWS CLI** - Configured with appropriate permissions
3. **Stock Lambda Producer** - Must be deployed first to create Kinesis stream

## Quick Start

### 1. Deploy Infrastructure

```bash
cd /Users/nlavender/Documents/StockLambdaConsumer

# Deploy ECS cluster, service, ECR repo, S3 bucket, etc.
./scripts/deploy_ecs.sh
```

This creates:
- ECS Cluster & Service
- ECR Repository
- S3 Bucket (state persistence)
- VPC, Subnets, Security Groups
- IAM Roles
- EventBridge Schedulers (market hours)

**Duration**: ~5 minutes

### 2. Build and Push Docker Image

```bash
# Build image and push to ECR
./scripts/build_and_push.sh
```

**Duration**: ~3 minutes

### 3. Update ECS Service

```bash
# Force service to use new image
./scripts/update_ecs_service.sh
```

**Duration**: ~2 minutes

### 4. Monitor

```bash
# View real-time logs
./scripts/view_ecs_logs.sh

# Check service status
./scripts/ecs_status.sh

# Query analytics
./scripts/query_analytics.sh AAPL 10
```

## Configuration

### Environment Variables (in template-ecs.yaml)

| Variable | Description | Default |
|----------|-------------|---------|
| `KINESIS_STREAM_NAME` | Kinesis stream name | `stock-prices-stream` |
| `DYNAMODB_TABLE_NAME` | DynamoDB table name | `stock-analytics` |
| `DATA_RETENTION_DAYS` | TTL for DynamoDB records | `7` |
| `ENFORCE_MARKET_HOURS` | Check market hours before processing | `true` |
| `TEST_MODE` | Bypass market hours check | `false` |
| `STATE_BUCKET` | S3 bucket for state persistence | Auto-created |

### Container Resources

- **CPU**: 0.5 vCPU (configurable in template)
- **Memory**: 1 GB (configurable in template)
- **Network**: Fargate with public IP

## Market Hours Scheduling

The service automatically:
- **Starts at 9:15 AM ET** (15 min before market open)
- **Stops at 4:15 PM ET** (15 min after market close)
- **Skips weekends automatically**

Implemented via EventBridge Scheduler that sets ECS service desired count to 1 or 0.

## State Persistence

### On Startup
1. Container starts
2. Loads rolling window state from S3 (if exists)
3. Begins processing from Kinesis

### During Runtime
- Saves state to S3 every 5 minutes
- State includes all rolling windows for all symbols

### On Shutdown
- Receives SIGTERM signal
- Saves current state to S3 (compressed)
- Flushes analytics batch to DynamoDB
- Container exits gracefully

## Analytics Generated

Each stock record is enriched with **40-66 fields**:

### Price Metrics
- Intraday changes from open
- Gap analysis vs previous day's close
- High/Low tracking per time window
- Breakout/breakdown detection

### Technical Indicators
- Moving averages (5min, 15min, 30min, 1hr)
- Volatility (standard deviation of returns, annualized)
- Momentum (rate of change)
- Price acceleration (momentum velocity)

### Trading Signals
- **BUY**: Strong upward momentum + low volatility
- **SELL**: Downward momentum + high volatility
- **HOLD**: Stable price action within normal parameters

**See [DynamoDB Schema Documentation](docs/DYNAMODB_SCHEMA.md) for complete field list.**

## Monitoring

### View Logs

```bash
# Tail logs (follow mode)
./scripts/view_ecs_logs.sh

# View last 30 minutes
./scripts/view_ecs_logs.sh 30m

# View last 1 hour
./scripts/view_ecs_logs.sh 1h
```

### Check Service Status

```bash
./scripts/ecs_status.sh
```

Shows:
- Service status (ACTIVE, DRAINING, INACTIVE)
- Desired vs Running task count
- Recent service events
- Task details (CPU, memory, status)

### Query Analytics

```bash
# Query latest analytics for AAPL
./scripts/query_analytics.sh AAPL 20

# Detailed inspection
./scripts/inspect_analytics.sh AAPL
```

## Updating Code

After making code changes:

```bash
# 1. Build and push new image
./scripts/build_and_push.sh

# 2. Force ECS to deploy new image
./scripts/update_ecs_service.sh

# 3. Monitor deployment
./scripts/ecs_status.sh
```

## Troubleshooting

### Container Won't Start

1. Check task logs: `./scripts/view_ecs_logs.sh`
2. Verify ECR image exists
3. Check IAM permissions on task role
4. Verify environment variables in task definition

### No Data Processing

1. Check Kinesis stream has data
2. Verify container is running: `./scripts/ecs_status.sh`
3. Check market hours (or set TEST_MODE=true)
4. View logs for errors: `./scripts/view_ecs_logs.sh`

### High Memory Usage

1. Check rolling window sizes in logs (look for "Stats:" lines)
2. Reduce time window sizes in config
3. Increase container memory in template-ecs.yaml

### State Not Persisting

1. Check S3 bucket exists and has files
2. Verify task role has S3 permissions
3. Check logs for save/load errors

## Cost Estimate

**Monthly costs** (7 hours/day, 5 days/week):

- **Fargate**: ~$25-30 (0.5 vCPU, 1GB memory)
- **DynamoDB**: ~$5-10 (on-demand)
- **S3**: <$1 (state files, compressed)
- **CloudWatch Logs**: ~$2-5
- **Total**: ~$30-45/month

Compare to Lambda: ~$10/month (but with 100x slower processing)

## Security

- Least-privilege IAM roles
- DynamoDB encryption at rest
- Point-in-time recovery enabled
- S3 bucket encryption
- Private container (no public access)
- Security group limits egress

## Complete Documentation

- **[ECS Migration Guide](docs/ECS_MIGRATION_GUIDE.md)** - Complete migration documentation
- **[DynamoDB Schema](docs/DYNAMODB_SCHEMA.md)** - All 66 analytics fields
- **[Update Guide](docs/UPDATE_GUIDE.md)** - How to update without downtime

## Related Projects

- [Stock Lambda Producer](../StockLambdaProducer) - Fetches and streams stock data to Kinesis

## Support

For issues:
1. Check CloudWatch logs: `./scripts/view_ecs_logs.sh`
2. Check service status: `./scripts/ecs_status.sh`
3. Review [ECS_MIGRATION_GUIDE.md](docs/ECS_MIGRATION_GUIDE.md)
4. Check CloudFormation events in AWS Console

## License

MIT License - see LICENSE file for details.
