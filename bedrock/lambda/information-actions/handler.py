"""
Information Actions Lambda Handler
Handles weather-related queries for Bedrock Agent

Actions:
1. get_weather - Get weather forecast for a location

This handler is specialized for external weather API calls only.
All project-related actions have been moved to the scheduling-actions handler.

Supports both MOCK and REAL API modes via USE_MOCK_API environment variable
"""

import json
import logging
import requests
from typing import Dict, Any

# Import configuration and mock data
from config import (
    USE_MOCK_API,
    get_api_config,
    get_auth_headers
)
from mock_data import get_mock_weather

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# ============================================================================
# Helper Functions
# ============================================================================

def extract_parameters(event: Dict) -> Dict[str, Any]:
    """
    Extract parameters from Bedrock Agent event
    Handles both actionGroup and requestBody formats
    Resolves session attribute references
    """
    try:
        # Bedrock Agent passes parameters in different ways
        if 'parameters' in event and event['parameters']:
            params = {p['name']: p['value'] for p in event['parameters']}
        elif 'requestBody' in event:
            content = event['requestBody'].get('content', {})
            app_json = content.get('application/json', {})

            # Check if properties array format (from action groups)
            if isinstance(app_json, dict) and 'properties' in app_json:
                params = {p['name']: p['value'] for p in app_json['properties']}
            # Check if JSON string format
            elif isinstance(app_json, str):
                params = json.loads(app_json)
            # Already a dict
            else:
                params = app_json
        else:
            # Fallback: try to parse body
            body = event.get('body', '{}')
            if isinstance(body, str):
                params = json.loads(body)
            else:
                params = body

        # Resolve session attribute references
        session_attrs = event.get('sessionAttributes', {})
        for key, value in params.items():
            if isinstance(value, str):
                # Handle $param_name format (e.g., $customer_id)
                if value.startswith('$') and not value.startswith('$session.'):
                    attr_name = value[1:]
                    if attr_name in session_attrs:
                        params[key] = session_attrs[attr_name]
                        logger.info(f"Resolved ${attr_name} -> {params[key]}")
                # Handle session.attr format
                elif 'session.' in value:
                    clean_value = value.strip('{}').strip('$').strip('{}')
                    if clean_value.startswith('session.'):
                        attr_name = clean_value.replace('session.', '')
                        if attr_name in session_attrs:
                            params[key] = session_attrs[attr_name]
                            logger.info(f"Resolved {value} -> {params[key]}")

        logger.info(f"Extracted parameters: {params}")
        return params

    except Exception as e:
        logger.error(f"Error extracting parameters: {str(e)}")
        return {}

def format_success_response(event: Dict, action: str, result: Dict[str, Any]) -> Dict[str, Any]:
    """Format successful response for Bedrock Agent - supports both OpenAPI and Function formats"""
    # Check if this is function calling format (new format)
    if 'function' in event:
        return {
            'messageVersion': '1.0',
            'response': {
                'actionGroup': event.get('actionGroup', 'information'),
                'function': event.get('function', action),
                'functionResponse': {
                    'responseBody': {
                        'TEXT': {
                            'body': json.dumps(result)
                        }
                    }
                }
            }
        }

    # Fall back to OpenAPI format (old format)
    return {
        'messageVersion': '1.0',
        'response': {
            'actionGroup': event.get('actionGroup', 'information'),
            'apiPath': event.get('apiPath', f'/{action}'),
            'httpMethod': event.get('httpMethod', 'POST'),
            'httpStatusCode': 200,
            'responseBody': {
                'application/json': {
                    'body': json.dumps(result)
                }
            }
        }
    }

