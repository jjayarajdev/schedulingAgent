"""
Unit tests for validators module
Tests input validation functions
"""

import unittest
import sys
import os

# Add Lambda layer to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../lambda/shared-layer/python/lib"))

from validators import (
    validate_customer_id,
    validate_project_id,
    validate_date,
    validate_time,
    validate_session_id,
    validate_required_fields,
    extract_bedrock_parameters
)


class TestValidators(unittest.TestCase):
    """Test validation functions"""

    def test_validate_customer_id_valid(self):
        """Test valid customer ID"""
        result = validate_customer_id("CUST001")
        self.assertEqual(result, "CUST001")

        result = validate_customer_id("CUST-123-ABC")
        self.assertEqual(result, "CUST-123-ABC")

    def test_validate_customer_id_invalid(self):
        """Test invalid customer ID"""
        with self.assertRaises(ValueError):
            validate_customer_id("")

        with self.assertRaises(ValueError):
            validate_customer_id(None)

        with self.assertRaises(ValueError):
            validate_customer_id("cust@123")  # Invalid characters

    def test_validate_project_id_valid(self):
        """Test valid project ID"""
        result = validate_project_id("12345")
        self.assertEqual(result, "12345")

        result = validate_project_id("PRJ-001")
        self.assertEqual(result, "PRJ-001")

    def test_validate_project_id_invalid(self):
        """Test invalid project ID"""
        with self.assertRaises(ValueError):
            validate_project_id("")

        with self.assertRaises(ValueError):
            validate_project_id(None)

    def test_validate_date_valid(self):
        """Test valid date format"""
        result = validate_date("2025-10-20")
        self.assertEqual(result, "2025-10-20")

        result = validate_date("2025-01-01")
        self.assertEqual(result, "2025-01-01")

    def test_validate_date_invalid(self):
        """Test invalid date format"""
        with self.assertRaises(ValueError):
            validate_date("10-20-2025")  # Wrong format

        with self.assertRaises(ValueError):
            validate_date("2025-13-01")  # Invalid month

        with self.assertRaises(ValueError):
            validate_date("2025-02-30")  # Invalid day

        with self.assertRaises(ValueError):
            validate_date("not-a-date")

    def test_validate_time_valid(self):
        """Test valid time format"""
        result = validate_time("09:00")
        self.assertEqual(result, "09:00")

        result = validate_time("23:59")
        self.assertEqual(result, "23:59")

    def test_validate_time_invalid(self):
        """Test invalid time format"""
        with self.assertRaises(ValueError):
            validate_time("9:00")  # Should be 09:00

        with self.assertRaises(ValueError):
            validate_time("25:00")  # Invalid hour

        with self.assertRaises(ValueError):
            validate_time("12:60")  # Invalid minute

        with self.assertRaises(ValueError):
            validate_time("not-a-time")

    def test_validate_session_id_valid(self):
        """Test valid session ID"""
        result = validate_session_id("session-123-abc")
        self.assertEqual(result, "session-123-abc")

    def test_validate_session_id_invalid(self):
        """Test invalid session ID"""
        with self.assertRaises(ValueError):
            validate_session_id("")

        with self.assertRaises(ValueError):
            validate_session_id(None)

    def test_validate_required_fields(self):
        """Test required fields validation"""
        data = {"field1": "value1", "field2": "value2"}

        # Should not raise
        validate_required_fields(data, ["field1", "field2"])

        # Should raise
        with self.assertRaises(ValueError) as cm:
            validate_required_fields(data, ["field1", "field3"])

        self.assertIn("Missing required fields", str(cm.exception))
        self.assertIn("field3", str(cm.exception))

    def test_extract_bedrock_parameters(self):
        """Test parameter extraction from Bedrock event"""
        event = {
            "requestBody": {
                "content": {
                    "application/json": {
                        "properties": [
                            {"name": "customer_id", "value": "CUST001"},
                            {"name": "project_id", "value": "12345"}
                        ]
                    }
                }
            }
        }

        params = extract_bedrock_parameters(event)

        self.assertEqual(params["customer_id"], "CUST001")
        self.assertEqual(params["project_id"], "12345")


if __name__ == "__main__":
    unittest.main()
