#!/usr/bin/env python3
"""
Comprehensive Test Suite for All Step Functions State Machines
Tests all complex query scenarios end-to-end
"""

import boto3
import json
import time
from typing import Dict, Any, Optional

# AWS clients
sfn = boto3.client('stepfunctions', region_name='us-east-1')
account_id = boto3.client('sts').get_caller_identity()['Account']

# Configuration
REGION = 'us-east-1'
PREFIX = 'pf'

# State Machine ARNs
STATE_MACHINES = {
    'schedule_urgent': f'arn:aws:states:{REGION}:{account_id}:stateMachine:{PREFIX}-schedule-urgent-project',
    'weather_dependent': f'arn:aws:states:{REGION}:{account_id}:stateMachine:{PREFIX}-schedule-weather-dependent',
    'batch_scheduling': f'arn:aws:states:{REGION}:{account_id}:stateMachine:{PREFIX}-schedule-batch-projects',
    'with_preferences': f'arn:aws:states:{REGION}:{account_id}:stateMachine:{PREFIX}-schedule-with-preferences'
}

def test_execution(state_machine_arn: str, test_input: Dict[str, Any],
                   test_name: str, max_wait: int = 30) -> Optional[Dict]:
    """
    Execute a state machine and wait for results

    Args:
        state_machine_arn: ARN of state machine to test
        test_input: Input data for execution
        test_name: Name/description of test
        max_wait: Maximum seconds to wait for completion

    Returns:
        Execution output dict or None if failed
    """
    print(f"\n{'='*80}")
    print(f"Test: {test_name}")
    print(f"State Machine: {state_machine_arn.split(':')[-1]}")
    print(f"{'='*80}\n")

    execution_name = f"test-{int(time.time())}"
    print(f"Starting execution: {execution_name}")
    print(f"Input: {json.dumps(test_input, indent=2)}\n")

    try:
        response = sfn.start_execution(
            stateMachineArn=state_machine_arn,
            name=execution_name,
            input=json.dumps(test_input)
        )

        execution_arn = response['executionArn']
        print(f"Execution ARN: {execution_arn}")
        print("\nWaiting for execution to complete...")

        # Poll for completion
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

