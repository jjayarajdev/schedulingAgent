import boto3
import time
from datetime import datetime

client = boto3.client('logs', region_name='us-east-1')

# Log groups to check
LOG_GROUPS = [
    '/aws/lambda/pf-lex-fulfillment-dev',
    '/aws/lambda/pf-orchestrator',
    '/aws/lambda/pf-scheduling-actions',
    '/aws/lambda/pf-customer-lookup-dev',
]

# Keywords to filter for debugging customer/fallback issues
KEYWORDS = [
    'customer', 'Customer', 'CUSTOMER',
    'fallback', 'Fallback', 'FALLBACK',
    'intent', 'Intent', 'INTENT',
    'job', 'Job', 'project', 'Project',
    'ERROR', 'error', 'Error',
    'response', 'Response',
    'orchestrator', 'ORCHESTRATOR',
    'reschedule', 'cancel',
    'slot', 'session',
    'phone', 'Phone', 'caller',
    'lookup', 'Lookup',
    'START', 'END', 'REPORT'
]

for log_group in LOG_GROUPS:
    print(f"\n{'='*80}")
    print(f"=== LOGS: {log_group} ===")
    print(f"{'='*80}\n")

    try:
        # Get the most recent log streams
        streams = client.describe_log_streams(
            logGroupName=log_group,
            orderBy='LastEventTime',
            descending=True,
            limit=5
        )

        for stream in streams['logStreams']:
            stream_name = stream['logStreamName']
            last_event = stream.get('lastEventTimestamp', 0)
            last_time = datetime.fromtimestamp(last_event/1000).strftime('%Y-%m-%d %H:%M:%S') if last_event else 'N/A'
            print(f"--- Stream: {stream_name} (Last: {last_time}) ---")

            # Get events from this stream
            events = client.get_log_events(
                logGroupName=log_group,
                logStreamName=stream_name,
                startFromHead=False,
                limit=200
            )

            for event in events['events']:
                msg = event.get('message', '')
                ts = datetime.fromtimestamp(event['timestamp']/1000).strftime('%H:%M:%S')
                # Show messages matching keywords
                if any(x in msg for x in KEYWORDS):
                    print(f"[{ts}] {msg.strip()[:600]}")
            print()
    except Exception as e:
        print(f"Error getting logs from {log_group}: {e}")
        print()
