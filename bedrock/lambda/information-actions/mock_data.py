"""
Mock API responses for Information Actions (Weather Only)

All project-related mock data has been moved to scheduling-actions/mock_data.py

This file now ONLY contains weather mock data.
"""
from datetime import datetime, timedelta
from typing import Dict, Any

def get_mock_weather(location: str) -> Dict[str, Any]:
    """
    Mock response for Weather API
    Returns realistic weather data for testing

    Note: All other mock functions (get_mock_projects, get_mock_project_details,
    get_mock_appointment_status, get_mock_business_hours) have been moved to
    scheduling-actions/mock_data.py
    """
    # Simulate different weather based on location
    location_lower = location.lower()

    # Default weather (Tampa-like)
    temp_f = "75"
    temp_c = "24"
    condition = "Partly cloudy"
    area_name = location.split(',')[0].strip() if ',' in location else location
    region_name = "Florida"
    country_name = "United States of America"

    # Adjust for common locations
    if any(city in location_lower for city in ['miami', 'fort lauderdale', 'west palm']):
        temp_f = "78"
        temp_c = "26"
        condition = "Sunny"
    elif any(city in location_lower for city in ['orlando', 'kissimmee']):
        temp_f = "76"
        temp_c = "24"
        condition = "Mostly sunny"
    elif any(city in location_lower for city in ['jacksonville']):
        temp_f = "72"
        temp_c = "22"
        condition = "Clear"
    elif any(city in location_lower for city in ['clearwater', 'st petersburg', 'st pete']):
        temp_f = "74"
        temp_c = "23"
        condition = "Partly cloudy"

    return {
        "current_condition": [
            {
                "temp_F": temp_f,
                "temp_C": temp_c,
                "weatherDesc": [{"value": condition}],
                "humidity": "65",
                "windspeedMiles": "10",
                "winddir16Point": "NE",
                "FeelsLikeF": str(int(temp_f) + 2),
                "uvIndex": "5"
            }
        ],
        "weather": [
            {
                "date": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
                "maxtempF": str(int(temp_f) + 3),
                "mintempF": str(int(temp_f) - 7),
                "avgtempF": temp_f,
                "uvIndex": "6",
                "sunHour": "8.5"
            },
            {
                "date": (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d"),
                "maxtempF": str(int(temp_f) + 2),
                "mintempF": str(int(temp_f) - 6),
                "avgtempF": str(int(temp_f) + 1),
                "uvIndex": "5",
                "sunHour": "7.8"
            },
            {
                "date": (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d"),
                "maxtempF": str(int(temp_f) + 1),
                "mintempF": str(int(temp_f) - 5),
                "avgtempF": temp_f,
                "uvIndex": "6",
                "sunHour": "8.2"
            }
        ],
        "nearest_area": [
            {
                "areaName": [{"value": area_name}],
                "region": [{"value": region_name}],
                "country": [{"value": country_name}]
            }
        ]
    }
