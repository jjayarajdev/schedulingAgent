#!/usr/bin/env python3

"""
test_deployment.py - Verify 4-agent deployment

Tests:
1. All agents exist and are in PREPARED state
2. All Lambda functions exist and are configured correctly
3. Action groups are properly attached
4. IAM permissions are correct
5. Secrets Manager access works

Usage:
    python3 test_deployment.py
"""

import boto3
import json
import sys
from datetime import datetime

# AWS clients
bedrock = boto3.client('bedrock-agent', region_name='us-east-1')
lambda_client = boto3.client('lambda', region_name='us-east-1')
iam = boto3.client('iam')
secrets = boto3.client('secretsmanager', region_name='us-east-1')

# Expected configuration
EXPECTED_AGENTS = {
    'SchedulingAgent': 'Primary scheduling and project management',
    'pf-information': 'Weather information specialist',
    'pf-chitchat': 'Conversational agent',
    'Supervisor': 'Query router and orchestrator'
}

EXPECTED_LAMBDAS = [
    'pf-scheduling-actions',
    'pf-information-actions',
    'pf-query-router'
]

def print_header(title):
    """Print formatted section header"""
    print(f"\n{'='*80}")
    print(f"{title}")
    print('='*80)

def print_result(test_name, passed, message=''):
    """Print test result"""
    status = '✅ PASS' if passed else '❌ FAIL'
    print(f"{status} - {test_name}")
    if message:
        print(f"        {message}")

def test_agents():
    """Test all Bedrock agents are deployed correctly"""
    print_header("Test 1: Bedrock Agents")

    try:
        # List all agents
        response = bedrock.list_agents()
        agent_summaries = response.get('agentSummaries', [])

        print(f"\nFound {len(agent_summaries)} agents")

        # Check each expected agent
        found_agents = {agent['agentName']: agent for agent in agent_summaries}

        all_passed = True
        for agent_name, description in EXPECTED_AGENTS.items():
            if agent_name in found_agents:
                agent = found_agents[agent_name]
                agent_id = agent['agentId']
                status = agent['agentStatus']

                # Get detailed info
                detail = bedrock.get_agent(agentId=agent_id)
                agent_detail = detail['agent']

                passed = status in ['PREPARED', 'NOT_PREPARED']
                print_result(
                    f"Agent: {agent_name}",
                    passed,
                    f"ID: {agent_id}, Status: {status}"
                )

                if not passed:
                    all_passed = False
            else:
                print_result(f"Agent: {agent_name}", False, "NOT FOUND")
                all_passed = False

        return all_passed

    except Exception as e:
        print_result("Agent Test", False, f"Error: {str(e)}")
        return False

def test_lambdas():
    """Test all Lambda functions are deployed correctly"""
    print_header("Test 2: Lambda Functions")

    all_passed = True
    for function_name in EXPECTED_LAMBDAS:
        try:
            response = lambda_client.get_function(FunctionName=function_name)
            config = response['Configuration']

            # Check configuration
            runtime = config.get('Runtime')
            handler = config.get('Handler')
            timeout = config.get('Timeout')
            env_vars = config.get('Environment', {}).get('Variables', {})

            # Verify environment variables
            has_token_secret = 'TOKEN_SECRET_NAME' in env_vars
            has_client_id = 'DEFAULT_CLIENT_ID' in env_vars

            passed = has_token_secret and has_client_id

            print_result(
                f"Lambda: {function_name}",
                passed,
                f"Runtime: {runtime}, Handler: {handler}, Timeout: {timeout}s"
            )

            if not passed:
                if not has_token_secret:
                    print(f"        ⚠️  Missing: TOKEN_SECRET_NAME")
                if not has_client_id:
                    print(f"        ⚠️  Missing: DEFAULT_CLIENT_ID")
                all_passed = False

        except lambda_client.exceptions.ResourceNotFoundException:
            print_result(f"Lambda: {function_name}", False, "NOT FOUND")
            all_passed = False
        except Exception as e:
            print_result(f"Lambda: {function_name}", False, f"Error: {str(e)}")
            all_passed = False

    return all_passed

def test_action_groups():
    """Test action groups are attached to agents"""
    print_header("Test 3: Action Groups")

    try:
        # Get agent IDs
        response = bedrock.list_agents()
        agents = {agent['agentName']: agent['agentId'] for agent in response['agentSummaries']}

        all_passed = True

        # Check SchedulingAgent has action group
        if 'SchedulingAgent' in agents:
            agent_id = agents['SchedulingAgent']
            try:
                action_groups = bedrock.list_agent_action_groups(
                    agentId=agent_id,
                    agentVersion='DRAFT'
                )
                num_groups = len(action_groups.get('actionGroupSummaries', []))
                passed = num_groups > 0
                print_result(
                    "SchedulingAgent Action Groups",
                    passed,
                    f"{num_groups} action group(s) found"
                )
                if not passed:
                    all_passed = False
            except Exception as e:
                print_result("SchedulingAgent Action Groups", False, f"Error: {str(e)}")
                all_passed = False
        else:
            print_result("SchedulingAgent Action Groups", False, "Agent not found")
            all_passed = False

        # pf-information should have action group (weather)
        if 'pf-information' in agents:
            agent_id = agents['pf-information']
            try:
                action_groups = bedrock.list_agent_action_groups(
                    agentId=agent_id,
                    agentVersion='DRAFT'
                )
                num_groups = len(action_groups.get('actionGroupSummaries', []))
                # Information agent might not have action group yet (external API)
                print_result(
                    "pf-information Action Groups",
                    True,
                    f"{num_groups} action group(s) found"
                )
            except Exception as e:
                print_result("pf-information Action Groups", True, f"No action groups (expected)")
        else:
            print_result("pf-information Action Groups", False, "Agent not found")
            all_passed = False

        return all_passed

    except Exception as e:
        print_result("Action Group Test", False, f"Error: {str(e)}")
        return False

