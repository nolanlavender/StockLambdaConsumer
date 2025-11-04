# Update Guide - Deploying Changes Without Teardown

## Quick Answer

**YES! You can update your stack without tearing anything down.**

```bash
# Option 1: Use the update script (with confirmation)
./scripts/update.sh

# Option 2: Use deploy script directly (auto-updates if stack exists)
./scripts/deploy.sh
```

Both preserve all your data and resources!

## How It Works

AWS CloudFormation and SAM support **stack updates** which:
- ✅ **Preserve DynamoDB data** - No data loss
- ✅ **Update Lambda code** - Deploys new function code
- ✅ **Update configuration** - Applies env var changes
- ✅ **Keep resources** - IAM roles, event mappings stay intact
- ✅ **Zero downtime** (for most changes)

## What Gets Updated vs Preserved

### Updated (Without Disruption)
- ✅ Lambda function code (`src/*.py` changes)
- ✅ Lambda environment variables
- ✅ Lambda memory/timeout settings
- ✅ CloudWatch log retention
- ✅ EventBridge schedules
- ✅ IAM policy statements

### Preserved (Never Deleted)
- ✅ **DynamoDB table and ALL data**
- ✅ Kinesis event source mapping state
- ✅ CloudWatch logs history
- ✅ IAM roles
- ✅ S3 deployment bucket

### May Cause Brief Interruption
- ⚠️ Kinesis event source mapping configuration changes
- ⚠️ DynamoDB table configuration changes (rare)

## Common Update Scenarios

### 1. Update Lambda Code Only

**Scenario:** You fixed a bug or added a feature in `src/`

```bash
# Edit your code
vim src/analytics.py

# Update (no teardown needed)
./scripts/update.sh

# Or simply
./scripts/deploy.sh
```

**Impact:** New code deployed, no data loss, no downtime

### 2. Update Environment Variables

**Scenario:** You want to change batch flush interval

```bash
# Change settings
export BATCH_WRITE_INTERVAL_MINUTES=10
export BATCH_MAX_SIZE=300

# Update
./scripts/update.sh
```

**Impact:** Lambda restarts with new settings, no data loss

### 3. Update Configuration

**Scenario:** You want to increase Lambda memory

```bash
# Edit template.yaml
vim template.yaml

# Change MemorySize from 512 to 1024

# Update
./scripts/update.sh
```

**Impact:** Lambda updated with new memory, no data loss

### 4. Update Dependencies

**Scenario:** You added a new Python package

```bash
# Add to requirements.txt
echo "pandas>=1.5.0" >> requirements.txt

# Update
./scripts/update.sh
```

**Impact:** New dependency included, no data loss

## Update Script vs Deploy Script

### `./scripts/update.sh`
- Checks if stack exists first
- Asks for confirmation
- Clear messaging about what's being updated
- **Recommended for updates**

### `./scripts/deploy.sh`
- Works for both fresh deploy AND updates
- Auto-detects if stack exists
- No confirmation prompt
- **Works for everything**

**Both are safe and preserve your data!**

## Update Process Step-by-Step

```bash
# 1. Make your changes
vim src/analytics.py

# 2. Test locally (optional)
./scripts/run_tests.sh

# 3. Update the stack
./scripts/update.sh

# 4. Monitor the update
./scripts/monitor_logs.sh processor

# 5. Verify changes
./scripts/query_analytics.sh AAPL 5
```

## What CloudFormation Updates

CloudFormation calculates the **changeset** - only what changed:

```
# Example changeset
Changes:
  - Lambda Function Code: UPDATE
  - Lambda Environment Variables: UPDATE
  - DynamoDB Table: NO CHANGE (preserved)
  - IAM Role: NO CHANGE (preserved)
```

## Rollback If Needed

If an update fails or you want to revert:

```bash
# Option 1: Rollback via Git
git log --oneline  # Find previous commit
git checkout abc123  # Go back to previous version
./scripts/update.sh

# Option 2: Rollback via CloudFormation
aws cloudformation rollback-stack --stack-name stock-lambda-consumer

# Option 3: Deploy specific version
git checkout v1.0.0
./scripts/update.sh
```

## When You SHOULD Use Teardown

