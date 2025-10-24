#!/usr/bin/env python3
"""
Test script for Bedrock Agent with Session Context
Tests agents with proper sessionAttributes to verify Lambda invocations

This script tests the fix for agent hallucination issue.
After updating agent instructions with AVAILABLE ACTIONS sections,
agents should call Lambda functions instead of generating fake data.
"""

import boto3
import json
import sys
import time
import uuid

def invoke_agent_with_session(agent_id, agent_alias_id, session_id, input_text,
                               session_attributes=None, region='us-east-1'):
    """
    Invoke a Bedrock agent with session context and stream the response

    Args:
        agent_id: The agent ID
        agent_alias_id: The agent alias ID
        session_id: Unique session identifier
        input_text: The user's input text
        session_attributes: Dict of session attributes (customer_id, customer_type, etc.)
        region: AWS region (default: us-east-1)

    Returns:
        Tuple of (full_response_text, success_boolean)
    """
    client = boto3.client('bedrock-agent-runtime', region_name=region)

    print(f"\n{'='*80}")
    print(f"Session ID: {session_id}")
    print(f"User Input: {input_text}")
    if session_attributes:
        print(f"Session Attributes: {json.dumps(session_attributes, indent=2)}")
    print(f"{'='*80}\n")

    try:
        # Build request parameters
        request_params = {
            'agentId': agent_id,
            'agentAliasId': agent_alias_id,
            'sessionId': session_id,
            'inputText': input_text
        }

        # Add session state if attributes provided
        if session_attributes:
            request_params['sessionState'] = {
                'sessionAttributes': session_attributes
            }

        response = client.invoke_agent(**request_params)

        # Process the streaming response
        event_stream = response['completion']
        full_response = ""

        for event in event_stream:
            if 'chunk' in event:
                chunk = event['chunk']
                if 'bytes' in chunk:
                    chunk_text = chunk['bytes'].decode('utf-8')
                    full_response += chunk_text
                    print(chunk_text, end='', flush=True)

        print(f"\n\n{'='*80}")
        print(f"Response complete ({len(full_response)} characters)")
        print(f"{'='*80}\n")

        return full_response, True

    except Exception as e:
        print(f"\n❌ Error invoking agent: {e}")
        import traceback
        traceback.print_exc()
        return None, False


def verify_response(response, expected_data, hallucinated_data):
    """
    Verify response contains expected data and no hallucinated data

    Args:
        response: The agent's response text
        expected_data: List of strings that SHOULD be in response
        hallucinated_data: List of strings that should NOT be in response

    Returns:
        Tuple of (success_boolean, details_string)
    """
    if not response:
        return False, "No response received"

    success = True
    details = []

    # Check for expected data
    found_expected = [data for data in expected_data if data in response]
    missing_expected = [data for data in expected_data if data not in response]

    if found_expected:
        details.append(f"✅ Found expected data: {', '.join(found_expected)}")

    if missing_expected:
        details.append(f"⚠️  Missing expected data: {', '.join(missing_expected)}")
        success = False

    # Check for hallucinated data
    found_hallucinations = [data for data in hallucinated_data if data in response]

    if found_hallucinations:
        details.append(f"❌ Found hallucinated data: {', '.join(found_hallucinations)}")
        success = False
    else:
        details.append(f"✅ No hallucinated data found")

    return success, "\n   ".join(details)


