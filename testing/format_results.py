#!/usr/bin/env python3
"""
Format test results into readable tables
Usage: ./test_suite_1.sh | python3 format_results.py
"""

import sys
import json
import re
from typing import Dict, Any, List

# ANSI color codes
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


def extract_json_responses(text: str) -> List[Dict[str, Any]]:
    """Extract JSON responses from test output using line-by-line parsing"""
    responses = []
    lines = text.split('\n')

    for line in lines:
        # Skip empty lines and non-JSON lines
        line = line.strip()
        if not line or not line.startswith('{'):
            continue

        try:
            # Try to parse the entire line as JSON
            data = json.loads(line)
            # Only include if it looks like a test response
            if 'response' in data or 'error' in data or 'message' in data:
                responses.append(data)
        except json.JSONDecodeError:
            # If single line fails, try to find JSON by matching braces
            brace_count = 0
            start_idx = -1

            for i, char in enumerate(line):
                if char == '{':
                    if brace_count == 0:
                        start_idx = i
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0 and start_idx != -1:
                        try:
                            json_str = line[start_idx:i+1]
                            data = json.loads(json_str)
                            if 'response' in data or 'error' in data or 'message' in data:
                                responses.append(data)
                                break
                        except json.JSONDecodeError:
                            continue

    return responses


def extract_test_info(text: str) -> List[tuple]:
    """Extract test numbers and descriptions"""
    test_pattern = r'📝\s+Test\s+(\d+\.\d+):\s+(.+?)(?=\n|$)'
    matches = re.findall(test_pattern, text)
    return matches


def truncate_string(s: str, max_len: int = 60) -> str:
    """Truncate string to max length"""
    if len(s) <= max_len:
        return s
    return s[:max_len-3] + "..."


def format_performance(perf: Dict[str, float]) -> str:
    """Format performance metrics"""
    if not perf:
        return "N/A"

    parts = []
    if 'total' in perf:
        parts.append(f"Total: {perf['total']:.2f}s")
    if 'classification' in perf:
        parts.append(f"Classify: {perf['classification']:.2f}s")
    if 'lambda_direct' in perf:
        parts.append(f"Lambda: {perf['lambda_direct']:.2f}s")
    if 'bedrock_invoke' in perf:
        parts.append(f"Bedrock: {perf['bedrock_invoke']:.2f}s")
    if 'stream_processing' in perf:
        parts.append(f"Stream: {perf['stream_processing']:.2f}s")

    return " | ".join(parts) if parts else "N/A"


def extract_response_text(data: Dict[str, Any]) -> str:
    """Extract the main response text from various formats"""
    # Try response field first
    if 'response' in data:
        resp = data['response']

        # If response is a JSON string, try to parse it
        if isinstance(resp, str):
            # Check for code blocks (```json)
            if resp.startswith('```json'):
                # Extract JSON from code block
                json_match = re.search(r'```json\s*(\{.+?\})\s*```', resp, re.DOTALL)
                if json_match:
                    try:
                        parsed = json.loads(json_match.group(1))
                        if 'action' in parsed:
                            action = parsed.get('action', 'unknown')
                            if action == '<REDACTED>':
                                action = 'get_available_dates'
                            # Check if dates are available
                            if 'available_dates' in parsed:
                                count = len(parsed['available_dates'])
                                return f"Available dates retrieved ({count} dates)"
                            return f"Action: {action}"
                    except:
                        pass
                # Fallback to text after code block
                return resp.split('```')[-1].strip() if '```' in resp else resp

            # Check for regular JSON string
            if resp.startswith('{'):
                try:
                    parsed = json.loads(resp)
                    # Look for message or error in parsed JSON
                    if 'message' in parsed:
                        msg = parsed['message']
                        # Add project count if available
                        if 'projects' in parsed:
                            count = len(parsed['projects'])
                            return f"{msg} ({count} projects)"
                        return msg
                    elif 'error' in parsed:
                        return f"❌ ERROR: {parsed['error']}"
                    elif 'action' in parsed:
                        action = parsed.get('action', 'unknown')
                        # For project details, show status if available
                        if action == 'get_project_details':
                            status = parsed.get('project', {}).get('status', 'Unknown')
                            if status == 'Unknown':
                                return f"❌ ERROR: Project details not found"
                            return f"Project details: Status={status}"
                        return f"Action: {action}"
                    elif 'summary' in parsed:
                        return parsed['summary']
                except:
                    pass

        return str(resp)

    # Try error field
    if 'error' in data:
        return f"❌ ERROR: {data['error']}"

    # Try message field
    if 'message' in data:
        return data['message']

    return "No response"


def print_table_header():
    """Print table header"""
    print(f"\n{Colors.BOLD}{'='*150}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'Test':<8} {'Agent':<18} {'Type':<10} {'Time':<12} {'Response':<80}{Colors.END}")
    print(f"{Colors.BOLD}{'='*150}{Colors.END}")