def run_all_tests():
    """Run all test scenarios"""
    results = {
        'passed': 0,
        'failed': 0,
        'tests': []
    }

    print("\n" + "="*80)
    print("AWS STEP FUNCTIONS COMPREHENSIVE TEST SUITE")
    print("="*80)

    # Test 1: Schedule Urgent Project
    print("\n\n" + "="*80)
    print("TEST CATEGORY 1: URGENT PROJECT SCHEDULING")
    print("="*80)

    test_cases_urgent = [
        {
            'name': 'Find and schedule most urgent project',
            'input': {
                'query': 'Schedule my most urgent project for the earliest time',
                'customer_id': 'CUST001',
                'client_id': 'CLIENT001',
                'sessionId': 'test-session-urgent-1'
            }
        },
        {
            'name': 'Schedule highest priority project',
            'input': {
                'query': 'Book my highest priority installation',
                'customer_id': 'CUST001',
                'client_id': 'CLIENT001',
                'sessionId': 'test-session-urgent-2'
            }
        }
    ]

    for test_case in test_cases_urgent:
        result = test_execution(
            STATE_MACHINES['schedule_urgent'],
            test_case['input'],
            test_case['name']
        )

        test_result = {
            'category': 'Urgent Scheduling',
            'name': test_case['name'],
            'passed': result is not None and result.get('success', False)
        }
        results['tests'].append(test_result)

        if test_result['passed']:
            results['passed'] += 1
        else:
            results['failed'] += 1

        time.sleep(2)  # Pause between tests

    # Test 2: Weather-Dependent Scheduling
    print("\n\n" + "="*80)
    print("TEST CATEGORY 2: WEATHER-DEPENDENT SCHEDULING")
    print("="*80)

    test_cases_weather = [
        {
            'name': 'Schedule outdoor project based on weather',
            'input': {
                'query': 'If the weather is good, schedule my outdoor flooring project',
                'customer_id': 'CUST001',
                'client_id': 'CLIENT001',
                'sessionId': 'test-session-weather-1',
                'location': 'Tampa,FL'
            }
        },
        {
            'name': 'Check weather for outdoor project',
            'input': {
                'query': 'Check weather and schedule my deck installation',
                'customer_id': 'CUST001',
                'client_id': 'CLIENT001',
                'sessionId': 'test-session-weather-2',
                'location': 'Orlando,FL'
            }
        }
    ]

    for test_case in test_cases_weather:
        result = test_execution(
            STATE_MACHINES['weather_dependent'],
            test_case['input'],
            test_case['name']
        )

        test_result = {
            'category': 'Weather-Dependent',
            'name': test_case['name'],
            'passed': result is not None  # May succeed with suitable or not suitable
        }
        results['tests'].append(test_result)

        if test_result['passed']:
            results['passed'] += 1
        else:
            results['failed'] += 1

        time.sleep(2)

    # Test 3: Batch Scheduling
    print("\n\n" + "="*80)
    print("TEST CATEGORY 3: BATCH/MULTI-PROJECT SCHEDULING")
    print("="*80)

    test_cases_batch = [
        {
            'name': 'Schedule all pending projects',
            'input': {
                'query': 'Schedule all my pending installation projects',
                'customer_id': 'CUST001',
                'client_id': 'CLIENT001',
                'sessionId': 'test-session-batch-1',
                'filterCriteria': {
                    'type': 'status',
                    'value': 'Pending'
                }
            }
        },
        {
            'name': 'Batch schedule high priority projects',
            'input': {
                'query': 'Book all my high priority projects',
                'customer_id': 'CUST001',
                'client_id': 'CLIENT001',
                'sessionId': 'test-session-batch-2',
                'filterCriteria': {
                    'type': 'priority',
                    'value': 'HIGH'
                }
            }
        }
    ]

    for test_case in test_cases_batch:
        result = test_execution(
            STATE_MACHINES['batch_scheduling'],
            test_case['input'],
            test_case['name']
        )

        test_result = {
            'category': 'Batch Scheduling',
            'name': test_case['name'],
            'passed': result is not None
        }
        results['tests'].append(test_result)

        if test_result['passed']:
            results['passed'] += 1
        else:
            results['failed'] += 1

        time.sleep(2)

    # Test 4: Conditional Scheduling with Preferences
    print("\n\n" + "="*80)
    print("TEST CATEGORY 4: CONDITIONAL SCHEDULING WITH PREFERENCES")
    print("="*80)

    test_cases_preferences = [
        {
            'name': 'Schedule with first and second choice',
            'input': {
                'project_id': 'PRJ-78945',
                'customer_id': 'CUST001',
                'client_id': 'CLIENT001',
                'sessionId': 'test-session-pref-1',
                'preferences': {
                    'first_choice': {
                        'date': '2025-11-04',
                        'time': '10:00 AM'
                    },
                    'second_choice': {
                        'date': '2025-11-05',
                        'time': '2:00 PM'
                    },
                    'show_alternatives': True
                }
            }
        }
    ]

    for test_case in test_cases_preferences:
        result = test_execution(
            STATE_MACHINES['with_preferences'],
            test_case['input'],
            test_case['name']
        )

        test_result = {
            'category': 'Preference-Based',
            'name': test_case['name'],
            'passed': result is not None
        }
        results['tests'].append(test_result)

        if test_result['passed']:
            results['passed'] += 1
        else:
            results['failed'] += 1

        time.sleep(2)

    # Print Summary
    print("\n\n" + "="*80)
    print("TEST RESULTS SUMMARY")
    print("="*80)

    print(f"\n✅ PASSED: {results['passed']}")
    print(f"❌ FAILED: {results['failed']}")
    print(f"📊 TOTAL:  {results['passed'] + results['failed']}")

    pass_rate = (results['passed'] / (results['passed'] + results['failed']) * 100) if (results['passed'] + results['failed']) > 0 else 0
    print(f"🎯 PASS RATE: {pass_rate:.1f}%")

    print("\n" + "="*80)
    print("DETAILED RESULTS BY CATEGORY")
    print("="*80)

    categories = {}
    for test in results['tests']:
        cat = test['category']
        if cat not in categories:
            categories[cat] = {'passed': 0, 'total': 0}
        categories[cat]['total'] += 1
        if test['passed']:
            categories[cat]['passed'] += 1

    for category, stats in categories.items():
        pass_rate_cat = (stats['passed'] / stats['total'] * 100) if stats['total'] > 0 else 0
        status = "✅" if stats['passed'] == stats['total'] else "⚠️"
        print(f"\n{status} {category}:")
        print(f"   Passed: {stats['passed']}/{stats['total']} ({pass_rate_cat:.1f}%)")

    print("\n" + "="*80)
    print("View all executions in AWS Console:")
    print(f"https://console.aws.amazon.com/states/home?region={REGION}#/statemachines")
    print("="*80 + "\n")

    return results

if __name__ == '__main__':
    results = run_all_tests()

    # Exit with error code if any tests failed
    import sys
    sys.exit(0 if results['failed'] == 0 else 1)