Only use `./scripts/teardown.sh` when you want to:
- 🗑️ **Delete everything** and start fresh
- 🗑️ **Remove all data** from DynamoDB
- 🗑️ **Clean up resources** completely
- 🗑️ **Test fresh deployment** from scratch

Otherwise, **always use update/deploy scripts**.

## Monitoring Updates

### Watch CloudFormation Events
```bash
aws cloudformation describe-stack-events \
  --stack-name stock-lambda-consumer \
  --max-items 20
```

### Monitor Lambda Updates
```bash
# Watch logs during update
./scripts/monitor_logs.sh processor

# Check function version
aws lambda get-function \
  --function-name stock-lambda-consumer-StockAnalyticsProcessor \
  --query 'Configuration.LastModified'
```

### Verify Data Integrity
```bash
# Check data before update
./scripts/query_analytics.sh AAPL 5

# Update stack
./scripts/update.sh

# Verify data after update (should be the same!)
./scripts/query_analytics.sh AAPL 5
```

## Update Best Practices

### 1. Test Before Deploying
```bash
# Run tests
./scripts/run_tests.sh

# Validate setup
./scripts/validate_setup.sh

# Then update
./scripts/update.sh
```

### 2. Update During Low Activity
- Update outside market hours when possible
- Or during low-traffic periods
- Consumer can be disabled temporarily if needed

### 3. Monitor After Update
```bash
# Watch for errors
./scripts/monitor_logs.sh processor

# Check metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value=stock-lambda-consumer-StockAnalyticsProcessor \
  --start-time $(date -u -d '5 minutes ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum
```

### 4. Keep Git History
```bash
# Commit before updating
git add .
git commit -m "Update: Added new analytics feature"

# Update
./scripts/update.sh

# Tag releases
git tag v1.1.0
git push --tags
```

## Troubleshooting Updates

### Update Stuck

```bash
# Check stack status
aws cloudformation describe-stacks \
  --stack-name stock-lambda-consumer \
  --query 'Stacks[0].StackStatus'

# If stuck, check events
aws cloudformation describe-stack-events \
  --stack-name stock-lambda-consumer \
  --max-items 10
```

### Update Failed

```bash
# Check error
aws cloudformation describe-stack-events \
  --stack-name stock-lambda-consumer \
  --query 'StackEvents[?ResourceStatus==`UPDATE_FAILED`]'

# Retry update
./scripts/update.sh

# Or rollback
aws cloudformation rollback-stack --stack-name stock-lambda-consumer
```

### Changes Not Taking Effect

```bash
# Force function update
aws lambda update-function-code \
  --function-name stock-lambda-consumer-StockAnalyticsProcessor \
  --s3-bucket YOUR_BUCKET \
  --s3-key YOUR_KEY

# Or redeploy
sam build
sam deploy --no-confirm-changeset
```

## Example Update Workflow

Here's a complete workflow for updating analytics code:

```bash
# 1. Make changes
cat >> src/analytics.py << 'EOF'
# Added new custom indicator
def calculate_rsi(prices):
    # RSI calculation
    pass
EOF

# 2. Test changes
./scripts/run_tests.sh

# 3. Commit changes
git add src/analytics.py
git commit -m "Add RSI indicator"

# 4. Update stack
./scripts/update.sh

# 5. Monitor deployment
./scripts/monitor_logs.sh processor

# 6. Verify new field in DynamoDB
./scripts/inspect_analytics.sh AAPL 1

# 7. Check for new 'rsi' field
aws dynamodb get-item \
  --table-name stock-analytics \
  --key '{"symbol":{"S":"AAPL"},"timestamp":{"S":"2025-11-03T17:30:00"}}' \
  | jq '.Item.rsi'
```

## Summary

✅ **Use `./scripts/update.sh` or `./scripts/deploy.sh`** for ALL updates
✅ **NO teardown needed** - data is preserved automatically
✅ **Stack updates are safe** - CloudFormation handles it
✅ **Can rollback easily** if needed
✅ **Zero data loss** - DynamoDB is never deleted during updates

**You only need teardown when you want to delete EVERYTHING.**

Otherwise, just keep running `./scripts/update.sh`! 🚀
