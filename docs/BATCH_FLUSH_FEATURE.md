# Batch Flush Feature Documentation

## Overview

The Stock Lambda Consumer implements intelligent batch flushing to prevent memory buildup during long-running Lambda executions. This feature ensures that analytics are written to DynamoDB regularly without overwhelming Lambda's memory limits.

## Problem Statement

Without periodic flushing, the Lambda function could:
1. **Run out of memory** during high-volume processing
2. **Lose data** if Lambda times out before flushing
3. **Experience degraded performance** as batch size grows

## Solution

Three-tiered automatic flushing mechanism:

### 1. Time-Based Flushing (Default: 15 minutes)

```python
# Flushes analytics to DynamoDB every 15 minutes
if time_since_flush >= flush_interval:
    flush_batch()
```

**Benefits:**
- Prevents unbounded memory growth
- Regular data persistence
- Predictable write patterns

**Configuration:**
```bash
export BATCH_WRITE_INTERVAL_MINUTES=15
```

### 2. Size-Based Flushing (Default: 500 items)

```python
# Forces flush when batch reaches maximum size
if len(analytics_batch) >= max_size:
    flush_batch()
```

**Benefits:**
- Safety mechanism for burst traffic
- Prevents memory overflow
- Adapts to data volume

**Configuration:**
```bash
export BATCH_MAX_SIZE=500
```

### 3. End-of-Execution Flushing

```python
# Always flush remaining items at end of Lambda invocation
if analytics_batch:
    flush_batch()
```

**Benefits:**
- Ensures no data loss
- Handles partial batches
- Clean Lambda exit

## Implementation Details

### Global State Management

```python
# Batch management
analytics_batch: List[Dict[str, Any]] = []
last_batch_flush: Optional[datetime] = None
```

The batch is maintained in Lambda's global scope for reuse across invocations within the same container.

### Flush Function

```python
def flush_batch() -> Dict[str, int]:
    """Flush current analytics batch to DynamoDB."""
    if not analytics_batch:
        return {'success': 0, 'failed': 0}

    result = dynamodb_writer.batch_write_analytics(analytics_batch)
    analytics_batch.clear()
    last_batch_flush = datetime.now()

    return result
```

### Check Function

```python
def should_flush_batch() -> bool:
    """Determine if batch should be flushed."""
    # Check size limit
    if len(analytics_batch) >= config.batch_max_size:
        return True

    # Check time limit
    if last_batch_flush:
        time_since_flush = datetime.now() - last_batch_flush
        if time_since_flush >= timedelta(minutes=config.batch_write_interval_minutes):
            return True

    return False
```

## Usage Examples

### High-Volume Scenario

For streams with many updates per second:

```bash
# Flush more frequently with smaller batches
export BATCH_WRITE_INTERVAL_MINUTES=5
export BATCH_MAX_SIZE=250
./scripts/deploy.sh
```

**Use Case:** 8+ stocks updating every 5 seconds during volatile market periods

### Low-Volume Scenario

For streams with infrequent updates:

```bash
# Batch more for efficiency
export BATCH_WRITE_INTERVAL_MINUTES=30
export BATCH_MAX_SIZE=1000
./scripts/deploy.sh
```

**Use Case:** 2-3 stocks updating every 30 seconds during quiet trading

### Balanced (Default)

```bash
# Default settings work for most scenarios
export BATCH_WRITE_INTERVAL_MINUTES=15
export BATCH_MAX_SIZE=500
./scripts/deploy.sh
```

**Use Case:** 5-8 stocks updating every 5-10 seconds

## Monitoring

### CloudWatch Logs

The Lambda function logs flush operations:

```
Flushing batch of 42 analytics to DynamoDB
Batch flush complete: 42 success, 0 failed
```

```
Batch size (500) reached max size (500), forcing flush
Flushing batch of 500 analytics to DynamoDB
```

```
Batch flush interval (15 min) reached, flushing batch
Flushing batch of 127 analytics to DynamoDB
```

### Lambda Response

The handler returns flush metrics:

```json
{
  "statusCode": 200,
  "body": {
    "processed": 523,
    "failed": 0,
    "total_records": 523,
    "periodic_flushes": 2,
    "batch_remaining": 0,
    "final_flush_success": 23,
    "final_flush_failed": 0
  }
}
```

