#!/usr/bin/env python3
"""
Comprehensive Agent Test Suite
Tests all 4 specialist agents with multiple test cases
Generates detailed results report
"""

import boto3
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List

# Configuration
REGION = "us-east-1"
ALIAS_ID = "TSTALIASID"

# Agent IDs
AGENTS = {
    "chitchat": "GXVZEOBQ64",
    "scheduling": "TIGRBGSXCS",
    "information": "JEK4SDJOOU",
    "notes": "CF0IPHCFFY"
}

# Test customer
TEST_CUSTOMER = {
    "customer_id": "1645975",
    "client_id": "09PF05VD"
}

client = boto3.client('bedrock-agent-runtime', region_name=REGION)

class TestResult:
    def __init__(self, test_id: str, name: str, agent: str):
        self.test_id = test_id
        self.name = name
        self.agent = agent
        self.status = "PENDING"
        self.response = ""
        self.response_length = 0
        self.error = None
        self.lambda_invoked = None
        self.notes = []

    def to_dict(self):
        return {
            "test_id": self.test_id,
            "name": self.name,
            "agent": self.agent,
            "status": self.status,
            "response_length": self.response_length,
            "lambda_invoked": self.lambda_invoked,
            "error": self.error,
            "notes": self.notes
        }

def invoke_agent(agent_id: str, input_text: str, session_attrs: Dict = None) -> Dict[str, Any]:
    """Invoke an agent and return response"""
    session_id = str(uuid.uuid4())

    try:
        response = client.invoke_agent(
            agentId=agent_id,
            agentAliasId=ALIAS_ID,
            sessionId=session_id,
            inputText=input_text,
            enableTrace=True,
            sessionState={
                'sessionAttributes': session_attrs or {}
            }
        )

        full_response = ""
        traces = []

        for event in response['completion']:
            if 'chunk' in event:
                chunk = event['chunk']
                if 'bytes' in chunk:
                    full_response += chunk['bytes'].decode('utf-8')
            elif 'trace' in event:
                traces.append(event['trace'])

        return {
            "success": True,
            "response": full_response,
            "traces": traces
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "response": "",
            "traces": []
        }

def check_lambda_invocation(response_text: str, traces: List) -> bool:
    """Check if Lambda was invoked based on traces and response content"""
    # Check traces for action group invocation
    for trace in traces:
        trace_data = trace.get('trace', {})
        if 'orchestrationTrace' in trace_data:
            orch = trace_data['orchestrationTrace']
            if 'invocationInput' in orch:
                inv_input = orch['invocationInput']
                if 'actionGroupInvocationInput' in inv_input:
                    return True

    # Check response for indicators of real data
    indicators = [
        '"mock_mode"',
        '"action":',
        '"project_id"',
        '"request_id"',
        'mock data',
        'MOCK'
    ]

    for indicator in indicators:
        if indicator in response_text:
            return True

    return False

# ============================================================================
# TEST DEFINITIONS
# ============================================================================

def run_chitchat_tests() -> List[TestResult]:
    """Run Chitchat Agent tests"""
    print("\n" + "="*80)
    print("CHITCHAT AGENT TESTS")
    print("="*80)

    results = []
    agent_id = AGENTS["chitchat"]

    tests = [
        {
            "id": "CC-1",
            "name": "Greeting - Hello",
            "input": "Hello! How are you?",
            "attrs": TEST_CUSTOMER
        },
        {
            "id": "CC-2",
            "name": "Greeting - Good Morning",
            "input": "Good morning!",
            "attrs": TEST_CUSTOMER
        },
        {
            "id": "CC-3",
            "name": "Thank You",
            "input": "Thank you so much for your help!",
            "attrs": TEST_CUSTOMER
        },
        {
            "id": "CC-4",
            "name": "Goodbye",
            "input": "Goodbye, have a great day!",
            "attrs": TEST_CUSTOMER
        },
        {
            "id": "CC-5",
            "name": "Help Request",
            "input": "Can you help me? I'm not sure how to get started.",
            "attrs": TEST_CUSTOMER
        },
        {
            "id": "CC-6",
            "name": "General Chitchat",
            "input": "How's the weather today?",
            "attrs": TEST_CUSTOMER
        }
    ]

    for test in tests:
        print(f"\nTest {test['id']}: {test['name']}")
        print("-" * 80)

        result = TestResult(test['id'], test['name'], "Chitchat")

        response = invoke_agent(agent_id, test['input'], test['attrs'])

        if response['success']:
            result.response = response['response']
            result.response_length = len(response['response'])
            result.lambda_invoked = False  # Chitchat doesn't use Lambda
            result.status = "PASS" if result.response_length > 0 else "FAIL"

            print(f"✅ Response: {result.response[:200]}...")
        else:
            result.status = "FAIL"
            result.error = response['error']
            print(f"❌ Error: {result.error}")

        results.append(result)

    return results