def main():
    """Main test function"""

    # Agent configuration (updated by complete_setup.py)
    SUPERVISOR_AGENT_ID = "V3BW0KFBMX"  # Supervisor agent (pf_supervisor_agent)
    SUPERVISOR_ALIAS_ID = "K6BWBY1RNY"  # test alias (with customer_id delegation)
    REGION = "us-east-1"

    # Test scenarios with session context
    test_scenarios = [
        {
            "name": "Test 1: List Projects (B2C Customer)",
            "input": "Show me all my projects",
            "session_attributes": {
                "customer_id": "CUST001",
                "customer_type": "B2C"
            },
            "expected_data": ["12345", "12347", "12350", "Flooring", "Windows", "Deck"],
            "hallucinated_data": [
                "Kitchen Remodel", "Bathroom Renovation", "Exterior Painting",
                "HVAC", "Website Redesign", "Mobile App", "Database Migration"
            ],
            "description": "Should call list_projects Lambda and return real mock data"
        },
        {
            "name": "Test 2: Get Project Details",
            "input": "Tell me about project 12345",
            "session_attributes": {
                "customer_id": "CUST001",
                "customer_type": "B2C"
            },
            "expected_data": ["12345", "Flooring", "Tampa", "ORD-2025-001", "John Smith"],
            "hallucinated_data": [
                "Kitchen", "Bathroom", "Website", "Mobile App"
            ],
            "description": "Should call get_project_details Lambda and return real project info"
        },
        {
            "name": "Test 3: Get Appointment Status",
            "input": "What's the appointment status for project 12345?",
            "session_attributes": {
                "customer_id": "CUST001",
                "customer_type": "B2C"
            },
            "expected_data": ["12345", "Scheduled", "2025-10-15", "John Smith"],
            "hallucinated_data": [
                "pending approval", "not scheduled", "unknown status"
            ],
            "description": "Should call get_appointment_status Lambda"
        },
        {
            "name": "Test 4: Get Working Hours",
            "input": "What are your business hours?",
            "session_attributes": {
                "customer_id": "CUST001",
                "customer_type": "B2C"
            },
            "expected_data": ["Monday", "Friday", "9:00 AM", "6:00 PM"],
            "hallucinated_data": [
                "24/7", "open all day", "closed on weekdays"
            ],
            "description": "Should call get_working_hours Lambda"
        },
        {
            "name": "Test 5: Check Availability",
            "input": "What dates are available for project 12347?",
            "session_attributes": {
                "customer_id": "CUST001",
                "customer_type": "B2C"
            },
            "expected_data": ["2025", "available"],
            "hallucinated_data": [
                "no availability", "fully booked", "next year"
            ],
            "description": "Should call get_available_dates Lambda"
        }
    ]

    print("\n" + "="*80)
    print("BEDROCK AGENT HALLUCINATION FIX VERIFICATION TEST")
    print("="*80)
    print(f"\nSupervisor Agent ID: {SUPERVISOR_AGENT_ID}")
    print(f"Agent Alias ID: {SUPERVISOR_ALIAS_ID}")
    print(f"Region: {REGION}")
    print(f"\nTesting {len(test_scenarios)} scenarios with session context...")
    print("\n⚠️  IMPORTANT: Run these scripts FIRST:")
    print("   1. bedrock/scripts/update_agent_instructions.sh")
    print("   2. bedrock/scripts/update_collaborator_aliases.sh  ← CRITICAL!")
    print("\n   The collaborator aliases MUST point to DRAFT versions!")
    print("\n" + "="*80)

    # Track results
    passed = 0
    failed = 0
    test_results = []

    # Run tests
    for i, scenario in enumerate(test_scenarios, 1):
        session_id = f"test-{int(time.time())}-{i}"

        print(f"\n{'#'*80}")
        print(f"# {scenario['name']}")
        print(f"# Description: {scenario['description']}")
        print(f"{'#'*80}")

        response, success = invoke_agent_with_session(
            agent_id=SUPERVISOR_AGENT_ID,
            agent_alias_id=SUPERVISOR_ALIAS_ID,
            session_id=session_id,
            input_text=scenario['input'],
            session_attributes=scenario['session_attributes'],
            region=REGION
        )

        if not success:
            print(f"\n❌ Test {i} FAILED - Agent invocation error")
            failed += 1
            test_results.append({
                "test": scenario['name'],
                "status": "FAILED",
                "reason": "Agent invocation error"
            })
            continue

        # Verify response
        verification_success, details = verify_response(
            response,
            scenario['expected_data'],
            scenario['hallucinated_data']
        )

        print(f"\nVERIFICATION:")
        print(f"   {details}")

        if verification_success:
            print(f"\n✅ Test {i} PASSED - {scenario['name']}")
            passed += 1
            test_results.append({
                "test": scenario['name'],
                "status": "PASSED",
                "reason": "Real data returned, no hallucinations"
            })
        else:
            print(f"\n❌ Test {i} FAILED - {scenario['name']}")
            failed += 1
            test_results.append({
                "test": scenario['name'],
                "status": "FAILED",
                "reason": "Missing expected data or found hallucinations"
            })

        # Small delay between tests
        if i < len(test_scenarios):
            time.sleep(2)

    # Print summary
    print(f"\n{'='*80}")
    print("TEST SUMMARY")
    print(f"{'='*80}")
    print(f"\nTotal Tests: {len(test_scenarios)}")
    print(f"Passed: ✅ {passed}")
    print(f"Failed: ❌ {failed}")
    print(f"Success Rate: {(passed/len(test_scenarios)*100):.1f}%")

    print(f"\n{'='*80}")
    print("DETAILED RESULTS")
    print(f"{'='*80}\n")

    for result in test_results:
        status_icon = "✅" if result['status'] == "PASSED" else "❌"
        print(f"{status_icon} {result['test']}")
        print(f"   Status: {result['status']}")
        print(f"   Reason: {result['reason']}\n")

    print(f"{'='*80}")
    print("CLOUDWATCH VERIFICATION")
    print(f"{'='*80}\n")
    print("To verify Lambda functions were called, check CloudWatch logs:")
    print("\n  aws logs tail /aws/lambda/scheduling-agent-scheduling-actions \\")
    print("    --follow --region us-east-1\n")
    print("Expected: You should see Lambda invocation logs for each test!")
    print("If no logs appear, agents are still not calling Lambda functions.\n")

    print(f"{'='*80}")
    print("NEXT STEPS")
    print(f"{'='*80}\n")

    if failed == 0:
        print("✅ SUCCESS! All tests passed!")
        print("\nAgents are now:")
        print("  - Calling Lambda functions (not hallucinating)")
        print("  - Returning real mock data (12345, 12347, 12350)")
        print("  - NOT generating fake data\n")
        print("The hallucination fix is working correctly! 🎉\n")
    else:
        print("⚠️  SOME TESTS FAILED")
        print("\nPossible causes:")
        print("  1. Agent instructions not updated yet")
        print("     → Run: bedrock/scripts/update_agent_instructions.sh")
        print("\n  2. Collaborator aliases not updated (MOST COMMON!)")
        print("     → Run: bedrock/scripts/update_collaborator_aliases.sh")
        print("     → This updates Supervisor to use DRAFT aliases with new instructions")
        print("\n  3. Agents not prepared after update")
        print("     → Check agent status should be PREPARED")
        print("\n  4. Action groups not configured")
        print("     → Run: bedrock/scripts/configure_action_groups.sh")
        print("\n  5. Lambda functions not deployed")
        print("     → Run: bedrock/scripts/test_lambdas.sh")
        print("\nSee: bedrock/docs/HALLUCINATION_FIX_GUIDE.md for troubleshooting\n")

    print(f"{'='*80}\n")

    # Exit with appropriate code
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
