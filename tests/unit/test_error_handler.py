"""
Unit tests for error_handler module
Tests error handling utilities
"""

import unittest
import sys
import os

# Add Lambda layer to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../lambda/shared-layer/python/lib"))

from error_handler import (
    format_error_response,
    format_success_response,
    classify_error,
    format_bedrock_response
)


class TestErrorHandler(unittest.TestCase):
    """Test error handling functions"""

    def test_format_error_response(self):
        """Test error response formatting"""
        response = format_error_response(
            error_message="Test error",
            error_type="ValidationError",
            status_code=400
        )

        self.assertEqual(response["statusCode"], 400)
        self.assertIn("error", response["body"])
        self.assertEqual(response["body"]["error"]["type"], "ValidationError")
        self.assertEqual(response["body"]["error"]["message"], "Test error")

    def test_format_success_response(self):
        """Test success response formatting"""
        data = {"result": "success", "id": "123"}
        response = format_success_response(data, message="Operation completed")

        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(response["body"]["message"], "Operation completed")
        self.assertEqual(response["body"]["data"], data)

    def test_classify_error_timeout(self):
        """Test timeout error classification"""
        error = Exception("Request timed out after 30s")
        error_type, status_code = classify_error(error)

        self.assertEqual(error_type, "TimeoutError")
        self.assertEqual(status_code, 504)

    def test_classify_error_rate_limit(self):
        """Test rate limit error classification"""
        error = Exception("Rate limit exceeded")
        error_type, status_code = classify_error(error)

        self.assertEqual(error_type, "RateLimitError")
        self.assertEqual(status_code, 429)

    def test_classify_error_authentication(self):
        """Test authentication error classification"""
        error = Exception("401 Unauthorized")
        error_type, status_code = classify_error(error)

        self.assertEqual(error_type, "AuthenticationError")
        self.assertEqual(status_code, 401)

    def test_classify_error_not_found(self):
        """Test not found error classification"""
        error = Exception("Resource not found")
        error_type, status_code = classify_error(error)

        self.assertEqual(error_type, "NotFoundError")
        self.assertEqual(status_code, 404)

    def test_classify_error_validation(self):
        """Test validation error classification"""
        error = Exception("Invalid input parameter")
        error_type, status_code = classify_error(error)

        self.assertEqual(error_type, "ValidationError")
        self.assertEqual(status_code, 400)

    def test_classify_error_default(self):
        """Test default error classification"""
        error = Exception("Something went wrong")
        error_type, status_code = classify_error(error)

        self.assertEqual(error_type, "InternalError")
        self.assertEqual(status_code, 500)

    def test_format_bedrock_response(self):
        """Test Bedrock Agent response formatting"""
        response_body = {"result": "success", "data": {"id": "123"}}

        response = format_bedrock_response(
            action_group="scheduling",
            api_path="/list-projects",
            http_method="POST",
            response_body=response_body,
            http_status_code=200
        )

        self.assertEqual(response["messageVersion"], "1.0")
        self.assertEqual(response["response"]["actionGroup"], "scheduling")
        self.assertEqual(response["response"]["apiPath"], "/list-projects")
        self.assertEqual(response["response"]["httpMethod"], "POST")
        self.assertEqual(response["response"]["httpStatusCode"], 200)
        self.assertIn("responseBody", response["response"])
        self.assertIn("application/json", response["response"]["responseBody"])


if __name__ == "__main__":
    unittest.main()
