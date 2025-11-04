# ECS/Fargate Migration Guide

## Overview

This guide covers the migration from **Lambda (stateless, event-driven)** to **ECS/Fargate (stateful, continuously-running)** for the Stock Analytics Consumer.

## Why Migrate?

### Lambda Limitations (Previous Architecture)
- **No state persistence** between invocations
- **350+ DynamoDB queries** per batch (6 time windows × 50-100 records)
- **Slow processing**: 47-60 seconds per batch
- **Timeout issues**: ~33% of invocations timing out
- **High latency**: ~20 minutes from data timestamp to analytics complete

### ECS Benefits (New Architecture)
- **In-memory rolling windows**: No DynamoDB queries for time window data
- **Stateful processing**: Maintains data across records
- **Faster analytics**: ~10ms per record (vs ~1 second with queries)
- **Low latency**: Sub-second from record arrival to analytics complete
- **Market hours scheduling**: Only runs when market is open

## Architecture Comparison

### Old: Lambda (Stateless)
```
┌─────────────┐
│   Kinesis   │
└──────┬──────┘
       │ Triggers every 5 seconds
       ▼
┌─────────────────────────────────────┐
│         Lambda Function             │
│  ┌───────────────────────────────┐  │
│  │ Process 50-100 records:       │  │
│  │  For each record:             │  │
│  │   ├─ Query DynamoDB (1min)    │  │
│  │   ├─ Query DynamoDB (5min)    │  │
│  │   ├─ Query DynamoDB (15min)   │  │
│  │   ├─ Query DynamoDB (30min)   │  │
│  │   ├─ Query DynamoDB (60min)   │  │
│  │   ├─ Query DynamoDB (120min)  │  │
│  │   └─ Calculate analytics      │  │
│  └───────────────────────────────┘  │
│  Duration: 47-60 seconds            │
└─────────────┬───────────────────────┘
              │
              ▼
       ┌─────────────┐
       │  DynamoDB   │
       │  (Results)  │
       └─────────────┘
```

### New: ECS/Fargate (Stateful)
```
┌─────────────┐
│   Kinesis   │
└──────┬──────┘
       │ Continuous polling
       ▼
┌──────────────────────────────────────────┐
│       ECS Container (Always Running)     │
│  ┌────────────────────────────────────┐  │
│  │  In-Memory Rolling Windows:        │  │
│  │   ├─ 1min:  deque(maxlen=~60)     │  │
│  │   ├─ 5min:  deque(maxlen=~300)    │  │
│  │   ├─ 15min: deque(maxlen=~900)    │  │
│  │   ├─ 30min: deque(maxlen=~1800)   │  │
│  │   ├─ 60min: deque(maxlen=~3600)   │  │
│  │   └─ 120min:deque(maxlen=~7200)   │  │
│  └────────────────────────────────────┘  │
│  For each record:                        │
│   1. Add to all deques (~1ms)            │
│   2. Evict old data (~1ms)               │
│   3. Calculate analytics (~8ms)          │
│  Duration per record: ~10ms              │
└─────────────┬────────────────────────────┘
              │
              ▼
       ┌─────────────┐
       │  DynamoDB   │
       │  (Results)  │
       └─────────────┘
              ▲
              │
       ┌──────┴──────┐
       │     S3      │
       │ (State Save)│
       └─────────────┘
```

## Key Features

### 1. In-Memory Rolling Windows
- **Data Structure**: Deques (double-ended queues) for O(1) append/pop
- **Automatic Eviction**: Old data removed based on timestamp
- **Per-Symbol Tracking**: Separate windows for each stock symbol
- **Serializable**: Can save/restore state to S3

### 2. State Persistence
- **Startup**: Load previous day's rolling windows from S3 (if available)
- **Periodic Save**: Every 5 minutes, save state to S3
- **Graceful Shutdown**: Save state on SIGTERM before container stops
- **Compressed**: gzip compression reduces S3 storage costs

### 3. Market Hours Scheduling
- **Start Time**: 9:15 AM ET (15 min before market open)
- **Stop Time**: 4:15 PM ET (15 min after market close)
- **Weekends**: Automatically skipped
- **Mechanism**: EventBridge Scheduler sets ECS service desired count

### 4. Continuous Processing
- **Polling**: Continuously polls Kinesis for new records
- **Batch Processing**: Processes up to 100 records per get-records call
- **Low Latency**: Sub-second from Kinesis → Analytics complete
- **Graceful Shutdown**: Handles SIGTERM, saves state, flushes batch

## Deployment Guide

### Prerequisites
1. **Docker** installed locally
2. **AWS CLI** configured with appropriate permissions
3. **StockLambdaProducer** stack deployed (for Kinesis stream)

### Step 1: Deploy Infrastructure

```bash
cd /Users/nlavender/Documents/StockLambdaConsumer

# Deploy the ECS CloudFormation stack
./scripts/deploy_ecs.sh
```

This creates:
- ECS Cluster
- ECS Service (initially with 0 tasks)
- ECR Repository
- S3 Bucket for state persistence
- VPC, Subnets, Security Groups
- IAM Roles
- EventBridge Schedulers

**Expected Duration**: ~5 minutes

### Step 2: Build and Push Docker Image

```bash
# Build Docker image and push to ECR
./scripts/build_and_push.sh
```

This:
- Builds the Docker image from `Dockerfile`
- Logs in to ECR
- Tags image with `:latest` and `:YYYYMMDD-HHMMSS`
- Pushes both tags to ECR

**Expected Duration**: ~3 minutes

### Step 3: Update ECS Service

```bash
# Force ECS service to pull new image
./scripts/update_ecs_service.sh
```

