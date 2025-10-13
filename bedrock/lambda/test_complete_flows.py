#!/usr/bin/env python3
"""
Complete Flow Test Cases for Bedrock Agent + Lambda Integration

Simulates the complete conversation flows that would happen with a real Bedrock Agent:
1. User input
2. Multiple Lambda invocations
3. Data flow between actions
4. Final response validation

Tests the entire orchestration chain to ensure seamless integration.
"""

import json
import os
import sys
import importlib.util
from datetime import datetime
from typing import Dict, Any, List

# Set mock mode
os.environ['USE_MOCK_API'] = 'true'

# Color codes for output
GREEN = '\033[92m'
RED = '\033[91m'
BLUE = '\033[94m'
YELLOW = '\033[93m'
RESET = '\033[0m'
BOLD = '\033[1m'

class LambdaInvoker:
    """Simulates how Bedrock Agent invokes Lambda functions"""

    def __init__(self):
        self.handlers = {}
        self.invocation_log = []

    def load_handler(self, lambda_dir: str):
        """Load a Lambda handler"""
        handler_path = os.path.join(lambda_dir, 'handler.py')

        # Create unique module names to avoid conflicts
        module_name = f"handler_{lambda_dir.replace('-', '_').replace('/', '_')}"

        # Clean up any previously loaded modules from this directory
        modules_to_remove = [key for key in sys.modules.keys()
                            if key in ['handler', 'config', 'mock_data']]
        for key in modules_to_remove:
            del sys.modules[key]

        # Temporarily adjust sys.path to load from correct directory
        original_path = sys.path.copy()
        sys.path.insert(0, lambda_dir)

        try:
            spec = importlib.util.spec_from_file_location(module_name, handler_path)
            module = importlib.util.module_from_spec(spec)
            # Register module before exec to allow relative imports
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
        finally:
            # Restore original sys.path
            sys.path = original_path

        self.handlers[lambda_dir] = module.lambda_handler
        return module.lambda_handler

    def invoke(self, lambda_dir: str, action: str, parameters: List[Dict]) -> Dict[str, Any]:
        """Invoke a Lambda function (simulating Bedrock Agent)"""
        if lambda_dir not in self.handlers:
            self.load_handler(lambda_dir)

        event = {
            "messageVersion": "1.0",
            "agent": {
                "name": "scheduling-agent",
                "id": "IX24FSMTQH",
                "alias": "TYJRF3CJ7F",
                "version": "1"
            },
            "sessionId": f"test-session-{datetime.now().timestamp()}",
            "sessionAttributes": {},
            "promptSessionAttributes": {},
            "actionGroup": lambda_dir.split('-')[0],
            "apiPath": f"/{action}",
            "httpMethod": "POST",
            "parameters": parameters
        }

        # Log invocation
        self.invocation_log.append({
            "timestamp": datetime.now().isoformat(),
            "lambda": lambda_dir,
            "action": action,
            "parameters": {p['name']: p['value'] for p in parameters}
        })

        # Invoke handler
        handler = self.handlers[lambda_dir]
        response = handler(event, None)

        # Extract body
        status_code = response.get('response', {}).get('httpStatusCode', 500)
        body_str = response.get('response', {}).get('responseBody', {}).get('application/json', {}).get('body', '{}')
        body = json.loads(body_str)

        return {
            'status_code': status_code,
            'body': body,
            'success': status_code == 200
        }

class FlowTestCase:
    """Represents a complete conversation flow test case"""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.steps = []
        self.validations = []

    def add_step(self, step_description: str, lambda_dir: str, action: str, parameters: List[Dict], expected_fields: List[str] = None):
        """Add a step to the flow"""
        self.steps.append({
            'description': step_description,
            'lambda_dir': lambda_dir,
            'action': action,
            'parameters': parameters,
            'expected_fields': expected_fields or []
        })

    def add_validation(self, validation_func, description: str):
        """Add a validation check"""
        self.validations.append({
            'func': validation_func,
            'description': description
        })

