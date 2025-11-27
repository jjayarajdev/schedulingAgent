#!/usr/bin/env python3
"""
Test script for Open-Meteo weather integration
Tests both coordinate-based and city-name-based weather queries
"""

import json
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

# Set mock mode to false for real API testing
os.environ['USE_MOCK_API'] = 'false'

from handler import lambda_handler

def test_weather_with_coordinates():
    """Test weather query with coordinates (Tampa)"""
    print("\n" + "="*80)
    print("TEST 1: Weather with Coordinates (Tampa)")
    print("="*80)

    event = {
        "apiPath": "/get_weather",
        "httpMethod": "POST",
        "function": "get_weather",
        "parameters": [
            {"name": "latitude", "value": "27.9506"},
            {"name": "longitude", "value": "-82.4572"},
            {"name": "location", "value": "Tampa"},
            {"name": "customer_id", "value": "1645869"},
            {"name": "user_id", "value": "user123"},
            {"name": "project_id", "value": "7751741"}
        ],
        "sessionAttributes": {
            "customer_id": "1645869"
        }
    }

    response = lambda_handler(event, None)
    print("\nResponse:")
    print(json.dumps(response, indent=2))

    # Extract weather data
    body = json.loads(response['response']['responseBody']['application/json']['body'])
    print("\nWeather Summary:")
    print(f"Location: {body['location']}")
    print(f"Coordinates: {body['coordinates']['latitude']}, {body['coordinates']['longitude']}")
    print(f"Current Temp: {body['weather']['current']['temp_f']}F")
    print(f"Condition: {body['weather']['current']['condition']}")
    print(f"Forecast Days: {len(body['weather']['forecast'])}")

    return response

def test_weather_with_city_name():
    """Test weather query with city name only (Minneapolis)"""
    print("\n" + "="*80)
    print("TEST 2: Weather with City Name (Minneapolis)")
    print("="*80)

    event = {
        "apiPath": "/get_weather",
        "httpMethod": "POST",
        "function": "get_weather",
        "parameters": [
            {"name": "location", "value": "Minneapolis, MN"},
            {"name": "customer_id", "value": "1645869"},
            {"name": "address", "value": "401 Chicago Avenue Minneapolis MN"}
        ],
        "sessionAttributes": {
            "customer_id": "1645869"
        }
    }

    response = lambda_handler(event, None)
    print("\nResponse:")
    print(json.dumps(response, indent=2))

    # Extract weather data
    body = json.loads(response['response']['responseBody']['application/json']['body'])
    print("\nWeather Summary:")
    print(f"Location: {body['location']}")
    print(f"Coordinates (geocoded): {body['coordinates']['latitude']}, {body['coordinates']['longitude']}")
    print(f"Current Temp: {body['weather']['current']['temp_f']}F")
    print(f"Condition: {body['weather']['current']['condition']}")
    print(f"Forecast Days: {len(body['weather']['forecast'])}")

    return response

def test_weather_project_context():
    """Test weather query with full project context"""
    print("\n" + "="*80)
    print("TEST 3: Weather with Full Project Context")
    print("="*80)

    event = {
        "apiPath": "/get_weather",
        "httpMethod": "POST",
        "function": "get_weather",
        "parameters": [
            {"name": "latitude", "value": "44.97364610000000"},
            {"name": "longitude", "value": "-93.25749449999999"},
            {"name": "customer_id", "value": "1645869"},
            {"name": "user_id", "value": "user123"},
            {"name": "project_id", "value": "7751741"},
            {"name": "address", "value": "401 Chicago Avenue Minneapolis Minnesota MN 55415"}
        ],
        "sessionAttributes": {
            "customer_id": "1645869",
            "client_id": "09PF05VD"
        }
    }

    response = lambda_handler(event, None)
    print("\nResponse:")
    print(json.dumps(response, indent=2))

    # Extract weather data
    body = json.loads(response['response']['responseBody']['application/json']['body'])
    print("\nWeather Summary:")
    print(f"Location: {body['location']}")
    print(f"Context: Project {body['weather']['context']['project_id']}, Customer {body['weather']['context']['customer_id']}")
    print(f"Current Temp: {body['weather']['current']['temp_f']}F")
    print(f"Feels Like: {body['weather']['current']['feels_like_f']}F")
    print(f"Condition: {body['weather']['current']['condition']}")
    print(f"Humidity: {body['weather']['current']['humidity']}%")
    print(f"Wind: {body['weather']['current']['wind_mph']} mph")
    print("\n3-Day Forecast:")
    for day in body['weather']['forecast']:
        print(f"  {day['date']}: {day['min_temp_f']}-{day['max_temp_f']}F, {day['condition']}, {day['precipitation_probability']}% rain")

    return response

def test_missing_location():
    """Test error handling when no location provided"""
    print("\n" + "="*80)
    print("TEST 4: Error Handling - Missing Location")
    print("="*80)

    event = {
        "apiPath": "/get_weather",
        "httpMethod": "POST",
        "function": "get_weather",
        "parameters": [
            {"name": "customer_id", "value": "1645869"}
        ],
        "sessionAttributes": {
            "customer_id": "1645869"
        }
    }

    response = lambda_handler(event, None)
    print("\nResponse:")
    print(json.dumps(response, indent=2))

    # Should return error
    body = json.loads(response['response']['responseBody']['application/json']['body'])
    print(f"\nError Message: {body.get('error', 'No error')}")

    return response

def test_invalid_city():
    """Test error handling for invalid city name"""
    print("\n" + "="*80)
    print("TEST 5: Error Handling - Invalid City")
    print("="*80)

    event = {
        "apiPath": "/get_weather",
        "httpMethod": "POST",
        "function": "get_weather",
        "parameters": [
            {"name": "location", "value": "InvalidCityXYZ12345"}
        ]
    }

    response = lambda_handler(event, None)
    print("\nResponse:")
    print(json.dumps(response, indent=2))

    # Should return error
    body = json.loads(response['response']['responseBody']['application/json']['body'])
    print(f"\nError Message: {body.get('error', 'No error')}")

    return response

if __name__ == "__main__":
    print("\n" + "="*80)
    print("OPEN-METEO WEATHER API INTEGRATION TESTS")
    print("="*80)

    try:
        # Run all tests
        test_weather_with_coordinates()
        test_weather_with_city_name()
        test_weather_project_context()
        test_missing_location()
        test_invalid_city()

        print("\n" + "="*80)
        print(" ALL TESTS COMPLETED")
        print("="*80)

    except Exception as e:
        print(f"\n TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
