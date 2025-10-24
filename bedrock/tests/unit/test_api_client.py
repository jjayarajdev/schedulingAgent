"""
Unit tests for API client (mock mode)
Tests PF360APIClient in mock mode
"""

import unittest
import sys
import os

# Set mock mode
os.environ["USE_MOCK_API"] = "true"

# Add Lambda layer and lambda function paths to sys.path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../lambda/shared-layer/python/lib"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../lambda/scheduling-actions"))

from api_client import PF360APIClient


class TestAPIClientMockMode(unittest.TestCase):
    """Test API client in mock mode"""

    def setUp(self):
        """Set up test client"""
        self.session_data = {
            "customer_id": "CUST001",
            "client_id": "CLIENT001",
            "client_name": "testclient",
            "auth_token": "test-token"
        }
        self.client = PF360APIClient(self.session_data)

    def test_initialization(self):
        """Test client initialization"""
        self.assertEqual(self.client.customer_id, "CUST001")
        self.assertEqual(self.client.client_id, "CLIENT001")
        self.assertEqual(self.client.use_mock, True)

    def test_get_projects(self):
        """Test getting projects in mock mode"""
        result = self.client.get_projects()

        self.assertIn("data", result)
        self.assertIsInstance(result["data"], list)
        self.assertGreater(len(result["data"]), 0)

        # Check project structure
        project = result["data"][0]
        self.assertIn("project_project_id", project)
        self.assertIn("project_project_number", project)
        self.assertIn("status_info_status", project)

    def test_get_available_dates(self):
        """Test getting available dates in mock mode"""
        result = self.client.get_available_dates("12345")

        self.assertIn("data", result)
        data = result["data"]

        self.assertIn("dates", data)
        self.assertIn("request_id", data)
        self.assertIsInstance(data["dates"], list)
        self.assertGreater(len(data["dates"]), 0)

        # Check that request_id was stored
        self.assertEqual(self.client.request_id, data["request_id"])

    def test_get_time_slots(self):
        """Test getting time slots in mock mode"""
        # First get available dates to generate request_id
        self.client.get_available_dates("12345")

        # Then get time slots
        result = self.client.get_time_slots("12345", "2025-10-21")

        self.assertIn("data", result)
        data = result["data"]

        self.assertIn("slots", data)
        self.assertIsInstance(data["slots"], list)

    def test_confirm_appointment(self):
        """Test confirming appointment in mock mode"""
        # Get request_id first
        self.client.get_available_dates("12345")

        # Confirm appointment
        result = self.client.confirm_appointment("12345", "2025-10-21", "09:00")

        self.assertIn("status", result)
        self.assertEqual(result["status"], "success")
        self.assertIn("message", result)

    def test_cancel_appointment(self):
        """Test cancelling appointment in mock mode"""
        result = self.client.cancel_appointment("12345")

        self.assertIn("status", result)
        self.assertEqual(result["status"], "success")
        self.assertIn("message", result)

    def test_get_business_hours(self):
        """Test getting business hours in mock mode"""
        result = self.client.get_business_hours()

        self.assertIn("data", result)
        data = result["data"]

        self.assertIn("business_hours", data)
        self.assertIsInstance(data["business_hours"], list)

    def test_add_note(self):
        """Test adding note in mock mode"""
        result = self.client.add_note("12345", "Test note")

        self.assertIn("status", result)
        self.assertEqual(result["status"], "success")
        self.assertIn("message", result)

    def test_get_weather(self):
        """Test getting weather in mock mode"""
        result = self.client.get_weather("Tampa")

        self.assertIn("location", result)
        self.assertIn("temperature", result)
        self.assertIn("condition", result)


if __name__ == "__main__":
    unittest.main()