class FlowTestRunner:
    """Runs complete flow test cases"""

    def __init__(self):
        self.invoker = LambdaInvoker()
        self.test_results = []

    def run_test(self, test_case: FlowTestCase) -> Dict[str, Any]:
        """Run a complete flow test case"""
        print(f"\n{BOLD}{'='*80}{RESET}")
        print(f"{BOLD}{BLUE}🧪 Test Case: {test_case.name}{RESET}")
        print(f"{BOLD}{'='*80}{RESET}")
        print(f"{YELLOW}Description: {test_case.description}{RESET}\n")

        flow_data = {}  # Store data between steps
        all_steps_passed = True
        step_results = []

        # Execute each step
        for i, step in enumerate(test_case.steps, 1):
            print(f"\n{BOLD}Step {i}: {step['description']}{RESET}")
            print(f"  Lambda: {step['lambda_dir']}")
            print(f"  Action: {step['action']}")
            print(f"  Parameters: {json.dumps({p['name']: p['value'] for p in step['parameters']}, indent=4)}")

            try:
                # Invoke Lambda
                result = self.invoker.invoke(
                    step['lambda_dir'],
                    step['action'],
                    step['parameters']
                )

                if result['success']:
                    print(f"  {GREEN}✅ Status: {result['status_code']}{RESET}")

                    # Store result data for next steps
                    action_name = step['action'].replace('-', '_')
                    flow_data[action_name] = result['body']

                    # Validate expected fields
                    for field in step['expected_fields']:
                        if field in result['body']:
                            print(f"    {GREEN}✓ Field '{field}' present{RESET}")
                        else:
                            print(f"    {RED}✗ Field '{field}' missing{RESET}")
                            all_steps_passed = False

                    # Show key response data
                    print(f"\n  {BOLD}Response:{RESET}")
                    self._print_response_summary(result['body'])

                    step_results.append({
                        'step': i,
                        'description': step['description'],
                        'success': True,
                        'response': result['body']
                    })
                else:
                    print(f"  {RED}❌ Failed: Status {result['status_code']}{RESET}")
                    print(f"  {RED}Error: {result['body'].get('error', 'Unknown error')}{RESET}")
                    all_steps_passed = False
                    step_results.append({
                        'step': i,
                        'description': step['description'],
                        'success': False,
                        'error': result['body'].get('error', 'Unknown')
                    })

            except Exception as e:
                print(f"  {RED}❌ Exception: {str(e)}{RESET}")
                all_steps_passed = False
                step_results.append({
                    'step': i,
                    'description': step['description'],
                    'success': False,
                    'error': str(e)
                })

        # Run validations
        print(f"\n{BOLD}Validations:{RESET}")
        validation_results = []
        for validation in test_case.validations:
            try:
                result = validation['func'](flow_data)
                validation_results.append({
                    'description': validation['description'],
                    'success': result,
                    'message': 'Passed' if result else 'Failed'
                })
                if result:
                    print(f"  {GREEN}✓ {validation['description']}{RESET}")
                else:
                    print(f"  {RED}✗ {validation['description']}{RESET}")
                    all_steps_passed = False
            except Exception as e:
                print(f"  {RED}✗ {validation['description']}: {str(e)}{RESET}")
                validation_results.append({
                    'description': validation['description'],
                    'success': False,
                    'message': str(e)
                })
                all_steps_passed = False

        # Final result
        print(f"\n{BOLD}Result:{RESET}")
        if all_steps_passed:
            print(f"  {GREEN}✅ TEST PASSED{RESET}")
        else:
            print(f"  {RED}❌ TEST FAILED{RESET}")

        return {
            'test_name': test_case.name,
            'success': all_steps_passed,
            'steps': step_results,
            'validations': validation_results,
            'flow_data': flow_data
        }

    def _print_response_summary(self, body: Dict[str, Any], indent: str = "    "):
        """Print a concise summary of response"""
        for key, value in body.items():
            if isinstance(value, dict):
                if len(value) <= 3:
                    print(f"{indent}{key}: {json.dumps(value)}")
                else:
                    print(f"{indent}{key}: <dict with {len(value)} items>")
            elif isinstance(value, list):
                if len(value) <= 3:
                    print(f"{indent}{key}: {json.dumps(value)}")
                else:
                    print(f"{indent}{key}: <list with {len(value)} items>")
            else:
                print(f"{indent}{key}: {value}")

# =============================================================================
# TEST CASE DEFINITIONS
# =============================================================================

