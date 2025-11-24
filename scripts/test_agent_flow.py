#!/usr/bin/env python3
"""
Interactive Agent Testing Script
Tests the complete workflow: Chitchat -> List Projects -> Get Project Details

Usage:
  ./test_agent_flow.py

The script will interactively prompt for:
- Client ID
- User ID
- Bearer Token

Then it will:
1. Test chitchat functionality
2. Retrieve list of projects
3. Iterate through first 2 projects and get details
"""

import boto3
import json
import time
import sys
from pathlib import Path

# Color codes for output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text):
    """Print a formatted header"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(70)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}\n")

def print_success(text):
    """Print success message"""
    print(f"{Colors.OKGREEN}✅ {text}{Colors.ENDC}")

def print_error(text):
    """Print error message"""
    print(f"{Colors.FAIL}❌ {text}{Colors.ENDC}")

def print_info(text):
    """Print info message"""
    print(f"{Colors.OKCYAN}ℹ️  {text}{Colors.ENDC}")

def print_warning(text):
    """Print warning message"""
    print(f"{Colors.WARNING}⚠️  {text}{Colors.ENDC}")

def load_agent_config():
    """Load agent configuration"""
    script_dir = Path(__file__).parent
    config_file = script_dir.parent / "config" / "agent_config.dev.json"

    if not config_file.exists():
        print_error(f"Config file not found: {config_file}")
        print_info("Please run DEPLOY.sh first to create agent configuration")
        sys.exit(1)

    with open(config_file, 'r') as f:
        return json.load(f)

def get_user_input():
    """Get user input for testing"""
    print_header("Agent Testing - User Input")

    print(f"{Colors.BOLD}Please provide the following credentials:{Colors.ENDC}\n")

    client_id = input(f"{Colors.OKCYAN}Client ID: {Colors.ENDC}").strip()
    if not client_id:
        print_error("Client ID is required")
        sys.exit(1)

    user_id = input(f"{Colors.OKCYAN}User ID: {Colors.ENDC}").strip()
    if not user_id:
        print_error("User ID is required")
        sys.exit(1)

    bearer_token = input(f"{Colors.OKCYAN}Bearer Token: {Colors.ENDC}").strip()
    if not bearer_token:
        print_error("Bearer Token is required")
        sys.exit(1)

    return {
        'client_id': client_id,
        'user_id': user_id,
        'bearer_token': bearer_token
    }

def invoke_agent(agent_id, alias_id, session_id, message, session_state=None, region='us-east-1'):
    """Invoke a Bedrock agent"""
    client = boto3.client('bedrock-agent-runtime', region_name=region)

    invoke_params = {
        'agentId': agent_id,
        'agentAliasId': alias_id,
        'sessionId': session_id,
        'inputText': message
    }

    if session_state:
        invoke_params['sessionState'] = session_state

    try:
        response = client.invoke_agent(**invoke_params)

        # Read event stream
        event_stream = response['completion']
        full_response = ""

        for event in event_stream:
            if 'chunk' in event:
                chunk = event['chunk']
                if 'bytes' in chunk:
                    text = chunk['bytes'].decode('utf-8')
                    full_response += text

        return {
            'success': True,
            'response': full_response,
            'raw_response': response
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__
        }

def test_chitchat(config, credentials, session_id):
    """Test 1: Chitchat functionality"""
    print_header("Test 1: Chitchat")

    supervisor_id = config['supervisor_id']
    supervisor_alias = config['supervisor_alias']

    print_info(f"Agent: Supervisor ({supervisor_id})")
    print_info(f"Query: Hello, how are you today?")

    # Create session state with customer context
    session_state = {
        'sessionAttributes': {
            'client_id': credentials['client_id'],
            'customer_id': credentials['user_id'],
            'customer_type': 'standard',
            'bearer_token': credentials['bearer_token']
        }
    }

    result = invoke_agent(
        supervisor_id,
        supervisor_alias,
        session_id,
        "Hello, how are you today?",
        session_state,
        config['region']
    )

    if result['success']:
        print_success("Chitchat test passed")
        print(f"\n{Colors.BOLD}Response:{Colors.ENDC}")
        print(f"{Colors.OKGREEN}{result['response']}{Colors.ENDC}\n")
        return True
    else:
        print_error(f"Chitchat test failed: {result['error']}")
        return False

def test_list_projects(config, credentials, session_id):
    """Test 2: List projects"""
    print_header("Test 2: List Projects")

    supervisor_id = config['supervisor_id']
    supervisor_alias = config['supervisor_alias']

    print_info(f"Agent: Supervisor ({supervisor_id})")
    print_info(f"Query: Show me my projects")

    session_state = {
        'sessionAttributes': {
            'client_id': credentials['client_id'],
            'customer_id': credentials['user_id'],
            'customer_type': 'standard',
            'bearer_token': credentials['bearer_token']
        }
    }

    result = invoke_agent(
        supervisor_id,
        supervisor_alias,
        session_id,
        "Show me my projects",
        session_state,
        config['region']
    )

    if result['success']:
        print_success("List projects test passed")
        print(f"\n{Colors.BOLD}Response:{Colors.ENDC}")
        print(f"{Colors.OKGREEN}{result['response']}{Colors.ENDC}\n")

        # Try to extract project IDs from response
        project_ids = extract_project_ids(result['response'])
        if project_ids:
            print_info(f"Found {len(project_ids)} project ID(s): {', '.join(project_ids[:5])}")
        else:
            print_warning("Could not automatically extract project IDs from response")

        return {
            'success': True,
            'response': result['response'],
            'project_ids': project_ids
        }
    else:
        print_error(f"List projects test failed: {result['error']}")
        return {'success': False}

def extract_project_ids(response_text):
    """Try to extract project IDs from the response"""
    import re

    # Try multiple patterns to find project IDs
    patterns = [
        r'project[_\s]*id[:\s]+(\d+)',  # project_id: 123 or project id: 123
        r'id[:\s]+(\d+)',                # id: 123
        r'\b(\d{5,})\b',                 # Any number with 5+ digits
    ]

    project_ids = []
    for pattern in patterns:
        matches = re.findall(pattern, response_text, re.IGNORECASE)
        project_ids.extend(matches)
        if project_ids:
            break

    # Remove duplicates while preserving order
    seen = set()
    unique_ids = []
    for pid in project_ids:
        if pid not in seen:
            seen.add(pid)
            unique_ids.append(pid)

    return unique_ids

def test_project_details(config, credentials, session_id, project_ids):
    """Test 3: Get project details"""
    print_header("Test 3: Get Project Details")

    if not project_ids:
        print_warning("No project IDs available for testing")
        print_info("Please enter project IDs manually (comma-separated):")
        manual_ids = input(f"{Colors.OKCYAN}Project IDs: {Colors.ENDC}").strip()
        if manual_ids:
            project_ids = [pid.strip() for pid in manual_ids.split(',')]
        else:
            print_warning("Skipping project details test")
            return

    supervisor_id = config['supervisor_id']
    supervisor_alias = config['supervisor_alias']

    # Test with first 2 projects
    test_projects = project_ids[:2]

    print_info(f"Testing with {len(test_projects)} project(s): {', '.join(test_projects)}")

    session_state = {
        'sessionAttributes': {
            'client_id': credentials['client_id'],
            'customer_id': credentials['user_id'],
            'customer_type': 'standard',
            'bearer_token': credentials['bearer_token']
        }
    }

    for idx, project_id in enumerate(test_projects, 1):
        print(f"\n{Colors.BOLD}--- Project {idx}/{len(test_projects)} (ID: {project_id}) ---{Colors.ENDC}")

        query = f"Give me details for project {project_id}"
        print_info(f"Query: {query}")

        result = invoke_agent(
            supervisor_id,
            supervisor_alias,
            session_id,
            query,
            session_state,
            config['region']
        )

        if result['success']:
            print_success(f"Project {project_id} details retrieved")
            print(f"\n{Colors.BOLD}Response:{Colors.ENDC}")
            print(f"{Colors.OKGREEN}{result['response']}{Colors.ENDC}\n")
        else:
            print_error(f"Failed to get details for project {project_id}: {result['error']}")

        # Small delay between requests
        if idx < len(test_projects):
            time.sleep(1)

def main():
    """Main test flow"""
    print(f"{Colors.BOLD}{Colors.HEADER}")
    print("╔═══════════════════════════════════════════════════════════════════╗")
    print("║       AWS Bedrock Multi-Agent Testing Script                     ║")
    print("║       Interactive End-to-End Workflow Test                       ║")
    print("╚═══════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.ENDC}")

    # Load configuration
    print_info("Loading agent configuration...")
    config = load_agent_config()
    print_success(f"Configuration loaded (Environment: {config.get('environment', 'dev')})")

    # Get user credentials
    credentials = get_user_input()

    # Create session ID
    session_id = f"test-session-{int(time.time())}"
    print_info(f"Session ID: {session_id}")

    # Run tests
    results = {
        'chitchat': False,
        'list_projects': False,
        'project_details': False
    }

    # Test 1: Chitchat
    results['chitchat'] = test_chitchat(config, credentials, session_id)
    time.sleep(2)

    # Test 2: List projects
    projects_result = test_list_projects(config, credentials, session_id)
    results['list_projects'] = projects_result['success']
    time.sleep(2)

    # Test 3: Project details
    if projects_result['success']:
        test_project_details(config, credentials, session_id, projects_result.get('project_ids', []))
        results['project_details'] = True

    # Summary
    print_header("Test Summary")

    print(f"{Colors.BOLD}Results:{Colors.ENDC}")
    for test_name, passed in results.items():
        status = f"{Colors.OKGREEN}✅ PASS{Colors.ENDC}" if passed else f"{Colors.FAIL}❌ FAIL{Colors.ENDC}"
        print(f"  {test_name.replace('_', ' ').title()}: {status}")

    passed_count = sum(results.values())
    total_count = len(results)

    print(f"\n{Colors.BOLD}Total: {passed_count}/{total_count} tests passed{Colors.ENDC}\n")

    if passed_count == total_count:
        print_success("All tests passed! 🎉")
    elif passed_count > 0:
        print_warning(f"Some tests failed ({total_count - passed_count} failures)")
    else:
        print_error("All tests failed")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.WARNING}Test interrupted by user{Colors.ENDC}")
        sys.exit(0)
    except Exception as e:
        print_error(f"Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