def print_table_row(test_num: str, test_desc: str, data: Dict[str, Any]):
    """Print a formatted table row"""
    # Extract fields
    agent = data.get('agent_name', 'Unknown')
    intent = data.get('intent', 'N/A')
    direct = data.get('direct_call', False)
    call_type = "Direct" if direct else "Agent"
    perf = data.get('performance', {})

    # Get total time
    total_time = perf.get('total', 0) if perf else 0
    time_str = f"{total_time:.2f}s" if total_time > 0 else "N/A"

    # Color code by call type
    type_color = Colors.GREEN if direct else Colors.YELLOW

    # Get response text (truncated)
    response_text = extract_response_text(data)
    response_short = truncate_string(response_text, 80)

    # Color code response based on errors
    if "ERROR" in response_short or "error" in response_short.lower():
        response_color = Colors.RED
    elif "success" in response_short.lower():
        response_color = Colors.GREEN
    else:
        response_color = ""

    # Print row
    print(f"{test_num:<8} {agent:<18} {type_color}{call_type:<10}{Colors.END} {time_str:<12} {response_color}{response_short}{Colors.END}")

    # Print test description as subtitle
    if test_desc:
        print(f"{Colors.BLUE}         └─ {test_desc}{Colors.END}")


def print_performance_summary(responses: List[Dict[str, Any]]):
    """Print performance summary statistics"""
    if not responses:
        return

    print(f"\n{Colors.BOLD}{'='*150}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}Performance Summary{Colors.END}")
    print(f"{Colors.BOLD}{'='*150}{Colors.END}")

    direct_calls = [r for r in responses if r.get('direct_call')]
    agent_calls = [r for r in responses if not r.get('direct_call')]

    print(f"\n{Colors.BOLD}Call Distribution:{Colors.END}")
    print(f"  • Direct Lambda Calls: {len(direct_calls)}")
    print(f"  • Bedrock Agent Calls: {len(agent_calls)}")

    if direct_calls:
        direct_times = [r.get('performance', {}).get('total', 0) for r in direct_calls if r.get('performance')]
        if direct_times:
            avg_direct = sum(direct_times) / len(direct_times)
            min_direct = min(direct_times)
            max_direct = max(direct_times)
            print(f"\n{Colors.BOLD}Direct Lambda Performance:{Colors.END}")
            print(f"  • Average: {avg_direct:.2f}s")
            print(f"  • Min: {min_direct:.2f}s")
            print(f"  • Max: {max_direct:.2f}s")

    if agent_calls:
        agent_times = [r.get('performance', {}).get('total', 0) for r in agent_calls if r.get('performance')]
        if agent_times:
            avg_agent = sum(agent_times) / len(agent_times)
            min_agent = min(agent_times)
            max_agent = max(agent_times)
            print(f"\n{Colors.BOLD}Bedrock Agent Performance:{Colors.END}")
            print(f"  • Average: {avg_agent:.2f}s")
            print(f"  • Min: {min_agent:.2f}s")
            print(f"  • Max: {max_agent:.2f}s")


def print_errors(responses: List[Dict[str, Any]]):
    """Print error summary"""
    errors = []

    for idx, resp in enumerate(responses, 1):
        response_text = extract_response_text(resp)
        if "ERROR" in response_text or "error" in response_text.lower():
            errors.append((idx, response_text))

    if errors:
        print(f"\n{Colors.BOLD}{'='*150}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.RED}Errors Found: {len(errors)}{Colors.END}")
        print(f"{Colors.BOLD}{'='*150}{Colors.END}")

        for test_num, error_msg in errors:
            print(f"{Colors.RED}Test {test_num}: {truncate_string(error_msg, 130)}{Colors.END}")


def main():
    """Main function to process and format test results"""
    # Read all input
    input_text = sys.stdin.read()

    # Extract test information
    test_infos = extract_test_info(input_text)

    # Extract JSON responses
    responses = extract_json_responses(input_text)

    if not responses:
        print(f"{Colors.YELLOW}No JSON responses found in input{Colors.END}")
        return

    # Print suite header
    suite_match = re.search(r'Test Suite (\d+): (.+)', input_text)
    if suite_match:
        suite_num = suite_match.group(1)
        suite_name = suite_match.group(2)
        print(f"\n{Colors.BOLD}{Colors.BLUE}╔{'═'*148}╗{Colors.END}")
        print(f"{Colors.BOLD}{Colors.BLUE}║ Test Suite {suite_num}: {suite_name:<132}║{Colors.END}")
        print(f"{Colors.BOLD}{Colors.BLUE}╚{'═'*148}╝{Colors.END}")

    # Print session ID
    session_match = re.search(r'Session ID: ([\w-]+)', input_text)
    if session_match:
        session_id = session_match.group(1)
        print(f"{Colors.CYAN}Session: {session_id}{Colors.END}")

    # Print table
    print_table_header()

    for idx, (test_num, test_desc) in enumerate(test_infos):
        if idx < len(responses):
            print_table_row(test_num, test_desc, responses[idx])

    print(f"{Colors.BOLD}{'='*150}{Colors.END}")

    # Print summaries
    print_performance_summary(responses)
    print_errors(responses)

    print(f"\n{Colors.BOLD}{Colors.GREEN}✓ Test suite completed{Colors.END}\n")


if __name__ == "__main__":
    main()