def create_complete_scheduling_flow() -> FlowTestCase:
    """
    Test Case 1: Complete Scheduling Flow

    User: "Schedule my flooring installation for October 15th at 10 AM"

    Flow:
    1. List projects (find the flooring project)
    2. Get available dates for that project
    3. Get time slots for October 15th
    4. Confirm appointment for 10 AM
    """
    test = FlowTestCase(
        "Complete Scheduling Flow",
        "Simulates a user scheduling their flooring installation through multiple Lambda calls"
    )

    # Step 1: List projects
    test.add_step(
        "Agent needs to find the customer's projects first",
        "scheduling-actions",
        "list-projects",
        [
            {"name": "customer_id", "value": "1645975"},
            {"name": "client_id", "value": "09PF05VD"}
        ],
        expected_fields=['projects', 'project_count', 'mock_mode']
    )

    # Step 2: Get available dates for flooring project
    test.add_step(
        "Agent finds flooring project (12345) and checks available dates",
        "scheduling-actions",
        "get-available-dates",
        [
            {"name": "project_id", "value": "12345"},
            {"name": "client_id", "value": "09PF05VD"}
        ],
        expected_fields=['available_dates', 'request_id', 'mock_mode']
    )

    # Step 3: Get time slots for October 15th
    test.add_step(
        "Agent checks available time slots for October 15th",
        "scheduling-actions",
        "get-time-slots",
        [
            {"name": "project_id", "value": "12345"},
            {"name": "date", "value": "2025-10-15"},
            {"name": "request_id", "value": "REQ-12345-test"},
            {"name": "client_id", "value": "09PF05VD"}
        ],
        expected_fields=['available_slots', 'mock_mode']
    )

    # Step 4: Confirm appointment at 10 AM
    test.add_step(
        "Agent confirms appointment for 10:00 AM",
        "scheduling-actions",
        "confirm-appointment",
        [
            {"name": "project_id", "value": "12345"},
            {"name": "date", "value": "2025-10-15"},
            {"name": "time", "value": "10:00 AM"},
            {"name": "request_id", "value": "REQ-12345-test"},
            {"name": "client_id", "value": "09PF05VD"}
        ],
        expected_fields=['confirmation_data', 'message', 'mock_mode']
    )

    # Validations
    test.add_validation(
        lambda data: len(data.get('list_projects', {}).get('projects', [])) > 0,
        "Projects were returned"
    )

    test.add_validation(
        lambda data: '12345' in [p.get('project_id') for p in data.get('list_projects', {}).get('projects', [])],
        "Flooring project (12345) was found in project list"
    )

    test.add_validation(
        lambda data: len(data.get('get_available_dates', {}).get('available_dates', [])) > 0,
        "Available dates were returned"
    )

    test.add_validation(
        lambda data: '2025-10-15' in data.get('get_available_dates', {}).get('available_dates', []),
        "October 15th is in available dates"
    )

    test.add_validation(
        lambda data: '10:00 AM' in data.get('get_time_slots', {}).get('available_slots', []),
        "10:00 AM is available"
    )

    test.add_validation(
        lambda data: 'confirmation_number' in data.get('confirm_appointment', {}).get('confirmation_data', {}),
        "Confirmation number was generated"
    )

    test.add_validation(
        lambda data: data.get('confirm_appointment', {}).get('scheduled_date') == '2025-10-15',
        "Scheduled date matches requested date"
    )

    test.add_validation(
        lambda data: data.get('confirm_appointment', {}).get('scheduled_time') == '10:00 AM',
        "Scheduled time matches requested time"
    )

    return test

def create_project_info_with_weather_flow() -> FlowTestCase:
    """
    Test Case 2: Project Information + Weather Check

    User: "What's the status of my flooring project and what's the weather for installation day?"

    Flow:
    1. List projects
    2. Get project details
    3. Get weather for installation location
    """
    test = FlowTestCase(
        "Project Information + Weather Flow",
        "User checks project details and weather forecast"
    )

    # Step 1: List projects
    test.add_step(
        "Agent lists projects to find flooring project",
        "scheduling-actions",
        "list-projects",
        [
            {"name": "customer_id", "value": "1645975"},
            {"name": "client_id", "value": "09PF05VD"}
        ],
        expected_fields=['projects']
    )

    # Step 2: Get project details
    test.add_step(
        "Agent gets detailed info for flooring project",
        "information-actions",
        "get-project-details",
        [
            {"name": "project_id", "value": "12345"},
            {"name": "customer_id", "value": "1645975"},
            {"name": "client_id", "value": "09PF05VD"}
        ],
        expected_fields=['project_details']
    )

    # Step 3: Get weather
    test.add_step(
        "Agent checks weather for Tampa, FL",
        "information-actions",
        "get-weather",
        [
            {"name": "location", "value": "Tampa, FL"},
            {"name": "client_id", "value": "09PF05VD"}
        ],
        expected_fields=['weather']
    )

    # Validations
    test.add_validation(
        lambda data: data.get('get_project_details', {}).get('project_details', {}).get('status') == 'Scheduled',
        "Project status is 'Scheduled'"
    )

    test.add_validation(
        lambda data: 'Tampa' in data.get('get_project_details', {}).get('project_details', {}).get('address', {}).get('city', ''),
        "Project location is Tampa"
    )

    test.add_validation(
        lambda data: 'current' in data.get('get_weather', {}).get('weather', {}),
        "Weather includes current conditions"
    )

    test.add_validation(
        lambda data: 'forecast' in data.get('get_weather', {}).get('weather', {}),
        "Weather includes forecast"
    )

    return test

