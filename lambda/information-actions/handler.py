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
import re
import requests
from typing import Dict, Any
from urllib.parse import quote

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

# US State abbreviation to full name mapping
US_STATES = {
    'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas', 'CA': 'California',
    'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware', 'FL': 'Florida', 'GA': 'Georgia',
    'HI': 'Hawaii', 'ID': 'Idaho', 'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa',
    'KS': 'Kansas', 'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
    'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi', 'MO': 'Missouri',
    'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada', 'NH': 'New Hampshire', 'NJ': 'New Jersey',
    'NM': 'New Mexico', 'NY': 'New York', 'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio',
    'OK': 'Oklahoma', 'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
    'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah', 'VT': 'Vermont',
    'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia', 'WI': 'Wisconsin', 'WY': 'Wyoming',
    'DC': 'District of Columbia'
}

def geocode_location(location: str) -> Dict[str, Any]:
    """
    Geocode a city name to get coordinates using Open-Meteo Geocoding API
    Handles duplicate city names by filtering by state when available.

    Args:
        location: City name, zip code, or location string

    Returns:
        Dict with latitude, longitude, name, admin1, country

    Raises:
        ValueError: If location not found
    """
    logger.info(f"Geocoding location: {location}")

    # Smart extraction of city name AND state from various formats:
    # - "Canterbury Park, Minneapolis, MN 55379" → city="Minneapolis", state="Minnesota"
    # - "401 Chicago Avenue, Minneapolis, MN 55415" → city="Minneapolis", state="Minnesota"
    # - "Minneapolis, MN" → city="Minneapolis", state="Minnesota"
    # - "Springfield, IL" → city="Springfield", state="Illinois"
    # - "Minneapolis" → city="Minneapolis", state=None

    parts = [p.strip() for p in location.split(',')]
    city_name = location  # Default
    state_name = None  # State to filter results by

    if len(parts) >= 3:
        # Format: "Street/Neighborhood, City, State ZIP"
        city_name = parts[-2].strip()
        state_part = parts[-1].strip()
        # Extract state abbreviation (e.g., "MN 55379" → "MN")
        state_match = re.match(r'^([A-Z]{2})\s*\d*', state_part)
        if state_match:
            state_abbr = state_match.group(1)
            state_name = US_STATES.get(state_abbr)
    elif len(parts) == 2:
        # Format: "City, State" or "City, State ZIP"
        city_name = parts[0].strip()
        state_part = parts[1].strip()
        state_match = re.match(r'^([A-Z]{2})\s*\d*', state_part)
        if state_match:
            state_abbr = state_match.group(1)
            state_name = US_STATES.get(state_abbr)
    # else: single part, use as-is

    logger.info(f"Geocoding: city='{city_name}', state='{state_name}'")

    # URL encode and request multiple results to handle duplicate city names
    encoded_location = quote(city_name)
    count = 10 if state_name else 1  # Get more results if we need to filter by state
    url = f"https://geocoding-api.open-meteo.com/v1/search?name={encoded_location}&count={count}&language=en&format=json"

    logger.info(f"Geocoding URL: {url}")

    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        data = res.json()

        logger.info(f"Geocoding response: {len(data.get('results', []))} results")

        if not data.get("results"):
            raise ValueError(f"Location '{location}' not found")

        results = data["results"]

        # If we have a state, filter to find the right city
        if state_name:
            for r in results:
                if r.get("admin1", "").lower() == state_name.lower() and r.get("country") == "United States":
                    logger.info(f"Found match: {r['name']}, {r.get('admin1')} (filtered by state)")
                    return {
                        "latitude": r["latitude"],
                        "longitude": r["longitude"],
                        "name": r["name"],
                        "admin1": r.get("admin1", ""),
                        "country": r.get("country", ""),
                        "timezone": r.get("timezone", "UTC")
                    }
            # No exact state match, fall through to first US result or first result
            logger.warning(f"No exact state match for {state_name}, using best match")

        # Return first result (or first US result if we had a state hint)
        result = results[0]
        return {
            "latitude": result["latitude"],
            "longitude": result["longitude"],
            "name": result["name"],
            "admin1": result.get("admin1", ""),
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
            f"&forecast_days=7"
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

        weather_info = {
            "location": {
                "latitude": response.get("latitude"),
                "longitude": response.get("longitude"),
                "name": location_info.get("name", ""),
                "admin1": location_info.get("admin1", ""),
                "country": location_info.get("country", ""),
                "timezone": response.get("timezone", ""),
                "elevation_meters": response.get("elevation", 0)
            },
            "current": {
                "time": current.get("time"),
                "temp_f": current.get("temperature_2m"),
                "feels_like_f": current.get("apparent_temperature"),
                "condition": WEATHER_CODES.get(current.get("weather_code", 0), "Unknown"),
                "weather_code": current.get("weather_code"),
                "humidity": current.get("relative_humidity_2m"),
                "wind_mph": current.get("wind_speed_10m"),
                "wind_direction": current.get("wind_direction_10m"),
                "precipitation_inch": current.get("precipitation", 0)
            },
            "forecast": [
                {
                    "date": daily["time"][i],
                    "max_temp_f": daily["temperature_2m_max"][i],
                    "min_temp_f": daily["temperature_2m_min"][i],
                    "condition": WEATHER_CODES.get(daily["weather_code"][i], "Unknown"),
                    "weather_code": daily["weather_code"][i],
                    "precipitation_probability": daily["precipitation_probability_max"][i]
                }
                for i in range(min(7, len(daily.get("time", []))))
            ],
            "context": {
                "project_id": project_id,
                "address": address
            }
        }

        return {
            "action": "get_weather",
            "location": location_info.get("name", location),
            "coordinates": {
                "latitude": lat,
                "longitude": lon
            },
            "weather": weather_info,
            "mock_mode": False,
            "api_provider": "open-meteo"
        }

    # Mock mode response formatting (for testing)
    current = response.get("current_condition", [{}])[0]
    forecast = response.get("weather", [])
    area = response.get("nearest_area", [{}])[0]

    weather_info = {
        "location": {
            "area": area.get("areaName", [{}])[0].get("value"),
            "region": area.get("region", [{}])[0].get("value"),
            "country": area.get("country", [{}])[0].get("value")
        },
        "current": {
            "temp_f": current.get("temp_F"),
            "temp_c": current.get("temp_C"),
            "condition": current.get("weatherDesc", [{}])[0].get("value"),
            "humidity": current.get("humidity"),
            "wind_mph": current.get("windspeedMiles"),
            "wind_dir": current.get("winddir16Point"),
            "feels_like_f": current.get("FeelsLikeF"),
            "uv_index": current.get("uvIndex")
        },
        "forecast": [
            {
                "date": day.get("date"),
                "max_temp_f": day.get("maxtempF"),
                "min_temp_f": day.get("mintempF"),
                "avg_temp_f": day.get("avgtempF"),
                "uv_index": day.get("uvIndex"),
                "sun_hours": day.get("sunHour")
            }
            for day in forecast[:3]
        ]
    }

    return {
        "action": "get_weather",
        "location": location,
        "weather": weather_info,
        "mock_mode": True
    }

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