def format_error_response(event: Dict, action: str, error_message: str, status_code: int = 500) -> Dict[str, Any]:
    """Format error response for Bedrock Agent - supports both OpenAPI and Function formats"""
    error_body = {'error': error_message, 'action': action}

    # Check if this is function calling format (new format)
    if 'function' in event:
        return {
            'messageVersion': '1.0',
            'response': {
                'actionGroup': event.get('actionGroup', 'information'),
                'function': event.get('function', action),
                'functionResponse': {
                    'responseBody': {
                        'TEXT': {
                            'body': json.dumps(error_body)
                        }
                    }
                }
            }
        }

    # Fall back to OpenAPI format (old format)
    return {
        'messageVersion': '1.0',
        'response': {
            'actionGroup': event.get('actionGroup', 'information'),
            'apiPath': event.get('apiPath', f'/{action}'),
            'httpMethod': event.get('httpMethod', 'POST'),
            'httpStatusCode': status_code,
            'responseBody': {
                'application/json': {
                    'body': json.dumps(error_body)
                }
            }
        }
    }

# ============================================================================
# Weather Code Mapping (WMO Weather interpretation codes)
# ============================================================================

WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Foggy",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail"
}

# ============================================================================
# Helper Functions for Weather
# ============================================================================

def format_day_name(date_str: str) -> str:
    """Format date string to friendly day name"""
    from datetime import datetime
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        today = datetime.now().date()
        date = date_obj.date()

        if date == today:
            return "Today"
        elif (date - today).days == 1:
            return "Tomorrow"
        else:
            return date_obj.strftime("%A")  # Full day name (e.g., "Wednesday")
    except:
        return date_str

def generate_installation_recommendation(temp_f: float, condition: str, precip_prob: int) -> str:
    """Generate installation recommendation based on weather conditions"""
    condition_lower = condition.lower()

    # Check for rain/snow
    if precip_prob > 60 or "rain" in condition_lower or "snow" in condition_lower or "storm" in condition_lower:
        return "Weather may affect installation. Consider rescheduling for better conditions."

    # Check for extreme cold
    if temp_f < 32:
        return "Freezing temperatures - installation materials may require special handling."

    # Check for extreme heat
    if temp_f > 95:
        return "Very hot conditions - crew will need heat precautions."

    # Check for moderate precip probability
    if precip_prob > 30:
        return "Some chance of precipitation - monitor weather closely."

    # Good conditions
    return "Great weather for outdoor installation work!"

def geocode_location(location: str) -> Dict[str, Any]:
    """
    Geocode a city name to get coordinates using Open-Meteo Geocoding API

    Args:
        location: City name, zip code, or location string

    Returns:
        Dict with latitude, longitude, name, admin1, country

    Raises:
        ValueError: If location not found
    """
    logger.info(f"Geocoding location: {location}")

    url = f"https://geocoding-api.open-meteo.com/v1/search?name={location}&count=1&language=en&format=json"

    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        data = res.json()

        if not data.get("results"):
            raise ValueError(f"Location '{location}' not found")

        result = data["results"][0]
        return {
            "latitude": result["latitude"],
            "longitude": result["longitude"],
            "name": result["name"],
            "admin1": result.get("admin1", ""),  # State/Province
            "country": result.get("country", ""),
            "timezone": result.get("timezone", "UTC")
        }
    except requests.RequestException as e:
        logger.error(f"Geocoding API request failed: {str(e)}")
        raise ValueError(f"Unable to geocode location '{location}': {str(e)}")

# ============================================================================
# Action Handler
# ============================================================================

