#!/usr/bin/env python3
"""
Interactive Bedrock Multi-Agent Test Script
Tests the supervisor agent routing with better error handling
"""

import boto3
import json
import sys
import uuid
from datetime import datetime
from typing import Optional, Dict, Any

# Color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

# Agent configuration
AGENT_ID = "5VTIWONUMO"  # Supervisor agent ID
AGENT_ALIAS_ID = "PEXPJRXIML"  # Supervisor agent alias
REGION = "us-east-1"

def print_header(text: str):
    """Print formatted header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}\n")

def print_success(text: str):
    """Print success message"""
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")

def print_error(text: str):
    """Print error message"""
    print(f"{Colors.RED}✗ {text}{Colors.END}")

def print_info(text: str):
    """Print info message"""
    print(f"{Colors.CYAN}ℹ {text}{Colors.END}")

def print_warning(text: str):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")

def check_aws_credentials() -> bool:
    """Check if AWS credentials are configured"""
    try:
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        print_success(f"AWS Credentials OK: {identity['Arn']}")
        return True
    except Exception as e:
        print_error(f"AWS Credentials Error: {e}")
        return False

def check_agent_status() -> bool:
    """Check if agent exists and is prepared"""
    try:
        client = boto3.client('bedrock-agent', region_name=REGION)
        response = client.get_agent(agentId=AGENT_ID)

        agent = response['agent']
        status = agent['agentStatus']
        model = agent['foundationModel']

        print_info(f"Agent: {agent['agentName']}")
        print_info(f"Status: {status}")
        print_info(f"Model: {model}")

        if status == 'PREPARED':
            print_success("Agent is PREPARED and ready for testing")
            return True
        else:
            print_warning(f"Agent status is {status} (expected: PREPARED)")
            return False

    except Exception as e:
        print_error(f"Failed to check agent: {e}")
        return False

def check_collaborators() -> bool:
    """Check if collaborators are associated"""
    try:
        client = boto3.client('bedrock-agent', region_name=REGION)
        response = client.list_agent_collaborators(
            agentId=AGENT_ID,
            agentVersion='DRAFT'
        )

        collaborators = response.get('agentCollaboratorSummaries', [])

        if collaborators:
            print_success(f"Found {len(collaborators)} collaborators:")
            for collab in collaborators:
                print(f"  • {collab['collaboratorName']}")
            return True
        else:
            print_warning("No collaborators found")
            return False

    except Exception as e:
        print_error(f"Failed to check collaborators: {e}")
        return False

def invoke_agent(input_text: str, session_id: Optional[str] = None) -> Optional[str]:
    """
    Invoke the Bedrock agent

    Args:
        input_text: User input
        session_id: Session ID (generates new if not provided)

    Returns:
        Agent response text or None if failed
    """
    if session_id is None:
        session_id = str(uuid.uuid4())

    try:
        client = boto3.client('bedrock-agent-runtime', region_name=REGION)

        print(f"\n{Colors.CYAN}Session: {session_id}{Colors.END}")
        print(f"{Colors.BOLD}User: {input_text}{Colors.END}")
        print(f"{Colors.CYAN}{'─'*80}{Colors.END}")

        response = client.invoke_agent(
            agentId=AGENT_ID,
            agentAliasId=AGENT_ALIAS_ID,
            sessionId=session_id,
            inputText=input_text
        )

        # Process streaming response
        event_stream = response['completion']
        full_response = ""

        print(f"{Colors.GREEN}Agent: {Colors.END}", end='', flush=True)

        for event in event_stream:
            if 'chunk' in event:
                chunk = event['chunk']
                if 'bytes' in chunk:
                    chunk_text = chunk['bytes'].decode('utf-8')
                    full_response += chunk_text
                    print(chunk_text, end='', flush=True)

        print(f"\n{Colors.CYAN}{'─'*80}{Colors.END}")

        return full_response

    except Exception as e:
        print_error(f"Agent invocation failed: {e}")

        if "AccessDeniedException" in str(e):
            print_warning("\nThis error occurs when using the API programmatically.")
            print_info("SOLUTION: Use AWS Console instead:")
            print_info("1. Go to: https://console.aws.amazon.com/bedrock/home?region=us-east-1#/agents")
            print_info("2. Click 'scheduling-agent-supervisor'")
            print_info("3. Click 'Test' button")
            print_info(f"4. Enter: {input_text}")

        return None

def run_predefined_tests():
    """Run predefined test scenarios"""
    test_scenarios = [
        {
            "name": "Chitchat (Greeting)",
            "input": "Hello! How are you today?",
            "expected": "chitchat_collaborator"
        },
        {
            "name": "Scheduling Request",
            "input": "I want to schedule an appointment",
            "expected": "scheduling_collaborator"
        },
        {
            "name": "Information Query",
            "input": "What are your working hours?",
            "expected": "information_collaborator"
        },
        {
            "name": "Notes Request",
            "input": "Can you add a note that I prefer morning appointments?",
            "expected": "notes_collaborator"
        }
    ]

    print_header("RUNNING PREDEFINED TEST SCENARIOS")

    results = []

    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n{Colors.BOLD}{Colors.YELLOW}{'#'*80}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.YELLOW}Test {i}: {scenario['name']}{Colors.END}")
        print(f"{Colors.YELLOW}Expected Routing: {scenario['expected']}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.YELLOW}{'#'*80}{Colors.END}")

        response = invoke_agent(scenario['input'])

        if response:
            results.append({"test": scenario['name'], "status": "✓ PASS"})
        else:
            results.append({"test": scenario['name'], "status": "✗ FAIL"})

        # Delay between tests
        if i < len(test_scenarios):
            import time
            time.sleep(2)

    # Print summary
    print_header("TEST RESULTS SUMMARY")
    for result in results:
        if "PASS" in result['status']:
            print_success(f"{result['test']}: {result['status']}")
        else:
            print_error(f"{result['test']}: {result['status']}")

def interactive_mode():
    """Run in interactive mode"""
    print_header("INTERACTIVE MODE")
    print_info("Enter messages to test the agent (type 'quit' to exit)")
    print_info("Type 'examples' to see sample messages\n")

    session_id = str(uuid.uuid4())
    print_info(f"Session ID: {session_id}")
    print_info("All messages in this session will share conversation context\n")

    while True:
        try:
            user_input = input(f"{Colors.BOLD}{Colors.BLUE}You: {Colors.END}").strip()

            if not user_input:
                continue

            if user_input.lower() in ['quit', 'exit', 'q']:
                print_info("Exiting interactive mode...")
                break

            if user_input.lower() == 'examples':
                print_info("\nSample messages to try:")
                print("  • Hello! How are you?")
                print("  • I want to schedule an appointment")
                print("  • What are your working hours?")
                print("  • Can you add a note that I prefer mornings?")
                print("  • Tell me about my current appointments")
                print("  • What's the weather like tomorrow?")
                print("")
                continue

            if user_input.lower() == 'new':
                session_id = str(uuid.uuid4())
                print_success(f"Started new session: {session_id}\n")
                continue

            invoke_agent(user_input, session_id)

        except KeyboardInterrupt:
            print_info("\n\nExiting...")
            break
        except Exception as e:
            print_error(f"Error: {e}")

def print_console_instructions():
    """Print instructions for AWS Console testing"""
    print_header("AWS CONSOLE TESTING INSTRUCTIONS")

    print(f"{Colors.BOLD}Step 1: Open AWS Console{Colors.END}")
    print("https://console.aws.amazon.com/bedrock/home?region=us-east-1#/agents\n")

    print(f"{Colors.BOLD}Step 2: Find Agent{Colors.END}")
    print("Click on: scheduling-agent-supervisor\n")

    print(f"{Colors.BOLD}Step 3: Test{Colors.END}")
    print("Click the 'Test' button in the top right corner\n")

    print(f"{Colors.BOLD}Step 4: Try These Messages{Colors.END}")
    messages = [
        "Hello! How are you?",
        "I want to schedule an appointment",
        "What are your working hours?",
        "Can you add a note that I prefer mornings?"
    ]
    for msg in messages:
        print(f"  {Colors.CYAN}•{Colors.END} {msg}")

    print(f"\n{Colors.GREEN}The console method bypasses API permission issues!{Colors.END}\n")

def main():
    """Main function"""
    print_header("BEDROCK MULTI-AGENT COLLABORATION TEST")
    print(f"Agent ID: {AGENT_ID}")
    print(f"Region: {REGION}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Pre-flight checks
    print_header("PRE-FLIGHT CHECKS")

    checks_passed = True

    if not check_aws_credentials():
        checks_passed = False

    if not check_agent_status():
        checks_passed = False

    if not check_collaborators():
        checks_passed = False

    if not checks_passed:
        print_warning("\nSome pre-flight checks failed, but continuing anyway...")

    # Main menu
    while True:
        print_header("MAIN MENU")
        print("1. Run predefined test scenarios (4 tests)")
        print("2. Interactive mode (chat with agent)")
        print("3. Show AWS Console instructions")
        print("4. Exit")

        choice = input(f"\n{Colors.BOLD}Select option (1-4): {Colors.END}").strip()

        if choice == '1':
            run_predefined_tests()
        elif choice == '2':
            interactive_mode()
        elif choice == '3':
            print_console_instructions()
        elif choice == '4':
            print_info("Exiting...")
            break
        else:
            print_error("Invalid choice. Please select 1-4.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_info("\n\nInterrupted by user. Exiting...")
        sys.exit(0)
