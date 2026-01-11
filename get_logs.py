
import boto3
import time

client = boto3.client('logs', region_name='eu-central-1')
log_group = '/aws/lambda/TacMed_Backend'

try:
    streams = client.describe_log_streams(
        logGroupName=log_group,
        orderBy='LastEventTime',
        descending=True,
        limit=1
    )
    stream_name = streams['logStreams'][0]['logStreamName']
    print(f"Reading stream: {stream_name}")
    
    resp = client.get_log_events(
        logGroupName=log_group,
        logStreamName=stream_name,
        limit=10,
        startFromHead=False
    )
    
    for event in resp['events']:
        print(f"{event['timestamp']} : {event['message'].strip()}")
except Exception as e:
    print(f"Error: {e}")