## Performance Impact

### Memory Usage

**Without Batch Flush:**
- Memory grows linearly with processing time
- Risk of OOM errors after ~20 minutes
- Unpredictable memory consumption

**With Batch Flush:**
- Memory bounded by `batch_max_size`
- Predictable memory footprint
- Safe for long-running executions

### DynamoDB Write Patterns

**Time-Based Flushing:**
- Regular write intervals
- Predictable throughput
- Easier to provision capacity

**Size-Based Flushing:**
- Adapts to data volume
- Prevents write throttling
- Maintains batch efficiency

## Testing

The feature includes comprehensive tests:

```python
def test_flush_batch():
    """Test batch flushing."""
    # Add analytics to batch
    analytics_batch.extend([...])

    # Flush
    result = flush_batch()

    assert result['success'] == 2
    assert len(analytics_batch) == 0
    assert last_batch_flush is not None


def test_should_flush_batch_size():
    """Test size-based flush trigger."""
    # Fill batch to max size
    for i in range(max_size):
        analytics_batch.append({...})

    assert should_flush_batch() is True


def test_should_flush_batch_time():
    """Test time-based flush trigger."""
    # Set last flush to 20 minutes ago
    last_batch_flush = datetime.now() - timedelta(minutes=20)

    assert should_flush_batch() is True
```

## Best Practices

### 1. Choose Appropriate Intervals

- **High volatility:** 5-10 minutes
- **Normal trading:** 10-15 minutes
- **Low activity:** 20-30 minutes

### 2. Set Reasonable Batch Sizes

- **High volume:** 250-500 items
- **Normal volume:** 500-750 items
- **Low volume:** 750-1000 items

### 3. Monitor CloudWatch

- Watch for frequent size-based flushes (indicates high volume)
- Check for memory warnings
- Monitor DynamoDB write capacity

### 4. Adjust Based on Metrics

If you see:
- **Frequent size-based flushes:** Increase `BATCH_MAX_SIZE` or decrease interval
- **Memory warnings:** Decrease interval or batch size
- **DynamoDB throttling:** Increase interval to batch more writes

## Troubleshooting

### Batch Never Flushes

**Symptom:** No periodic flush logs

**Solutions:**
1. Check `last_batch_flush` is initialized
2. Verify config values are loaded
3. Ensure Lambda runs long enough

### Memory Issues Persist

**Symptom:** Lambda still running out of memory

**Solutions:**
1. Decrease `BATCH_WRITE_INTERVAL_MINUTES`
2. Decrease `BATCH_MAX_SIZE`
3. Increase Lambda memory allocation

### Too Many DynamoDB Writes

**Symptom:** High DynamoDB costs

**Solutions:**
1. Increase `BATCH_WRITE_INTERVAL_MINUTES`
2. Increase `BATCH_MAX_SIZE`
3. Use on-demand billing

## Future Enhancements

Potential improvements:
1. **Adaptive Flushing:** Adjust intervals based on data velocity
2. **Priority Flushing:** Flush critical signals immediately
3. **Compression:** Compress batch before write
4. **Metrics:** CloudWatch custom metrics for flush operations
5. **Circuit Breaker:** Pause processing if DynamoDB throttles

## Related Code

- `src/lambda_function.py`: Main implementation
- `src/config.py`: Configuration management
- `src/dynamodb_writer.py`: Batch write implementation
- `tests/test_lambda_function.py`: Feature tests

## Configuration Reference

| Parameter | Default | Min | Max | Description |
|-----------|---------|-----|-----|-------------|
| `BATCH_WRITE_INTERVAL_MINUTES` | 15 | 1 | 60 | Minutes between flushes |
| `BATCH_MAX_SIZE` | 500 | 25 | 1000 | Maximum batch size |

## Summary

The batch flush feature provides:
- **Memory Safety:** Prevents OOM errors
- **Data Safety:** Regular persistence
- **Flexibility:** Configurable for any workload
- **Efficiency:** Optimized batch writes
- **Visibility:** Comprehensive logging

It's a critical component for production deployments handling variable data volumes.
