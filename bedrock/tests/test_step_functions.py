#!/usr/bin/env python3
"""
Test Step Functions Execution
Tests the deployed state machine with sample inputs
"""

import boto3
import json
import time

# AWS clients
sfn = boto3.client('stepfunctions', region_name='us-east-1')

# Configuration
STATE_MACHINE_ARN = 'arn:aws:states:us-east-1:618048437522:stateMachine:pf-schedule-urgent-project'

def test_execution(query, customer_id='CUST001'):
    """
    Start a Step Functions execution and wait for results
    """
    print(f"\n{'='*80}")
    print(f"Testing Query: {query}")
    print(f"Customer ID: {customer_id}")
    print(f"{'='*80}\n")

    # Start execution
    execution_name = f"test-{int(time.time())}"

    print(f"Starting execution: {execution_name}")

    try:
        response = sfn.start_execution(
            stateMachineArn=STATE_MACHINE_ARN,
            name=execution_name,
            input=json.dumps({
                'query': query,
                'customer_id': customer_id,
                'client_id': 'CLIENT001',
                'sessionId': f'test-session-{customer_id}'
            })
        )

        execution_arn = response['executionArn']
        print(f"Execution ARN: {execution_arn}")
        print("\nWaiting for execution to complete...")

        # Poll for completion
        max_wait = 30  # seconds
        for i in range(max_wait):
            status_response = sfn.describe_execution(
                executionArn=execution_arn
            )

            status = status_response['status']
            print(f"  [{i+1}/{max_wait}] Status: {status}")

            if status == 'SUCCEEDED':
                output = json.loads(status_response['output'])
                print("\n✅ Execution SUCCEEDED!")
                print(f"\nOutput:")
                print(json.dumps(output, indent=2))
                return output

            elif status in ['FAILED', 'TIMED_OUT', 'ABORTED']:
                print(f"\n❌ Execution {status}")
                if 'error' in status_response:
                    print(f"Error: {status_response['error']}")
                if 'cause' in status_response:
                    print(f"Cause: {status_response['cause']}")
                return None

            time.sleep(1)

        print(f"\n⏱️  Execution still running after {max_wait} seconds")
        return None

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == '__main__':
    print("\n" + "="*80)
    print("AWS STEP FUNCTIONS TEST - Schedule Urgent Project")
    print("="*80)

    # Test Case 1: Find urgent project
    test_execution(
        query="Schedule my most urgent project for the earliest time",
        customer_id='CUST001'
    )

    # Give some time between tests
    time.sleep(2)

    # Test Case 2: Simple query (should show projects)
    print("\n\n")
    test_execution(
        query="Show me my urgent projects",
        customer_id='CUST001'
    )

    print("\n" + "="*80)
    print("Testing Complete!")
    print("="*80)
    print("\nView executions in AWS Console:")
    print("https://console.aws.amazon.com/states/home?region=us-east-1#/statemachines")