def create_reschedule_flow() -> FlowTestCase:
    """
    Test Case 3: Reschedule Appointment

    User: "I need to reschedule my appointment from October 15th to October 20th at 2 PM"

    Flow:
    1. List projects (find project)
    2. Get available dates for new date
    3. Get time slots for October 20th
    4. Reschedule appointment (cancel old + confirm new)
    """
    test = FlowTestCase(
        "Reschedule Appointment Flow",
        "User reschedules an existing appointment to a new date and time"
    )

    # Step 1: List projects
    test.add_step(
        "Agent finds the project to reschedule",
        "scheduling-actions",
        "list-projects",
        [
            {"name": "customer_id", "value": "1645975"},
            {"name": "client_id", "value": "09PF05VD"}
        ]
    )

    # Step 2: Get available dates
    test.add_step(
        "Agent checks if October 20th is available",
        "scheduling-actions",
        "get-available-dates",
        [
            {"name": "project_id", "value": "12345"},
            {"name": "client_id", "value": "09PF05VD"}
        ]
    )

    # Step 3: Get time slots for Oct 20
    test.add_step(
        "Agent checks available times for October 20th",
        "scheduling-actions",
        "get-time-slots",
        [
            {"name": "project_id", "value": "12345"},
            {"name": "date", "value": "2025-10-20"},
            {"name": "request_id", "value": "REQ-12345-test"},
            {"name": "client_id", "value": "09PF05VD"}
        ]
    )

    # Step 4: Reschedule
    test.add_step(
        "Agent reschedules to October 20th at 2:00 PM",
        "scheduling-actions",
        "reschedule-appointment",
        [
            {"name": "project_id", "value": "12345"},
            {"name": "new_date", "value": "2025-10-20"},
            {"name": "new_time", "value": "02:00 PM"},
            {"name": "request_id", "value": "REQ-12345-test"},
            {"name": "client_id", "value": "09PF05VD"}
        ],
        expected_fields=['cancel_result', 'confirm_result', 'message']
    )

    # Validations
    test.add_validation(
        lambda data: data.get('reschedule_appointment', {}).get('new_date') == '2025-10-20',
        "New date is October 20th"
    )

    test.add_validation(
        lambda data: data.get('reschedule_appointment', {}).get('new_time') == '02:00 PM',
        "New time is 2:00 PM"
    )

    test.add_validation(
        lambda data: 'cancel_result' in data.get('reschedule_appointment', {}),
        "Old appointment was cancelled"
    )

    test.add_validation(
        lambda data: 'confirm_result' in data.get('reschedule_appointment', {}),
        "New appointment was confirmed"
    )

    return test

def create_notes_flow() -> FlowTestCase:
    """
    Test Case 4: Add and View Notes

    User: "Add a note that customer needs advance call, then show me all notes"

    Flow:
    1. Add note
    2. List notes
    """
    test = FlowTestCase(
        "Notes Management Flow",
        "User adds a note and then views all notes for a project"
    )

    # Step 1: Add note
    test.add_step(
        "Agent adds note to project",
        "notes-actions",
        "add-note",
        [
            {"name": "project_id", "value": "12345"},
            {"name": "note_text", "value": "Customer requests 30-minute advance call before technician arrival"},
            {"name": "author", "value": "Agent"},
            {"name": "client_id", "value": "09PF05VD"}
        ],
        expected_fields=['note_data', 'message']
    )

    # Step 2: List notes
    test.add_step(
        "Agent retrieves all notes for the project",
        "notes-actions",
        "list-notes",
        [
            {"name": "project_id", "value": "12345"},
            {"name": "client_id", "value": "09PF05VD"}
        ],
        expected_fields=['notes', 'total_count']
    )

    # Validations
    test.add_validation(
        lambda data: data.get('add_note', {}).get('note_data', {}).get('note_id') is not None,
        "Note ID was generated"
    )

    test.add_validation(
        lambda data: data.get('list_notes', {}).get('total_count', 0) > 0,
        "Notes were returned"
    )

    test.add_validation(
        lambda data: any(
            '30-minute' in note.get('note_text', '')
            for note in data.get('list_notes', {}).get('notes', [])
        ),
        "Added note appears in list"
    )

    return test