def handle_get_weather(params: Dict, config: Dict, auth_headers: Dict) -> Dict[str, Any]:
    """
    Action: get_weather
    Returns weather forecast for a location using Open-Meteo API

    Parameters (in priority order):
    1. latitude + longitude (preferred - most accurate)
    2. location (city name - requires geocoding)

    Additional context parameters (optional):
    - project_id: For context and logging
    - address: Full address for reference and logging

    Note: Uses Open-Meteo API (no authentication needed)
    This is the ONLY action in this handler - all other actions moved to scheduling-actions
    """
    # Extract location parameters (lat/long preferred, location as fallback)
    latitude = params.get('latitude')
    longitude = params.get('longitude')
    location = params.get('location')

    # Extract optional context parameters for logging
    project_id = params.get('project_id')
    address = params.get('address')

    logger.info(f"Weather request - project_id: {project_id}, address: {address}")

    # Determine coordinates
    location_info = {}

    if latitude and longitude:
        # Priority 1: Use provided coordinates (most accurate)
        logger.info(f"[COORDINATES] Using lat={latitude}, lon={longitude}")
        lat = float(latitude)
        lon = float(longitude)
        location_info = {
            "latitude": lat,
            "longitude": lon,
            "name": location or address or f"{lat}, {lon}",
            "source": "coordinates_provided"
        }
    elif location:
        # Priority 2: Geocode the location name
        logger.info(f"[GEOCODE] Location name provided: {location}")
        if not USE_MOCK_API:
            geo_result = geocode_location(location)
            lat = geo_result["latitude"]
            lon = geo_result["longitude"]
            location_info = {
                "latitude": lat,
                "longitude": lon,
                "name": geo_result["name"],
                "admin1": geo_result.get("admin1", ""),
                "country": geo_result.get("country", ""),
                "source": "geocoded"
            }
        else:
            # Mock mode - use default coordinates
            lat, lon = 27.9506, -82.4572  # Tampa
            location_info = {
                "latitude": lat,
                "longitude": lon,
                "name": location,
                "source": "mock"
            }
    else:
        raise ValueError("Missing location parameters: provide either (latitude + longitude) or location")

    # Fetch weather data
    if USE_MOCK_API:
        logger.info(f"[MOCK] Fetching weather for {location_info['name']}")
        response = get_mock_weather(location_info['name'])
    else:
        logger.info(f"[REAL] Fetching weather from Open-Meteo for lat={lat}, lon={lon}")

        # Open-Meteo API endpoint
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m,wind_direction_10m"
            f"&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code"
            f"&temperature_unit=fahrenheit"
            f"&wind_speed_unit=mph"
            f"&precipitation_unit=inch"
            f"&timezone=auto"
            f"&forecast_days=3"
        )

        try:
            res = requests.get(url, timeout=10)
            res.raise_for_status()
            response = res.json()
        except requests.RequestException as e:
            logger.error(f"Open-Meteo API request failed: {str(e)}")
            raise ValueError(f"Unable to fetch weather data: {str(e)}")

        # Format weather data from Open-Meteo
        current = response.get("current", {})
        daily = response.get("daily", {})

        # Format weather data for UI consumption (pre-formatted, agent just passes through)
        temp_f = current.get("temperature_2m")
        feels_like_f = current.get("apparent_temperature")
        condition = WEATHER_CODES.get(current.get("weather_code", 0), "Unknown")
        humidity = current.get("relative_humidity_2m")
        wind_mph = current.get("wind_speed_10m")

        # Generate installation recommendation based on conditions
        recommendation = generate_installation_recommendation(
            temp_f, condition, daily["precipitation_probability_max"][0] if daily.get("precipitation_probability_max") else 0
        )

        # UI-ready format (agent will pass this through as JSON)
        ui_format = {
            "location": location_info.get("name", location),
            "address": address if address else None,
            "current": {
                "temperature": round(temp_f, 1) if temp_f else None,
                "condition": condition,
                "humidity": humidity,
                "windSpeed": round(wind_mph, 1) if wind_mph else None
            },
            "forecast": [
                {
                    "day": format_day_name(daily["time"][i]) if i == 0 else format_day_name(daily["time"][i]),
                    "high": round(daily["temperature_2m_max"][i]),
                    "low": round(daily["temperature_2m_min"][i]),
                    "condition": WEATHER_CODES.get(daily["weather_code"][i], "Unknown"),
                    "precipitation": daily["precipitation_probability_max"][i]
                }
                for i in range(min(3, len(daily.get("time", []))))
            ],
            "recommendation": recommendation
        }

        # Remove null address field if not provided
        if ui_format["address"] is None:
            del ui_format["address"]

        return ui_format

    # Mock mode response formatting (for testing) - same UI format
    current = response.get("current_condition", [{}])[0]
    forecast = response.get("weather", [])

    temp_f = int(current.get("temp_F", 75))
    condition_desc = current.get("weatherDesc", [{}])[0].get("value", "Partly Cloudy")

    # UI-ready format (same as real API)
    ui_format = {
        "location": location,
        "address": address if address else None,
        "current": {
            "temperature": temp_f,
            "condition": condition_desc,
            "humidity": int(current.get("humidity", 65)),
            "windSpeed": int(current.get("windspeedMiles", 8))
        },
        "forecast": [
            {
                "day": "Today" if i == 0 else ("Tomorrow" if i == 1 else "Day 3"),
                "high": int(day.get("maxtempF", 78)),
                "low": int(day.get("mintempF", 68)),
                "condition": day.get("weatherDesc", [{}])[0].get("value", "Sunny") if day.get("weatherDesc") else "Sunny",
                "precipitation": 10 if i == 0 else (0 if i == 1 else 5)
            }
            for i, day in enumerate(forecast[:3])
        ],
        "recommendation": generate_installation_recommendation(temp_f, condition_desc, 10)
    }

    # Remove null address field if not provided
    if ui_format["address"] is None:
        del ui_format["address"]

    return ui_format

