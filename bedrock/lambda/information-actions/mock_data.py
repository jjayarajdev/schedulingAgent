"""
Mock API responses for Information Actions
Based on real API responses from core/tools.py analysis
"""
from datetime import datetime, timedelta
from typing import Dict, List, Any

def get_mock_project_details(project_id: str, customer_id: str) -> Dict[str, Any]:
    """
    Mock response for Dashboard API (project details)
    GET /dashboard/get/{client_id}/{customer_id}
    """
    # Mock projects database
    projects = {
        "12345": {
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
            "service_time_duration_type": "hours",
            "customer_customer_id": customer_id,
            "customer_first_name": "Sarah",
            "customer_last_name": "Johnson",
            "customer_email": "sarah.johnson@email.com",
            "customer_phone": "(555) 123-4567"
        },
        "12347": {
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
            "service_time_duration_type": "hours",
            "customer_customer_id": customer_id,
            "customer_first_name": "Sarah",
            "customer_last_name": "Johnson",
            "customer_email": "sarah.johnson@email.com",
            "customer_phone": "(555) 123-4567"
        },
        "12350": {
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
            "service_time_duration_type": "hours",
            "customer_customer_id": customer_id,
            "customer_first_name": "Sarah",
            "customer_last_name": "Johnson",
            "customer_email": "sarah.johnson@email.com",
            "customer_phone": "(555) 123-4567"
        }
    }

    project = projects.get(project_id)
    if not project:
        return {
            "status": "error",
            "message": f"Project {project_id} not found"
        }

    return {
        "status": "success",
        "data": [project]
    }

def get_mock_appointment_status(project_id: str) -> Dict[str, Any]:
    """
    Mock response for appointment status
    Derived from project data (no dedicated API found)
    """
    # Mock appointment statuses
    statuses = {
        "12345": {
            "project_id": "12345",
            "status": "Scheduled",
            "scheduled_date": "2025-10-15",
            "scheduled_time": "08:00 AM",
            "scheduled_end_time": "12:00 PM",
            "duration": "4 hours",
            "technician": "John Smith",
            "technician_phone": "(555) 987-6543",
            "can_reschedule": True,
            "can_cancel": True
        },
        "12347": {
            "project_id": "12347",
            "status": "Pending",
            "scheduled_date": None,
            "scheduled_time": None,
            "scheduled_end_time": None,
            "duration": "3 hours",
            "technician": None,
            "technician_phone": None,
            "can_reschedule": False,
            "can_cancel": False
        },
        "12350": {
            "project_id": "12350",
            "status": "Pending",
            "scheduled_date": None,
            "scheduled_time": None,
            "scheduled_end_time": None,
            "duration": "2 hours",
            "technician": None,
            "technician_phone": None,
            "can_reschedule": False,
            "can_cancel": False
        }
    }

    status = statuses.get(project_id, {
        "project_id": project_id,
        "status": "Unknown",
        "scheduled_date": None,
        "scheduled_time": None,
        "can_reschedule": False,
        "can_cancel": False
    })

    return {
        "status": "success",
        "data": status
    }

def get_mock_business_hours(client_id: str) -> Dict[str, Any]:
    """
    Mock response for Business Hours API
    GET /scheduler/client/{client_id}/business-hours
    """
    return {
        "status": "success",
        "data": {
            "workHours": [
                {
                    "day": "Monday",
                    "is_working": True,
                    "start": "08:00",
                    "end": "17:00"
                },
                {
                    "day": "Tuesday",
                    "is_working": True,
                    "start": "08:00",
                    "end": "17:00"
                },
                {
                    "day": "Wednesday",
                    "is_working": True,
                    "start": "08:00",
                    "end": "17:00"
                },
                {
                    "day": "Thursday",
                    "is_working": True,
                    "start": "08:00",
                    "end": "17:00"
                },
                {
                    "day": "Friday",
                    "is_working": True,
                    "start": "08:00",
                    "end": "17:00"
                },
                {
                    "day": "Saturday",
                    "is_working": False,
                    "start": None,
                    "end": None
                },
                {
                    "day": "Sunday",
                    "is_working": False,
                    "start": None,
                    "end": None
                }
            ],
            "timezone": "America/New_York",
            "client_id": client_id
        }
    }

def get_mock_weather(location: str) -> Dict[str, Any]:
    """
    Mock response for Weather API
    GET https://wttr.in/{location}?format=j1
    """
    # Generate mock weather for next 3 days
    today = datetime.now()
    weather_days = []

    for i in range(3):
        date = today + timedelta(days=i)
        weather_days.append({
            "date": date.strftime("%Y-%m-%d"),
            "maxtempF": "78" if i == 0 else ("80" if i == 1 else "75"),
            "mintempF": "65" if i == 0 else ("68" if i == 1 else "62"),
            "avgtempF": "72" if i == 0 else ("74" if i == 1 else "69"),
            "totalSnow_cm": "0.0",
            "sunHour": "8.5",
            "uvIndex": "6",
            "hourly": [
                {
                    "time": "800",
                    "tempF": "68",
                    "weatherDesc": [{"value": "Partly cloudy"}],
                    "precipMM": "0.0",
                    "humidity": "65",
                    "windspeedMiles": "8",
                    "winddir16Point": "SE",
                    "weatherCode": "116",
                    "chanceofrain": "10"
                },
                {
                    "time": "1200",
                    "tempF": "75",
                    "weatherDesc": [{"value": "Sunny"}],
                    "precipMM": "0.0",
                    "humidity": "55",
                    "windspeedMiles": "10",
                    "winddir16Point": "SE",
                    "weatherCode": "113",
                    "chanceofrain": "5"
                },
                {
                    "time": "1600",
                    "tempF": "78",
                    "weatherDesc": [{"value": "Sunny"}],
                    "precipMM": "0.0",
                    "humidity": "50",
                    "windspeedMiles": "12",
                    "winddir16Point": "S",
                    "weatherCode": "113",
                    "chanceofrain": "0"
                }
            ]
        })

    return {
        "current_condition": [
            {
                "temp_F": "72",
                "temp_C": "22",
                "weatherDesc": [{"value": "Partly cloudy"}],
                "humidity": "60",
                "windspeedMiles": "8",
                "winddir16Point": "SE",
                "precipMM": "0.0",
                "pressure": "1015",
                "cloudcover": "25",
                "FeelsLikeF": "72",
                "uvIndex": "5"
            }
        ],
        "weather": weather_days,
        "nearest_area": [
            {
                "areaName": [{"value": location.split(",")[0] if "," in location else location}],
                "region": [{"value": "Florida"}],
                "country": [{"value": "United States"}],
                "latitude": "27.95",
                "longitude": "-82.46"
            }
        ]
    }

# Example usage for testing
if __name__ == "__main__":
    import json

    print("=== Mock Project Details ===")
    print(json.dumps(get_mock_project_details("12345", "1645975"), indent=2))

    print("\n=== Mock Appointment Status ===")
    print(json.dumps(get_mock_appointment_status("12345"), indent=2))

    print("\n=== Mock Business Hours ===")
    print(json.dumps(get_mock_business_hours("09PF05VD"), indent=2))

    print("\n=== Mock Weather ===")
    print(json.dumps(get_mock_weather("Tampa, FL"), indent=2))
