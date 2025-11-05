#!/usr/bin/env python3
"""Test script to check Kinesis record format."""
import boto3
import json

# Create Kinesis client
kinesis = boto3.client('kinesis', region_name='us-east-1')

# Get shard iterator
response = kinesis.get_shard_iterator(
    StreamName='stock-prices-stream',
    ShardId='shardId-000000000000',
    ShardIteratorType='LATEST'
)
shard_iterator = response['ShardIterator']

# Get a record
response = kinesis.get_records(ShardIterator=shard_iterator, Limit=1)

if response['Records']:
    record = response['Records'][0]
    data = record['Data']

    print(f"Data type: {type(data)}")
    print(f"Data length: {len(data)}")
    print(f"First 100 bytes (raw): {data[:100]}")
    print(f"\nFirst 100 bytes (repr): {repr(data[:100])}")

    # Try decoding as JSON directly
    try:
        stock_data = json.loads(data)
        print(f"\n✅ JSON direct decode SUCCESS:")
        print(json.dumps(stock_data, indent=2)[:200])
    except Exception as e:
        print(f"\n❌ JSON direct decode FAILED: {e}")

else:
    print("No records available")
