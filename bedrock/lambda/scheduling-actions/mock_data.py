"""
Mock API responses for Scheduling Actions
Based on real API responses from core/tools.py analysis
"""
from datetime import datetime, timedelta
from typing import Dict, List, Any

def get_mock_projects(customer_id: str) -> Dict[str, Any]:
    """
    Mock response for Dashboard API
    GET /dashboard/get/{client_id}/{customer_id}
    """
    return {
        "status": "success",
        "data": [
            {
                "project_project_id": "12345",
                "project_project_number": "ORD-2025-001",
                "project_type_project_type": "Installation",
                "project_category_category": "Flooring",
                "status_info_status": "Scheduled",
                "project_store_store_number": "ST-101",
                "installation_address_full_address": "123 Main St, Tampa, FL 33601",
                "installation_address_address1": "123 Main St",
                "installation_address_address2": "Apt 4B",
                "installation_address_city": "Tampa",
                "installation_address_state": "FL",
                "installation_address_zipcode": "33601",
                "project_date_sold": "2025-10-01",
                "project_date_scheduled_date": "2025-10-15",
                "convertedProjectStartScheduledDate": "2025-10-15 08:00:00",
                "convertedProjectEndScheduledDate": "2025-10-15 12:00:00",
                "project_date_completed_date": None,
                "user_idata_user_id": "1001",
                "user_idata_first_name": "John",
                "user_idata_last_name": "Smith",
                "service_time_duration_value": "4",
                "service_time_duration_type": "hours"
            },
            {
                "project_project_id": "12347",
                "project_project_number": "ORD-2025-002",
                "project_type_project_type": "Installation",
                "project_category_category": "Windows",
                "status_info_status": "Pending",
                "project_store_store_number": "ST-102",
                "installation_address_full_address": "456 Oak Ave, Tampa, FL 33602",
                "installation_address_address1": "456 Oak Ave",
                "installation_address_address2": "",
                "installation_address_city": "Tampa",
                "installation_address_state": "FL",
                "installation_address_zipcode": "33602",
                "project_date_sold": "2025-10-05",
                "project_date_scheduled_date": None,
                "convertedProjectStartScheduledDate": None,
                "convertedProjectEndScheduledDate": None,
                "project_date_completed_date": None,
                "user_idata_user_id": "1002",
                "user_idata_first_name": "Jane",
                "user_idata_last_name": "Doe",
                "service_time_duration_value": "3",
                "service_time_duration_type": "hours"
            },
            {
                "project_project_id": "12350",
                "project_project_number": "ORD-2025-003",
                "project_type_project_type": "Repair",
                "project_category_category": "Deck Repair",
                "status_info_status": "Pending",
                "project_store_store_number": "ST-103",
                "installation_address_full_address": "789 Pine Dr, Clearwater, FL 33755",
                "installation_address_address1": "789 Pine Dr",
                "installation_address_address2": "",
                "installation_address_city": "Clearwater",
                "installation_address_state": "FL",
                "installation_address_zipcode": "33755",
                "project_date_sold": "2025-10-08",
                "project_date_scheduled_date": None,
                "convertedProjectStartScheduledDate": None,
                "convertedProjectEndScheduledDate": None,
                "project_date_completed_date": None,
                "user_idata_user_id": "1003",
                "user_idata_first_name": "Mike",
                "user_idata_last_name": "Johnson",
                "service_time_duration_value": "2",
                "service_time_duration_type": "hours"
            }
        ]
    }

def get_mock_available_dates(project_id: str) -> Dict[str, Any]:
    """
    Mock response for Available Dates API
    GET /scheduler/.../get-rescheduler-slots
    """
    today = datetime.now()
    dates = [(today + timedelta(days=i)).strftime("%Y-%m-%d")
             for i in range(1, 15)
             if (today + timedelta(days=i)).weekday() < 5]  # Weekdays only

    return {
        "status": "success",
        "data": {
            "dates": dates,
            "request_id": f"REQ-{project_id}-{int(datetime.now().timestamp())}"
        }
    }

def get_mock_time_slots(project_id: str, date: str, request_id: str) -> Dict[str, Any]:
    """
    Mock response for Time Slots API
    GET /scheduler/.../get-rescheduler-slots?request_id=...
    """
    # Generate time slots from 8 AM to 5 PM
    slots = [
        "08:00 AM", "09:00 AM", "10:00 AM", "11:00 AM",
        "01:00 PM", "02:00 PM", "03:00 PM", "04:00 PM", "05:00 PM"
    ]

    return {
        "status": "success",
        "data": {
            "slots": slots,
            "date": date,
            "project_id": project_id,
            "request_id": request_id
        }
    }

def get_mock_confirm_appointment(project_id: str, date: str, time: str, request_id: str) -> Dict[str, Any]:
    """
    Mock response for Confirm Appointment API
    POST /scheduler/.../schedule
    """
    return {
        "status": "success",
        "message": f"✅ [MOCK] Appointment scheduled successfully for project {project_id} on {date} at {time}",
        "data": {
            "project_id": project_id,
            "scheduled_date": date,
            "scheduled_time": time,
            "request_id": request_id,
            "confirmation_number": f"CONF-{int(datetime.now().timestamp())}"
        }
    }

def get_mock_cancel_appointment(project_id: str) -> Dict[str, Any]:
    """
    Mock response for Cancel Appointment API
    GET /scheduler/.../cancel-reschedule
    """
    return {
        "status": "success",
        "message": f"✅ [MOCK] Appointment cancelled successfully for project {project_id}",
        "data": {
            "project_id": project_id,
            "cancelled_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "cancellation_id": f"CANC-{int(datetime.now().timestamp())}"
        }
    }

def get_mock_business_hours(client_id: str) -> Dict[str, Any]:
    """
    Mock response for Business Hours API
    GET /scheduler/.../business-hours
    """
    return {
        "status": "success",
        "data": {
            "workHours": [
                {"day": "Monday", "is_working": True, "start": "08:00", "end": "17:00"},
                {"day": "Tuesday", "is_working": True, "start": "08:00", "end": "17:00"},
                {"day": "Wednesday", "is_working": True, "start": "08:00", "end": "17:00"},
                {"day": "Thursday", "is_working": True, "start": "08:00", "end": "17:00"},
                {"day": "Friday", "is_working": True, "start": "08:00", "end": "17:00"},
                {"day": "Saturday", "is_working": False, "start": None, "end": None},
                {"day": "Sunday", "is_working": False, "start": None, "end": None}
            ]
        }
    }

# Example usage for testing
if __name__ == "__main__":
    import json

    print("=== Mock Projects ===")
    print(json.dumps(get_mock_projects("1645975"), indent=2))

    print("\n=== Mock Available Dates ===")
    print(json.dumps(get_mock_available_dates("12345"), indent=2))

    print("\n=== Mock Time Slots ===")
    print(json.dumps(get_mock_time_slots("12345", "2025-10-15", "REQ-123"), indent=2))
