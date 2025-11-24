"""
Integration tests for full scheduling workflow
Tests multi-step scheduling flow with session management
"""

import unittest
import sys
import os
import uuid

# Set mock mode
os.environ["USE_MOCK_API"] = "true"

# Add paths for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../lambda/shared-layer/python/lib"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../lambda/scheduling-actions"))

from api_client import PF360APIClient


class TestSchedulingFlow(unittest.TestCase):
    """Test complete scheduling workflow"""

    def setUp(self):
        """Set up test client and session data"""
        self.session_data = {
            "customer_id": "CUST001",
            "client_id": "CLIENT001",
            "client_name": "testclient",
            "auth_token": "test-token",
            "request_id": None
        }
        self.client = PF360APIClient(self.session_data)

    def test_complete_scheduling_workflow(self):
        """
        Test complete scheduling workflow:
        1. List projects
        2. Get available dates (stores request_id)
        3. Get time slots (uses request_id)
        4. Confirm appointment (uses request_id)
        """
        # Step 1: List projects
        print("\n--- Step 1: List Projects ---")
        projects_response = self.client.get_projects()

        self.assertIn("data", projects_response)
        self.assertGreater(len(projects_response["data"]), 0)

        project_id = projects_response["data"][0]["project_project_id"]
        print(f"Selected project: {project_id}")

        # Step 2: Get available dates (this stores request_id)
        print("\n--- Step 2: Get Available Dates ---")
        dates_response = self.client.get_available_dates(project_id)

        self.assertIn("data", dates_response)
        data = dates_response["data"]

        self.assertIn("dates", data)
        self.assertIn("request_id", data)
        self.assertGreater(len(data["dates"]), 0)

        # Verify request_id was stored in client
        self.assertIsNotNone(self.client.request_id)
        request_id = self.client.request_id
        print(f"Request ID: {request_id}")

        selected_date = data["dates"][0]
        print(f"Selected date: {selected_date}")

        # Step 3: Get time slots (uses stored request_id)
        print("\n--- Step 3: Get Time Slots ---")
        slots_response = self.client.get_time_slots(project_id, selected_date)

        self.assertIn("data", slots_response)
        slots_data = slots_response["data"]

        self.assertIn("slots", slots_data)
        self.assertGreater(len(slots_data["slots"]), 0)

        selected_time = slots_data["slots"][0]
        print(f"Selected time: {selected_time}")

        # Step 4: Confirm appointment (uses stored request_id)
        print("\n--- Step 4: Confirm Appointment ---")
        confirm_response = self.client.confirm_appointment(
            project_id,
            selected_date,
            selected_time
        )

        self.assertIn("status", confirm_response)
        self.assertEqual(confirm_response["status"], "success")
        self.assertIn("message", confirm_response)

        print(f"Confirmation: {confirm_response['message']}")
        print("\n✅ Complete scheduling workflow successful!")

    def test_reschedule_workflow(self):
        """
        Test rescheduling workflow:
        1. Get available dates
        2. Get time slots
        3. Confirm first appointment
        4. Get new dates
        5. Cancel old appointment
        6. Confirm new appointment
        """
        project_id = "12345"

        # Initial scheduling
        print("\n--- Initial Scheduling ---")
        dates_response = self.client.get_available_dates(project_id)
        date1 = dates_response["data"]["dates"][0]

        slots_response = self.client.get_time_slots(project_id, date1)
        time1 = slots_response["data"]["slots"][0]

        confirm1 = self.client.confirm_appointment(project_id, date1, time1)
        self.assertEqual(confirm1["status"], "success")
        print(f"Initial appointment: {date1} at {time1}")

        # Rescheduling
        print("\n--- Rescheduling ---")
        dates_response2 = self.client.get_available_dates(project_id)
        date2 = dates_response2["data"]["dates"][1]  # Pick different date

        slots_response2 = self.client.get_time_slots(project_id, date2)
        time2 = slots_response2["data"]["slots"][1]  # Pick different time

        # Cancel old
        cancel_response = self.client.cancel_appointment(project_id)
        self.assertEqual(cancel_response["status"], "success")

        # Confirm new
        confirm2 = self.client.confirm_appointment(project_id, date2, time2)
        self.assertEqual(confirm2["status"], "success")
        print(f"Rescheduled to: {date2} at {time2}")

        print("\n✅ Reschedule workflow successful!")

    def test_cancel_workflow(self):
        """
        Test cancellation workflow:
        1. Get available dates
        2. Confirm appointment
        3. Cancel appointment
        """
        project_id = "12345"

        # Schedule appointment
        print("\n--- Scheduling Appointment ---")
        dates_response = self.client.get_available_dates(project_id)
        date = dates_response["data"]["dates"][0]

        slots_response = self.client.get_time_slots(project_id, date)
        time = slots_response["data"]["slots"][0]

        confirm_response = self.client.confirm_appointment(project_id, date, time)
        self.assertEqual(confirm_response["status"], "success")
        print(f"Scheduled: {date} at {time}")

        # Cancel appointment
        print("\n--- Cancelling Appointment ---")
        cancel_response = self.client.cancel_appointment(project_id)

        self.assertEqual(cancel_response["status"], "success")
        self.assertIn("message", cancel_response)
        print(f"Cancellation: {cancel_response['message']}")

        print("\n✅ Cancel workflow successful!")

    def test_error_missing_request_id(self):
        """Test error when request_id is missing for time slots"""
        project_id = "12345"

        # Try to get time slots without calling get_available_dates first
        print("\n--- Testing Missing Request ID Error ---")

        with self.assertRaises(ValueError) as cm:
            self.client.get_time_slots(project_id, "2025-10-21")

        self.assertIn("request_id is required", str(cm.exception))
        print(f"Expected error: {cm.exception}")

        print("\n✅ Error handling works correctly!")


class TestMultipleProjects(unittest.TestCase):
    """Test handling multiple projects"""

    def setUp(self):
        """Set up test client"""
        self.session_data = {
            "customer_id": "CUST001",
            "client_id": "CLIENT001",
            "client_name": "testclient"
        }
        self.client = PF360APIClient(self.session_data)

    def test_schedule_multiple_projects(self):
        """Test scheduling appointments for multiple projects"""
        print("\n--- Testing Multiple Project Scheduling ---")

        # Get all projects
        projects_response = self.client.get_projects()
        projects = projects_response["data"]

        self.assertGreaterEqual(len(projects), 2)

        scheduled = []

        # Schedule first 2 projects
        for i, project in enumerate(projects[:2]):
            project_id = project["project_project_id"]

            print(f"\nScheduling project {i+1}: {project_id}")

            # Get dates and slots
            dates_response = self.client.get_available_dates(project_id)
            date = dates_response["data"]["dates"][0]

            slots_response = self.client.get_time_slots(project_id, date)
            time = slots_response["data"]["slots"][0]

            # Confirm
            confirm_response = self.client.confirm_appointment(project_id, date, time)
            self.assertEqual(confirm_response["status"], "success")

            scheduled.append({
                "project_id": project_id,
                "date": date,
                "time": time
            })

            print(f"✓ Scheduled: {date} at {time}")

        self.assertEqual(len(scheduled), 2)
        print(f"\n✅ Successfully scheduled {len(scheduled)} projects!")


if __name__ == "__main__":
    # Run tests with verbose output
    unittest.main(verbosity=2)