def create_business_hours_and_status_flow() -> FlowTestCase:
    """
    Test Case 5: Check Business Hours and Appointment Status

    User: "What are your hours and what's my appointment status?"

    Flow:
    1. Get working hours
    2. Get appointment status
    """
    test = FlowTestCase(
        "Business Hours + Appointment Status",
        "User checks business hours and appointment status"
    )

    # Step 1: Get working hours
    test.add_step(
        "Agent retrieves business hours",
        "information-actions",
        "get-working-hours",
        [
            {"name": "client_id", "value": "09PF05VD"}
        ],
        expected_fields=['business_hours']
    )

    # Step 2: Get appointment status
    test.add_step(
        "Agent checks appointment status",
        "information-actions",
        "get-appointment-status",
        [
            {"name": "project_id", "value": "12345"},
            {"name": "client_id", "value": "09PF05VD"}
        ],
        expected_fields=['appointment_status']
    )

    # Validations
    test.add_validation(
        lambda data: len(data.get('get_working_hours', {}).get('business_hours', [])) == 7,
        "All 7 days of week returned"
    )

    test.add_validation(
        lambda data: any(
            day.get('day') == 'Monday' and day.get('is_working') == True
            for day in data.get('get_working_hours', {}).get('business_hours', [])
        ),
        "Monday is a working day"
    )

    test.add_validation(
        lambda data: data.get('get_appointment_status', {}).get('appointment_status', {}).get('project_id') == '12345',
        "Status returned for correct project"
    )

    return test

def create_full_customer_journey() -> FlowTestCase:
    """
    Test Case 6: Complete Customer Journey

    Comprehensive flow covering multiple interactions
    """
    test = FlowTestCase(
        "Complete Customer Journey",
        "End-to-end customer interaction: list projects, get details, check weather, schedule, add note"
    )

    # Step 1: List projects
    test.add_step(
        "Customer asks to see their projects",
        "scheduling-actions",
        "list-projects",
        [
            {"name": "customer_id", "value": "1645975"},
            {"name": "client_id", "value": "09PF05VD"}
        ]
    )

    # Step 2: Get project details
    test.add_step(
        "Customer wants details on flooring project",
        "information-actions",
        "get-project-details",
        [
            {"name": "project_id", "value": "12345"},
            {"name": "customer_id", "value": "1645975"},
            {"name": "client_id", "value": "09PF05VD"}
        ]
    )

    # Step 3: Check weather
    test.add_step(
        "Customer checks weather for installation day",
        "information-actions",
        "get-weather",
        [
            {"name": "location", "value": "Tampa, FL"},
            {"name": "client_id", "value": "09PF05VD"}
        ]
    )

    # Step 4: Get available dates
    test.add_step(
        "Customer wants to schedule, agent checks dates",
        "scheduling-actions",
        "get-available-dates",
        [
            {"name": "project_id", "value": "12345"},
            {"name": "client_id", "value": "09PF05VD"}
        ]
    )

    # Step 5: Get time slots
    test.add_step(
        "Agent shows available times for chosen date",
        "scheduling-actions",
        "get-time-slots",
        [
            {"name": "project_id", "value": "12345"},
            {"name": "date", "value": "2025-10-15"},
            {"name": "request_id", "value": "REQ-12345-test"},
            {"name": "client_id", "value": "09PF05VD"}
        ]
    )

    # Step 6: Confirm appointment
    test.add_step(
        "Customer confirms time, agent schedules",
        "scheduling-actions",
        "confirm-appointment",
        [
            {"name": "project_id", "value": "12345"},
            {"name": "date", "value": "2025-10-15"},
            {"name": "time", "value": "10:00 AM"},
            {"name": "request_id", "value": "REQ-12345-test"},
            {"name": "client_id", "value": "09PF05VD"}
        ]
    )

    # Step 7: Add note
    test.add_step(
        "Agent adds note about customer preference",
        "notes-actions",
        "add-note",
        [
            {"name": "project_id", "value": "12345"},
            {"name": "note_text", "value": "Customer prefers morning appointments. Scheduled for 10 AM as requested."},
            {"name": "author", "value": "Agent"},
            {"name": "client_id", "value": "09PF05VD"}
        ]
    )

    # Comprehensive validations
    test.add_validation(
        lambda data: all(key in data for key in ['list_projects', 'get_project_details', 'get_weather',
                                                   'get_available_dates', 'get_time_slots',
                                                   'confirm_appointment', 'add_note']),
        "All 7 steps completed successfully"
    )

    test.add_validation(
        lambda data: all(data[key].get('mock_mode') == True for key in ['list_projects', 'get_available_dates',
                                                                          'get_time_slots', 'confirm_appointment']),
        "All responses indicate mock mode"
    )

    return test