This forces a new deployment with the latest image.

**Expected Duration**: ~2 minutes

### Step 4: Manually Start for Testing (Optional)

The service starts automatically at 9:15 AM ET. To start manually for testing:

```bash
# Get cluster and service names
STACK_NAME=stock-ecs-consumer
CLUSTER=$(aws cloudformation describe-stacks --stack-name $STACK_NAME \
    --query "Stacks[0].Outputs[?OutputKey=='ECSClusterName'].OutputValue" --output text)
SERVICE=$(aws cloudformation describe-stacks --stack-name $STACK_NAME \
    --query "Stacks[0].Outputs[?OutputKey=='ECSServiceName'].OutputValue" --output text)

# Start service
aws ecs update-service \
    --cluster $CLUSTER \
    --service $SERVICE \
    --desired-count 1
```

### Step 5: Monitor

```bash
# View real-time logs
./scripts/view_ecs_logs.sh

# Check service status
./scripts/ecs_status.sh

# Query analytics from DynamoDB
./scripts/query_analytics.sh AAPL 10
```

## Monitoring and Operations

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

### Update Code

After making code changes:

```bash
# 1. Build and push new image
./scripts/build_and_push.sh

# 2. Force ECS to deploy new image
./scripts/update_ecs_service.sh

# 3. Monitor deployment
./scripts/ecs_status.sh
```

### Manually Start/Stop

```bash
# Start (set desired count to 1)
aws ecs update-service \
    --cluster stock-ecs-consumer-cluster \
    --service stock-ecs-consumer-consumer-service \
    --desired-count 1

# Stop (set desired count to 0)
aws ecs update-service \
    --cluster stock-ecs-consumer-cluster \
    --service stock-ecs-consumer-consumer-service \
    --desired-count 0
```

## Cost Comparison

### Lambda (Old)
- **Invocations**: ~100-200/day (during market hours)
- **Duration**: 50 seconds per invocation
- **Memory**: 512 MB
- **Estimated Cost**: ~$5-10/month

### ECS/Fargate (New)
- **Running Time**: ~7 hours/day (9:15 AM - 4:15 PM ET)
- **CPU**: 0.5 vCPU
- **Memory**: 1 GB
- **Estimated Cost**: ~$25-35/month

**Benefit**: 100x faster processing, sub-second latency, stateful windows

## Troubleshooting

### Container Won't Start

**Check task logs**:
```bash
./scripts/view_ecs_logs.sh
```

**Common issues**:
- Missing ECR image: Run `./scripts/build_and_push.sh`
- IAM permissions: Check task role has Kinesis/DynamoDB/S3 access
- Invalid environment variables: Check task definition

### No Data Processing

**Check**:
1. Kinesis stream has data: `aws kinesis describe-stream --stream-name stock-prices-stream`
2. Container is running: `./scripts/ecs_status.sh`
3. Market hours: Service only processes during market hours unless `TEST_MODE=true`
4. Logs for errors: `./scripts/view_ecs_logs.sh`

### High Memory Usage

**Check rolling window sizes**:
```bash
# Look for "Stats:" log lines showing data points in memory
./scripts/view_ecs_logs.sh | grep "Stats:"
```

**If memory is high**:
- Reduce time window sizes in config
- Increase container memory in `template-ecs.yaml` (ContainerMemory parameter)

### State Not Persisting

**Check S3 bucket**:
```bash
aws s3 ls s3://stock-ecs-consumer-state-{ACCOUNT_ID}/state/rolling-windows/
```

**Common issues**:
- S3 permissions: Check task role has `s3:PutObject` permission
- Shutdown too fast: Container needs time to save state on SIGTERM

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

### Update Configuration

1. Edit `template-ecs.yaml` parameters
2. Redeploy stack: `./scripts/deploy_ecs.sh`
3. Update service: `./scripts/update_ecs_service.sh`

## Rollback to Lambda

If you need to rollback to the Lambda version:

```bash
# Stop ECS service
aws ecs update-service \
    --cluster stock-ecs-consumer-cluster \
    --service stock-ecs-consumer-consumer-service \
    --desired-count 0

# Re-deploy Lambda version
cd /Users/nlavender/Documents/StockLambdaConsumer
./scripts/deploy.sh  # Uses template.yaml (Lambda version)
```

## Next Steps

1. **Monitor latency**: Check CloudWatch logs for analytics latency metrics
2. **Optimize windows**: Adjust time window sizes based on memory usage
3. **Add metrics**: Consider adding CloudWatch custom metrics for rolling window sizes
4. **Multi-shard support**: Extend consumer_main.py to process multiple Kinesis shards concurrently

## Files Created

### Core Code
- `src/rolling_windows.py`: In-memory rolling window data structures
- `src/state_persistence.py`: S3 state save/restore logic
- `src/consumer_main.py`: Continuous Kinesis consumer (ECS entry point)

### Infrastructure
- `template-ecs.yaml`: CloudFormation template for ECS/Fargate
- `Dockerfile`: Container image definition

### Scripts
- `scripts/deploy_ecs.sh`: Deploy CloudFormation stack
- `scripts/build_and_push.sh`: Build and push Docker image to ECR
- `scripts/update_ecs_service.sh`: Force ECS service to deploy new image
- `scripts/view_ecs_logs.sh`: View CloudWatch logs
- `scripts/ecs_status.sh`: Check service and task status

## Support

For issues or questions, check:
1. CloudWatch Logs: `./scripts/view_ecs_logs.sh`
2. ECS Service Events: `./scripts/ecs_status.sh`
3. CloudFormation Events: AWS Console → CloudFormation → stack-ecs-consumer
