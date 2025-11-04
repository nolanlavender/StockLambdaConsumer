# Deployment Guide - Stock Lambda Consumer

## Prerequisites

The consumer requires a Kinesis Data Stream to consume from. You have three options:

## Option 1: Deploy Producer First (Recommended)

If you haven't deployed the producer yet:

```bash
# 1. Deploy the producer
cd ../StockLambdaProducer
export FINNHUB_API_KEY=your-api-key-here
./scripts/deploy.sh

# 2. Deploy the consumer (will auto-detect Kinesis stream)
cd ../StockLambdaConsumer
./scripts/deploy.sh
```

The consumer script will automatically fetch the Kinesis stream ARN from the producer stack.

## Option 2: Use Existing Kinesis Stream

If you already have a Kinesis stream deployed:

```bash
# Get your stream ARN
aws kinesis describe-stream --stream-name stock-prices-stream

# Set environment variables
export KINESIS_STREAM_NAME=stock-prices-stream
export KINESIS_STREAM_ARN=arn:aws:kinesis:us-east-1:123456789012:stream/stock-prices-stream

# Deploy
./scripts/deploy.sh
```

## Option 3: Use Different Producer Stack Name

If your producer stack has a different name:

```bash
export PRODUCER_STACK_NAME=my-custom-producer-stack
./scripts/deploy.sh
```

## Getting Kinesis Stream Information

### From AWS Console
1. Go to Kinesis in AWS Console
2. Click on your stream
3. Copy the ARN from the stream details

### From AWS CLI
```bash
# List all streams
aws kinesis list-streams

# Get specific stream details
aws kinesis describe-stream --stream-name stock-prices-stream

# Get ARN from CloudFormation stack
aws cloudformation describe-stacks \
  --stack-name stock-lambda-producer \
  --query "Stacks[0].Outputs[?OutputKey=='KinesisStreamArn'].OutputValue" \
  --output text
```

## Common Deployment Errors

### Error: Producer stack not found

**Problem:**
```
Error: Producer stack 'stock-lambda-producer' not found
```

**Solution:**
Either deploy the producer first, or manually specify the Kinesis stream:
```bash
export KINESIS_STREAM_NAME=stock-prices-stream
export KINESIS_STREAM_ARN=arn:aws:kinesis:us-east-1:ACCOUNT_ID:stream/stock-prices-stream
./scripts/deploy.sh
```

### Error: Parameters must have values

**Problem:**
```
Parameters: [KinesisStreamArn] must have values
```

**Solution:**
The script couldn't find your Kinesis stream. Set it manually:
```bash
# Get your AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Set the Kinesis stream ARN
export KINESIS_STREAM_NAME=stock-prices-stream
export KINESIS_STREAM_ARN=arn:aws:kinesis:us-east-1:${ACCOUNT_ID}:stream/stock-prices-stream

# Deploy
./scripts/deploy.sh
```

### Error: Stack exists but has no KinesisStreamName output

**Problem:**
Producer stack exists but doesn't export the Kinesis stream information.

**Solution:**
1. Check what outputs the producer stack has:
   ```bash
   aws cloudformation describe-stacks \
     --stack-name stock-lambda-producer \
     --query "Stacks[0].Outputs"
   ```

2. Manually set the Kinesis stream information:
   ```bash
   export KINESIS_STREAM_NAME=stock-prices-stream
   export KINESIS_STREAM_ARN=arn:aws:kinesis:us-east-1:ACCOUNT_ID:stream/stock-prices-stream
   ./scripts/deploy.sh
   ```

## Full Deployment Example

Here's a complete example from scratch:

```bash
# 1. Clone or navigate to producer
cd StockLambdaProducer

# 2. Deploy producer
export FINNHUB_API_KEY=your-finnhub-api-key
export AWS_REGION=us-east-1
./scripts/deploy.sh

# Wait for deployment to complete...

# 3. Navigate to consumer
cd ../StockLambdaConsumer

# 4. Deploy consumer (will auto-detect Kinesis from producer)
./scripts/deploy.sh

# 5. Verify deployment
aws cloudformation describe-stacks \
  --stack-name stock-lambda-consumer \
  --query "Stacks[0].StackStatus"

# 6. Check event source mapping
aws lambda list-event-source-mappings \
  --function-name stock-lambda-consumer-StockAnalyticsProcessor

# 7. Monitor logs
./scripts/monitor_logs.sh processor
```

## Custom Configuration

Deploy with custom settings:

```bash
# Custom settings
export STACK_NAME=my-stock-consumer
export AWS_REGION=us-west-2
export DYNAMODB_TABLE_NAME=my-stock-analytics
export DATA_RETENTION_DAYS=14
export TEST_MODE=true
export BATCH_WRITE_INTERVAL_MINUTES=10
export BATCH_MAX_SIZE=300

# Set Kinesis stream (if not auto-detected)
export KINESIS_STREAM_NAME=stock-prices-stream
export KINESIS_STREAM_ARN=arn:aws:kinesis:us-west-2:ACCOUNT_ID:stream/stock-prices-stream

# Deploy
./scripts/deploy.sh
```

## Verification Steps

After deployment, verify everything is working:

```bash
# 1. Check stack status
aws cloudformation describe-stacks \
  --stack-name stock-lambda-consumer

# 2. Check Lambda function exists
aws lambda get-function \
  --function-name stock-lambda-consumer-StockAnalyticsProcessor

# 3. Check DynamoDB table exists
aws dynamodb describe-table \
  --table-name stock-analytics

# 4. Check event source mapping is enabled
aws lambda list-event-source-mappings \
  --function-name stock-lambda-consumer-StockAnalyticsProcessor

# 5. Monitor CloudWatch logs
aws logs tail /aws/lambda/stock-lambda-consumer-StockAnalyticsProcessor --follow

# 6. Query for analytics data (after a few minutes)
./scripts/query_analytics.sh AAPL 10
```

## Troubleshooting

### No data appearing in DynamoDB

1. **Check producer is running:**
   ```bash
   cd ../StockLambdaProducer
   ./scripts/monitor_logs.sh
   ```

2. **Check event source mapping is enabled:**
   ```bash
   aws lambda list-event-source-mappings \
     --function-name stock-lambda-consumer-StockAnalyticsProcessor
   ```

3. **Check consumer logs for errors:**
   ```bash
   ./scripts/monitor_logs.sh processor
   ```

4. **Verify Kinesis stream has data:**
   ```bash
   aws kinesis get-records \
     --shard-iterator $(aws kinesis get-shard-iterator \
       --stream-name stock-prices-stream \
       --shard-id shardId-000000000000 \
       --shard-iterator-type LATEST \
       --query 'ShardIterator' \
       --output text)
   ```

### Consumer keeps disabling

This is normal! The monitor Lambda automatically disables the consumer:
- Outside market hours (9:30 AM - 4:00 PM ET)
- When no data received for 10+ minutes

To keep it running 24/7 for testing:
```bash
export TEST_MODE=true
./scripts/deploy.sh
```

## Need Help?

1. Check [README.md](README.md) for full documentation
2. Check [QUICKSTART.md](QUICKSTART.md) for quick setup
3. Review logs: `./scripts/monitor_logs.sh processor`
4. Check AWS CloudFormation console for stack events