# =============================================================================
# MAIN TEST EXECUTION
# =============================================================================

def main():
    print(f"""
{BOLD}╔════════════════════════════════════════════════════════════════════════════╗
║       Complete Flow Test Suite - Bedrock Agent + Lambda Integration       ║
║                     Simulating Multi-Step Conversations                    ║
╚════════════════════════════════════════════════════════════════════════════╝{RESET}
""")

    # Initialize test runner
    runner = FlowTestRunner()

    # Create test cases
    test_cases = [
        create_complete_scheduling_flow(),
        create_project_info_with_weather_flow(),
        create_reschedule_flow(),
        create_notes_flow(),
        create_business_hours_and_status_flow(),
        create_full_customer_journey()
    ]

    # Run all tests
    results = []
    for test_case in test_cases:
        result = runner.run_test(test_case)
        results.append(result)

    # Summary
    print(f"\n{BOLD}{'='*80}{RESET}")
    print(f"{BOLD}📊 TEST EXECUTION SUMMARY{RESET}")
    print(f"{BOLD}{'='*80}{RESET}\n")

    total_tests = len(results)
    passed_tests = sum(1 for r in results if r['success'])
    failed_tests = total_tests - passed_tests

    print(f"Total Test Cases: {total_tests}")
    print(f"{GREEN}✅ Passed: {passed_tests}{RESET}")
    print(f"{RED}❌ Failed: {failed_tests}{RESET}")
    print(f"Pass Rate: {(passed_tests/total_tests*100):.1f}%\n")

    # Detailed results
    print(f"{BOLD}Test Case Results:{RESET}")
    for i, result in enumerate(results, 1):
        status = f"{GREEN}✅ PASS{RESET}" if result['success'] else f"{RED}❌ FAIL{RESET}"
        print(f"  {i}. {result['test_name']}: {status}")
        if not result['success']:
            failed_steps = [s for s in result['steps'] if not s['success']]
            for step in failed_steps:
                print(f"     {RED}↳ Step {step['step']} failed: {step.get('error', 'Unknown')}{RESET}")

    # Invocation statistics
    print(f"\n{BOLD}Lambda Invocation Statistics:{RESET}")
    print(f"  Total Lambda Calls: {len(runner.invoker.invocation_log)}")

    by_lambda = {}
    for inv in runner.invoker.invocation_log:
        lambda_name = inv['lambda']
        by_lambda[lambda_name] = by_lambda.get(lambda_name, 0) + 1

    for lambda_name, count in sorted(by_lambda.items()):
        print(f"    {lambda_name}: {count} calls")

    # Final message
    print(f"\n{BOLD}{'='*80}{RESET}")
    if passed_tests == total_tests:
        print(f"{GREEN}{BOLD}🎉 All complete flow tests passed!{RESET}")
        print(f"{GREEN}Lambda functions are ready for Bedrock Agent integration.{RESET}")
    else:
        print(f"{RED}{BOLD}⚠️  {failed_tests} test case(s) failed.{RESET}")
        print(f"{RED}Please review the failures above.{RESET}")
    print(f"{BOLD}{'='*80}{RESET}\n")

    return passed_tests == total_tests

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    success = main()
    sys.exit(0 if success else 1)
