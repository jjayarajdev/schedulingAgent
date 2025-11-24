"""
Unit tests for Lex Fulfillment Lambda

Tests all intent handlers and response formatting.
"""

import pytest
import json
import sys
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Mock AWS SDK before importing handler
sys.path.insert(0, '../../lambda/layers/common/python')
sys.path.insert(0, '../../lambda/lex-fulfillment')

@pytest.fixture
def lambda_context():
    """Mock Lambda context"""
    context = Mock()
    context.request_id = 'test-request-123'
    context.function_name = 'pf-lex-fulfillment-dev'
    context.memory_limit_in_mb = 512
    return context


@pytest.fixture
def welcome_event():
    """Sample Welcome intent event"""
    return {
        "sessionId": "test-session-123",
        "inputTranscript": "hello",
        "sessionState": {
            "sessionAttributes": {
                "customer_id": "CUST123"
            },
            "intent": {
                "name": "Welcome",
                "slots": {},
                "state": "InProgress"
            }
        },
        "requestAttributes": {
            "CustomerNumber": "+18005551234"
        }
    }


@pytest.fixture
def project_inquiry_event():
    """Sample ProjectInquiry intent event"""
    return {
        "sessionId": "test-session-456",
        "inputTranscript": "show me my projects",
        "sessionState": {
            "sessionAttributes": {
                "customer_id": "CUST456"
            },
            "intent": {
                "name": "ProjectInquiry",
                "slots": {},
                "state": "InProgress"
            }
        },
        "requestAttributes": {}
    }


@pytest.fixture
def check_availability_event():
    """Sample CheckAvailability intent event"""
    return {
        "sessionId": "test-session-789",
        "inputTranscript": "check availability for project 123",
        "sessionState": {
            "sessionAttributes": {
                "customer_id": "CUST789"
            },
            "intent": {
                "name": "CheckAvailability",
                "slots": {
                    "ProjectId": {
                        "value": {
                            "interpretedValue": "123"
                        }
                    }
                },
                "state": "InProgress"
            }
        },
        "requestAttributes": {}
    }