def run_scheduling_tests() -> List[TestResult]:
    """Run Scheduling Agent tests"""
    print("\n" + "="*80)
    print("SCHEDULING AGENT TESTS")
    print("="*80)

    results = []
    agent_id = AGENTS["scheduling"]

    tests = [
        {
            "id": "SCH-1",
            "name": "List Projects",
            "input": "Show me my projects",
            "attrs": {**TEST_CUSTOMER}
        },
        {
            "id": "SCH-2",
            "name": "Get Available Dates",
            "input": "What dates are available for project 138836?",
            "attrs": {**TEST_CUSTOMER, "project_id": "138836"}
        },
        {
            "id": "SCH-3",
            "name": "Get Time Slots",
            "input": "Show me available time slots for 2024-11-15",
            "attrs": {**TEST_CUSTOMER, "project_id": "138836", "date": "2024-11-15", "request_id": "REQ123"}
        },
        {
            "id": "SCH-4",
            "name": "Confirm Appointment (Mock)",
            "input": "Confirm appointment for 2024-11-15 at 09:00 AM",
            "attrs": {**TEST_CUSTOMER, "project_id": "138836", "date": "2024-11-15", "time": "09:00", "request_id": "REQ123"}
        },
        {
            "id": "SCH-5",
            "name": "Cancel Appointment (Mock)",
            "input": "Cancel my appointment for project 138836",
            "attrs": {**TEST_CUSTOMER, "project_id": "138836"}
        }
    ]

    for test in tests:
        print(f"\nTest {test['id']}: {test['name']}")
        print("-" * 80)

        result = TestResult(test['id'], test['name'], "Scheduling")

        response = invoke_agent(agent_id, test['input'], test['attrs'])

        if response['success']:
            result.response = response['response']
            result.response_length = len(response['response'])
            result.lambda_invoked = check_lambda_invocation(result.response, response['traces'])

            if result.lambda_invoked:
                result.status = "PASS"
                result.notes.append("Lambda invoked successfully")
                print(f"✅ Lambda invoked")
            else:
                result.status = "PARTIAL"
                result.notes.append("Lambda NOT invoked - agent responded without action")
                print(f"⚠️  Lambda NOT invoked")

            print(f"Response: {result.response[:200]}...")
        else:
            result.status = "FAIL"
            result.error = response['error']
            print(f"❌ Error: {result.error}")

        results.append(result)

    return results

def run_information_tests() -> List[TestResult]:
    """Run Information Agent tests"""
    print("\n" + "="*80)
    print("INFORMATION AGENT TESTS")
    print("="*80)

    results = []
    agent_id = AGENTS["information"]

    tests = [
        {
            "id": "INFO-1",
            "name": "Get Business Hours",
            "input": "What are your business hours?",
            "attrs": TEST_CUSTOMER
        },
        {
            "id": "INFO-2",
            "name": "Get Weather Forecast",
            "input": "What's the weather forecast for November 15, 2024?",
            "attrs": {**TEST_CUSTOMER, "date": "2024-11-15"}
        },
        {
            "id": "INFO-3",
            "name": "Get Project Information",
            "input": "Tell me about project 138836",
            "attrs": {**TEST_CUSTOMER, "project_id": "138836"}
        },
        {
            "id": "INFO-4",
            "name": "General Information Query",
            "input": "How does the scheduling process work?",
            "attrs": TEST_CUSTOMER
        }
    ]

    for test in tests:
        print(f"\nTest {test['id']}: {test['name']}")
        print("-" * 80)

        result = TestResult(test['id'], test['name'], "Information")

        response = invoke_agent(agent_id, test['input'], test['attrs'])

        if response['success']:
            result.response = response['response']
            result.response_length = len(response['response'])
            result.lambda_invoked = check_lambda_invocation(result.response, response['traces'])

            if result.lambda_invoked or result.response_length > 50:
                result.status = "PASS"
                if result.lambda_invoked:
                    result.notes.append("Lambda invoked")
                    print(f"✅ Lambda invoked")
            else:
                result.status = "PARTIAL"
                print(f"⚠️  Response received but unclear if Lambda invoked")

            print(f"Response: {result.response[:200]}...")
        else:
            result.status = "FAIL"
            result.error = response['error']
            print(f"❌ Error: {result.error}")

        results.append(result)

    return results