# ============================================================================
# Lambda Handler
# ============================================================================

def lambda_handler(event, context):
    """
    Main Lambda handler for information actions (weather only)

    All project-related actions have been moved to scheduling-actions handler:
    - get_projects -> scheduling-actions (list_projects)
    - get_project_details -> scheduling-actions (get_project_details)
    - get_appointment_status -> scheduling-actions (get_appointment_status)
    - get_working_hours -> scheduling-actions (get_working_hours)

    This handler now ONLY handles weather queries.
    """
    logger.info(f"Received event: {json.dumps(event)}")

    try:
        # Extract action from event
        # Function calling format uses 'function', OpenAPI format uses 'apiPath'
        action = event.get('function', event.get('apiPath', '')).lstrip('/')
        if not action:
            # Fallback: check for action in parameters
            params = extract_parameters(event)
            action = params.get('action', '').replace('_', '-')

        if not action:
            return format_error_response(
                event,
                'unknown',
                'No action specified in event',
                400
            )

        # Convert underscores to hyphens for consistency
        action = action.replace('_', '-')

        logger.info(f"Processing action: {action}")

        # Only weather action is supported
        if action != 'get-weather':
            error_msg = f"Action '{action}' has been moved to scheduling-actions handler. This handler only supports 'get-weather'."
            logger.warning(error_msg)
            return format_error_response(event, action, error_msg, 400)

        # Extract parameters
        params = extract_parameters(event)

        # Get configuration
        config = get_api_config()

        # Execute weather handler (no auth needed for external weather API)
        result = handle_get_weather(params, config, {})

        # Return formatted response
        return format_success_response(event, action, result)

    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        return format_error_response(
            event,
            action if 'action' in locals() else 'unknown',
            f'Validation error: {str(e)}',
            400
        )

    except requests.RequestException as e:
        logger.error(f"API request failed: {str(e)}")
        return format_error_response(
            event,
            action if 'action' in locals() else 'unknown',
            f'API request failed: {str(e)}',
            502
        )

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return format_error_response(
            event,
            action if 'action' in locals() else 'unknown',
            f'Internal error: {str(e)}',
            500
        )

# For local testing
if __name__ == "__main__":
    # Test event
    test_event = {
        "apiPath": "/get-weather",
        "httpMethod": "POST",
        "parameters": [
            {"name": "location", "value": "Tampa,FL"}
        ]
    }

    response = lambda_handler(test_event, None)
    print(json.dumps(response, indent=2))