class TestLexFulfillment:
    """Test suite for Lex Fulfillment Lambda"""

    @patch('handler.lambda_client')
    @patch('handler.table')
    def test_welcome_intent_with_customer_id(self, mock_table, mock_lambda, welcome_event, lambda_context):
        """Test Welcome intent when customer ID is provided"""
        from handler import lambda_handler

        response = lambda_handler(welcome_event, lambda_context)

        assert response['sessionState']['dialogAction']['type'] == 'ElicitIntent'
        assert 'ProjectForce' in response['messages'][0]['content']
        assert 'AI scheduling assistant' in response['messages'][0]['content']

    @patch('handler.lambda_client')
    @patch('handler.table')
    def test_welcome_intent_without_customer_id(self, mock_table, mock_lambda, welcome_event, lambda_context):
        """Test Welcome intent when customer ID is NOT provided"""
        from handler import lambda_handler

        # Remove customer_id
        welcome_event['sessionState']['sessionAttributes'] = {}

        response = lambda_handler(welcome_event, lambda_context)

        assert 'customer ID' in response['messages'][0]['content']

    @patch('handler.lambda_client')
    @patch('handler.table')
    def test_project_inquiry_success(self, mock_table, mock_lambda, project_inquiry_event, lambda_context):
        """Test ProjectInquiry with successful response"""
        from handler import lambda_handler

        # Mock Lambda response
        mock_payload = {
            'statusCode': 200,
            'response': {
                'projects': [
                    {
                        'id': 'PRJ-001',
                        'project_id': 'PRJ-001',
                        'category': 'Roofing',
                        'status': 'Scheduled'
                    },
                    {
                        'id': 'PRJ-002',
                        'project_id': 'PRJ-002',
                        'category': 'Painting',
                        'status': 'In Progress'
                    }
                ]
            }
        }

        mock_response = Mock()
        mock_response.read.return_value = json.dumps(mock_payload).encode()
        mock_lambda.invoke.return_value = {'Payload': mock_response}

        response = lambda_handler(project_inquiry_event, lambda_context)

        assert response['sessionState']['dialogAction']['type'] == 'ElicitIntent'
        assert 'projects' in response['messages'][0]['content'].lower()
        assert 'PRJ-001' in response['messages'][0]['content'] or 'Roofing' in response['messages'][0]['content']

    @patch('handler.lambda_client')
    @patch('handler.table')
    def test_project_inquiry_no_customer_id(self, mock_table, mock_lambda, project_inquiry_event, lambda_context):
        """Test ProjectInquiry without customer ID"""
        from handler import lambda_handler

        # Remove customer_id
        project_inquiry_event['sessionState']['sessionAttributes'] = {}

        response = lambda_handler(project_inquiry_event, lambda_context)

        assert 'customer ID' in response['messages'][0]['content']

    @patch('handler.lambda_client')
    @patch('handler.table')
    def test_check_availability_success(self, mock_table, mock_lambda, check_availability_event, lambda_context):
        """Test CheckAvailability with successful response"""
        from handler import lambda_handler

        # Mock Lambda response
        mock_payload = {
            'statusCode': 200,
            'response': {
                'available_dates': [
                    {'date': '2025-11-20', 'day_name': 'Wednesday'},
                    {'date': '2025-11-21', 'day_name': 'Thursday'},
                    {'date': '2025-11-22', 'day_name': 'Friday'}
                ]
            }
        }

        mock_response = Mock()
        mock_response.read.return_value = json.dumps(mock_payload).encode()
        mock_lambda.invoke.return_value = {'Payload': mock_response}

        response = lambda_handler(check_availability_event, lambda_context)

        assert response['sessionState']['dialogAction']['type'] == 'ElicitIntent'
        assert 'available' in response['messages'][0]['content'].lower()

    @patch('handler.lambda_client')
    @patch('handler.table')
    def test_handoff_to_bedrock(self, mock_table, mock_lambda, lambda_context):
        """Test handoff to Bedrock for complex intents"""
        from handler import lambda_handler

        event = {
            "sessionId": "test-session-999",
            "inputTranscript": "schedule an appointment for next Tuesday at 2pm",
            "sessionState": {
                "sessionAttributes": {"customer_id": "CUST999"},
                "intent": {
                    "name": "ScheduleAppointment",
                    "slots": {},
                    "state": "InProgress"
                }
            },
            "requestAttributes": {}
        }

        # Mock Bedrock bridge response
        mock_payload = {
            'statusCode': 200,
            'response': "I'll help you schedule that appointment. Let me check available time slots."
        }

        mock_response = Mock()
        mock_response.read.return_value = json.dumps(mock_payload).encode()
        mock_lambda.invoke.return_value = {'Payload': mock_response}

        response = lambda_handler(event, lambda_context)

        assert response['sessionState']['dialogAction']['type'] == 'ElicitIntent'
        assert mock_lambda.invoke.called
        # Verify we called voice-bridge Lambda
        call_args = mock_lambda.invoke.call_args
        assert 'pf-voice-bedrock-bridge-dev' in call_args.kwargs['FunctionName']

    def test_format_projects_for_voice_single_project(self):
        """Test voice formatting for single project"""
        from handler import _format_projects_for_voice

        response = {
            'projects': [
                {
                    'id': 'PRJ-001',
                    'project_id': 'PRJ-001',
                    'category': 'Roofing',
                    'status': 'Scheduled'
                }
            ]
        }

        result = _format_projects_for_voice(response)

        assert '1 project' in result
        assert 'Roofing' in result
        assert 'PRJ-001' in result
        assert 'schedule' in result.lower()

    def test_format_projects_for_voice_multiple_projects(self):
        """Test voice formatting for multiple projects"""
        from handler import _format_projects_for_voice

        response = {
            'projects': [
                {'id': f'PRJ-{i:03d}', 'project_id': f'PRJ-{i:03d}', 'category': 'Test', 'status': 'Active'}
                for i in range(10)
            ]
        }

        result = _format_projects_for_voice(response)

        assert '10 projects' in result
        assert 'first 5' in result  # Should limit to 5 for voice
        assert '5 more' in result

    def test_format_availability_for_voice(self):
        """Test voice formatting for availability"""
        from handler import _format_availability_for_voice

        response = {
            'available_dates': [
                {'date': '2025-11-20', 'day_name': 'Wednesday'},
                {'date': '2025-11-21', 'day_name': 'Thursday'}
            ]
        }

        result = _format_availability_for_voice(response)

        assert 'available dates' in result.lower()
        assert 'Wednesday' in result
        assert 'Thursday' in result

    def test_mask_phone(self):
        """Test phone number masking for PII protection"""
        from handler import _mask_phone

        assert _mask_phone('+18005551234') == '********1234'
        assert _mask_phone('123') == '***'
        assert _mask_phone('unknown') == 'unknown'


@pytest.mark.integration
class TestLexFulfillmentIntegration:
    """Integration tests (require AWS credentials)"""

    @pytest.mark.skip(reason="Requires AWS credentials and deployed resources")
    def test_end_to_end_project_inquiry(self):
        """End-to-end test with real AWS services"""
        pass


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--cov=handler', '--cov-report=html'])