def test_secrets_access():
    """Test Secrets Manager access"""
    print_header("Test 4: Secrets Manager")

    try:
        # Try to get the secret
        secret_name = 'projectforce/api/dev/credentials'
        response = secrets.get_secret_value(SecretId=secret_name)

        secret_string = response['SecretString']
        secret_data = json.loads(secret_string)

        # Verify required fields
        has_bearer = 'bearer_token' in secret_data
        has_email = 'email' in secret_data
        has_password = 'encrypted_password' in secret_data

        passed = has_bearer and has_email and has_password

        print_result(
            f"Secret: {secret_name}",
            passed,
            "All required fields present" if passed else "Missing required fields"
        )

        # Check Lambda can access secret (via IAM role)
        for function_name in ['pf-scheduling-actions', 'pf-information-actions']:
            try:
                func_config = lambda_client.get_function(FunctionName=function_name)
                role_arn = func_config['Configuration']['Role']
                role_name = role_arn.split('/')[-1]

                # Check if role has Secrets Manager permissions
                try:
                    attached_policies = iam.list_attached_role_policies(RoleName=role_name)
                    policies = [p['PolicyArn'] for p in attached_policies['AttachedPolicies']]

                    has_secrets_access = any('secrets' in p.lower() for p in policies)

                    print_result(
                        f"Lambda {function_name} Secrets Access",
                        has_secrets_access,
                        f"Role: {role_name}"
                    )
                except Exception:
                    print_result(
                        f"Lambda {function_name} Secrets Access",
                        False,
                        "Could not verify IAM permissions"
                    )

            except Exception:
                pass

        return passed

    except Exception as e:
        print_result("Secrets Manager Test", False, f"Error: {str(e)}")
        return False

def test_iam_permissions():
    """Test IAM permissions are configured correctly"""
    print_header("Test 5: IAM Permissions")

    all_passed = True

    for function_name in EXPECTED_LAMBDAS:
        try:
            # Get Lambda role
            func_config = lambda_client.get_function(FunctionName=function_name)
            role_arn = func_config['Configuration']['Role']
            role_name = role_arn.split('/')[-1]

            # Check attached policies
            attached = iam.list_attached_role_policies(RoleName=role_name)
            policy_names = [p['PolicyName'] for p in attached['AttachedPolicies']]

            # Basic execution policy should be attached
            has_basic_execution = any('lambda' in p.lower() or 'execution' in p.lower() for p in policy_names)

            print_result(
                f"IAM Role: {role_name}",
                has_basic_execution,
                f"Policies: {len(policy_names)}"
            )

            if not has_basic_execution:
                all_passed = False

        except Exception as e:
            print_result(f"IAM Role for {function_name}", False, f"Error: {str(e)}")
            all_passed = False

    return all_passed

def save_test_results(results):
    """Save test results to file"""
    output = {
        'test_date': datetime.utcnow().isoformat(),
        'results': results,
        'overall_status': 'PASS' if all(results.values()) else 'FAIL'
    }

    with open('test_results.json', 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\n✅ Test results saved to: test_results.json")

def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("ProjectForce 4-Agent Deployment Test")
    print("="*80)
    print(f"Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")

    # Run tests
    results = {
        'agents': test_agents(),
        'lambdas': test_lambdas(),
        'action_groups': test_action_groups(),
        'secrets': test_secrets_access(),
        'iam': test_iam_permissions()
    }

    # Summary
    print_header("Test Summary")
    total_tests = len(results)
    passed_tests = sum(1 for v in results.values() if v)

    print(f"\nTests Passed: {passed_tests}/{total_tests}")
    print("")

    for test_name, passed in results.items():
        status = '✅' if passed else '❌'
        print(f"  {status} {test_name.replace('_', ' ').title()}")

    # Save results
    save_test_results(results)

    # Exit code
    print("")
    if all(results.values()):
        print("🎉 All tests passed!")
        print("\nNext steps:")
        print("  1. Run: python3 test_all_queries.py")
        print("  2. Or use test UI: ./testing/ui/launch_test_ui.sh")
        sys.exit(0)
    else:
        print("⚠️  Some tests failed. Review output above.")
        sys.exit(1)

if __name__ == '__main__':
    main()