def run_notes_tests() -> List[TestResult]:
    """Run Notes Agent tests"""
    print("\n" + "="*80)
    print("NOTES AGENT TESTS")
    print("="*80)

    results = []
    agent_id = AGENTS["notes"]

    tests = [
        {
            "id": "NOTE-1",
            "name": "Add Note to Project",
            "input": "Add a note to project 138836: Customer prefers morning appointments",
            "attrs": {**TEST_CUSTOMER, "project_id": "138836", "note_text": "Customer prefers morning appointments"}
        },
        {
            "id": "NOTE-2",
            "name": "View Notes for Project",
            "input": "Show me all notes for project 138836",
            "attrs": {**TEST_CUSTOMER, "project_id": "138836"}
        },
        {
            "id": "NOTE-3",
            "name": "Update Existing Note",
            "input": "Update note NOTE123 to say: Customer prefers afternoon appointments after 2 PM",
            "attrs": {**TEST_CUSTOMER, "project_id": "138836", "note_id": "NOTE123", "note_text": "Customer prefers afternoon appointments after 2 PM"}
        },
        {
            "id": "NOTE-4",
            "name": "Delete Note",
            "input": "Delete note NOTE123",
            "attrs": {**TEST_CUSTOMER, "project_id": "138836", "note_id": "NOTE123"}
        }
    ]

    for test in tests:
        print(f"\nTest {test['id']}: {test['name']}")
        print("-" * 80)

        result = TestResult(test['id'], test['name'], "Notes")

        response = invoke_agent(agent_id, test['input'], test['attrs'])

        if response['success']:
            result.response = response['response']
            result.response_length = len(response['response'])
            result.lambda_invoked = check_lambda_invocation(result.response, response['traces'])

            if result.lambda_invoked or result.response_length > 50:
                result.status = "PASS"
                if result.lambda_invoked:
                    result.notes.append("Lambda invoked")
                    print(f"✅ Lambda invoked")
            else:
                result.status = "PARTIAL"
                print(f"⚠️  Response received")

            print(f"Response: {result.response[:200]}...")
        else:
            result.status = "FAIL"
            result.error = response['error']
            print(f"❌ Error: {result.error}")

        results.append(result)

    return results

# ============================================================================
# MAIN TEST EXECUTION
# ============================================================================

def main():
    print("\n" + "="*80)
    print("COMPREHENSIVE AGENT TEST SUITE")
    print("="*80)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Region: {REGION}")
    print(f"Test Customer: {TEST_CUSTOMER['customer_id']}")
    print("="*80)

    all_results = []

    # Run tests in order
    all_results.extend(run_chitchat_tests())
    all_results.extend(run_scheduling_tests())
    all_results.extend(run_information_tests())
    all_results.extend(run_notes_tests())

    # Generate summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    by_status = {"PASS": 0, "PARTIAL": 0, "FAIL": 0}
    by_agent = {"Chitchat": [], "Scheduling": [], "Information": [], "Notes": []}

    for result in all_results:
        by_status[result.status] += 1
        by_agent[result.agent].append(result)

    print(f"\nOverall Results:")
    print(f"  ✅ PASS:    {by_status['PASS']}")
    print(f"  ⚠️  PARTIAL: {by_status['PARTIAL']}")
    print(f"  ❌ FAIL:    {by_status['FAIL']}")
    print(f"  📊 TOTAL:   {len(all_results)}")

    print(f"\nBy Agent:")
    for agent, results in by_agent.items():
        passed = sum(1 for r in results if r.status == "PASS")
        print(f"  {agent}: {passed}/{len(results)} passed")

    # Save detailed results
    output_file = "AGENT_TEST_RESULTS.json"
    with open(output_file, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total": len(all_results),
                "passed": by_status['PASS'],
                "partial": by_status['PARTIAL'],
                "failed": by_status['FAIL']
            },
            "results": [r.to_dict() for r in all_results]
        }, f, indent=2)

    print(f"\n✅ Detailed results saved to: {output_file}")

    return all_results

if __name__ == "__main__":
    results = main()
