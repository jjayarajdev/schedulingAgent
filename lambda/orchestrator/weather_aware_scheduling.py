"""
Weather-Aware Scheduling for Outdoor Projects

Automatically checks weather conditions when scheduling outdoor projects
and warns users about unsuitable conditions (rain, extreme temperatures, etc.)
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger()

# Define outdoor project categories that are weather-dependent
OUTDOOR_CATEGORIES = {
    "Decking": {
        "bad_conditions": ["rain", "snow", "thunderstorm"],
        "rain_threshold": 50,  # % precipitation
        "temp_min": 40,  # F
        "temp_max": 95,  # F
        "wind_max": 25,  # mph
    },
    "Roofing": {
        "bad_conditions": ["rain", "snow", "thunderstorm", "ice"],
        "rain_threshold": 30,
        "temp_min": 40,
        "temp_max": 90,
        "wind_max": 20,
    },
    "Siding": {
        "bad_conditions": ["rain", "snow", "thunderstorm"],
        "rain_threshold": 50,
        "temp_min": 35,
        "temp_max": 95,
        "wind_max": 25,
    },
    "Exterior Painting": {
        "bad_conditions": ["rain", "snow"],
        "rain_threshold": 20,
        "temp_min": 50,
        "temp_max": 90,
        "wind_max": 15,
    },
    "Fencing": {
        "bad_conditions": ["rain", "snow", "thunderstorm"],
        "rain_threshold": 50,
        "temp_min": 32,
        "temp_max": 100,
        "wind_max": 30,
    },
    "Fence": {  # Alias for "Fence Installation" projects
        "bad_conditions": ["rain", "snow", "thunderstorm"],
        "rain_threshold": 50,
        "temp_min": 32,
        "temp_max": 100,
        "wind_max": 30,
    },
    "Concrete": {
        "bad_conditions": ["rain", "snow", "thunderstorm", "ice"],
        "rain_threshold": 30,
        "temp_min": 40,
        "temp_max": 95,
        "wind_max": 20,
    },
    "Flooring": {  # Outdoor flooring (decks, patios)
        "bad_conditions": ["rain", "snow"],
        "rain_threshold": 50,
        "temp_min": 40,
        "temp_max": 95,
        "wind_max": 25,
    },
    "Windows": {  # Exterior window installation
        "bad_conditions": ["rain", "snow", "thunderstorm"],
        "rain_threshold": 40,
        "temp_min": 35,
        "temp_max": 95,
        "wind_max": 25,
    },
    "Doors": {  # Exterior door installation
        "bad_conditions": ["rain", "snow", "thunderstorm"],
        "rain_threshold": 40,
        "temp_min": 35,
        "temp_max": 95,
        "wind_max": 25,
    },
}


def is_outdoor_project(category: str) -> bool:
    """
    Check if project category requires outdoor work

    Args:
        category: Project category (e.g., "Decking", "Roofing")

    Returns:
        True if project is outdoor work, False otherwise
    """
    if not category:
        return False

    # Case-insensitive check
    category_lower = category.lower()
    return any(cat.lower() in category_lower for cat in OUTDOOR_CATEGORIES.keys())


def get_category_criteria(category: str) -> Optional[Dict]:
    """
    Get weather criteria for a specific category

    Args:
        category: Project category

    Returns:
        Dictionary with weather criteria or None
    """
    if not category:
        return None

    # Find matching category (case-insensitive)
    for cat, criteria in OUTDOOR_CATEGORIES.items():
        if cat.lower() in category.lower():
            return criteria

    # Default outdoor criteria
    return {
        "bad_conditions": ["rain", "snow", "thunderstorm"],
        "rain_threshold": 50,
        "temp_min": 40,
        "temp_max": 95,
        "wind_max": 25,
    }


def find_forecast_for_date(weather_data: Dict, target_date: str) -> Optional[Dict]:
    """
    Find forecast for specific date from weather data

    Args:
        weather_data: Weather response from Lambda
        target_date: Date string (YYYY-MM-DD)

    Returns:
        Forecast dict for that date or None
    """
    try:
        weather = weather_data.get('weather', {})
        forecast_list = weather.get('forecast', [])

        for day in forecast_list:
            if day.get('date') == target_date:
                return day

        # If exact date not found, check if it's today
        current = weather.get('current', {})
        if current:
            # Assume current is for today
            return {
                'date': target_date,
                'condition': current.get('condition', 'Unknown'),
                'max_temp_f': current.get('temp_f', current.get('temp_F', 0)),
                'min_temp_f': current.get('temp_f', current.get('temp_F', 0)),
                'precipitation_probability': 0  # Current weather doesn't have forecast
            }

        return None
    except Exception as e:
        logger.error(f"Error finding forecast for date {target_date}: {e}")
        return None


def analyze_weather_suitability(
    forecast: Dict,
    category: str,
    target_date: str
) -> Dict[str, Any]:
    """
    Analyze if weather conditions are suitable for outdoor work

    Args:
        forecast: Forecast data for the date
        category: Project category (e.g., "Decking")
        target_date: Date string for context

    Returns:
        Dictionary with analysis:
        {
            "suitable": bool,
            "warnings": List[str],
            "severity": "low"|"medium"|"high",
            "recommendation": str
        }
    """
    if not forecast:
        return {
            "suitable": True,
            "warnings": [],
            "severity": "low",
            "recommendation": "Weather forecast not available for this date."
        }

    criteria = get_category_criteria(category)
    if not criteria:
        return {"suitable": True, "warnings": [], "severity": "low", "recommendation": ""}

    warnings = []
    severity = "low"

    # Check condition
    condition = forecast.get('condition', '').lower()
    for bad_cond in criteria['bad_conditions']:
        if bad_cond.lower() in condition:
            warnings.append(f"{forecast.get('condition', 'Unknown')} forecasted")
            severity = "high" if bad_cond in ['thunderstorm', 'ice', 'snow'] else "medium"

    # Check precipitation - ensure numeric comparison
    try:
        precip = float(forecast.get('precipitation_probability', 0) or 0)
    except (ValueError, TypeError):
        precip = 0
    if precip >= criteria['rain_threshold']:
        warnings.append(f"{int(precip)}% chance of precipitation")
        if precip >= 70:
            severity = "high"
        elif severity == "low":
            severity = "medium"

    # Check temperature - ensure numeric comparison
    try:
        max_temp = float(forecast.get('max_temp_f', 75) or 75)
        min_temp = float(forecast.get('min_temp_f', 60) or 60)
    except (ValueError, TypeError):
        max_temp = 75
        min_temp = 60

    if max_temp < criteria['temp_min']:
        warnings.append(f"Temperature too cold (high of {int(max_temp)}F)")
        severity = "medium" if severity == "low" else severity

    if min_temp > criteria['temp_max']:
        warnings.append(f"Temperature too hot (low of {int(min_temp)}F)")
        severity = "medium" if severity == "low" else severity

    # Check wind (if available) - ensure numeric comparison
    try:
        wind = float(forecast.get('wind_mph', 0) or 0)
    except (ValueError, TypeError):
        wind = 0
    if wind >= criteria['wind_max']:
        warnings.append(f"High winds ({int(wind)} mph)")
        severity = "high" if wind >= criteria['wind_max'] + 10 else severity

    # Determine suitability
    suitable = len(warnings) == 0

    # Generate recommendation
    if not suitable:
        if severity == "high":
            recommendation = f"We strongly recommend rescheduling. {category} work in these conditions could be unsafe or result in poor quality."
        elif severity == "medium":
            recommendation = f"Working conditions may not be ideal for {category}. Consider choosing a better day if possible."
        else:
            recommendation = f"Minor weather concerns for {category} work. Proceed with caution."
    else:
        recommendation = "Weather conditions look good for outdoor work."

    return {
        "suitable": suitable,
        "warnings": warnings,
        "severity": severity,
        "recommendation": recommendation,
        "forecast": forecast
    }


def find_better_weather_dates(
    weather_data: Dict,
    available_dates: List[str],
    category: str,
    limit: int = 3
) -> List[Dict[str, Any]]:
    """
    Find dates with suitable weather conditions for outdoor work.

    Checks weather forecast for each available date and returns
    dates that meet weather criteria for the project category.

    Args:
        weather_data: Weather response from get_weather Lambda
        available_dates: List of date strings (YYYY-MM-DD)
        category: Project category (e.g., "Decking", "Roofing")
        limit: Maximum number of good dates to return

    Returns:
        List of dicts with date info and weather summary:
        [
            {
                "date": "2024-11-29",
                "day_name": "Saturday",
                "condition": "Clear",
                "high_temp": 45,
                "low_temp": 32,
                "precipitation": 10,
                "suitable": True
            },
            ...
        ]
    """
    better_dates = []

    try:
        weather = weather_data.get('weather', {})
        forecast_list = weather.get('forecast', [])

        if not forecast_list:
            logger.warning("No forecast data available for better date suggestions")
            return []

        # Build forecast lookup by date
        forecast_by_date = {}
        for day in forecast_list:
            date_str = day.get('date')
            if date_str:
                forecast_by_date[date_str] = day

        # Check each available date
        for date_str in available_dates:
            if date_str not in forecast_by_date:
                continue  # No forecast for this date

            forecast = forecast_by_date[date_str]
            assessment = analyze_weather_suitability(forecast, category, date_str)

            if assessment['suitable']:
                # Parse date for day name
                try:
                    from datetime import datetime
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                    day_name = date_obj.strftime("%A")
                    month_day = date_obj.strftime("%b %d")
                except:
                    day_name = date_str
                    month_day = date_str

                better_dates.append({
                    "date": date_str,
                    "day_name": day_name,
                    "month_day": month_day,
                    "condition": forecast.get('condition', 'Unknown'),
                    "high_temp": forecast.get('max_temp_f', 0),
                    "low_temp": forecast.get('min_temp_f', 0),
                    "precipitation": forecast.get('precipitation_probability', 0),
                    "suitable": True
                })

                if len(better_dates) >= limit:
                    break

        logger.info(f"Found {len(better_dates)} suitable weather dates for {category}")
        return better_dates

    except Exception as e:
        logger.error(f"Error finding better weather dates: {e}")
        return []


def add_weather_indicators_to_dates(
    weather_data: Dict,
    available_dates: List[str],
    category: str
) -> List[Dict[str, Any]]:
    """
    Enrich available dates with weather indicators for proactive warnings.

    For each available date, checks weather and adds an indicator:
    - [GOOD] Good weather
    - [WARN] Marginal conditions with warning text
    - [BAD] Poor conditions with warning text

    Args:
        weather_data: Weather response from get_weather Lambda
        available_dates: List of date strings (YYYY-MM-DD)
        category: Project category (e.g., "Decking", "Roofing")

    Returns:
        List of dicts with enriched date info:
        [
            {
                "date": "2024-11-27",
                "day_name": "Wednesday",
                "month_day": "Nov 27",
                "indicator": "[WARN]",
                "suitable": False,
                "severity": "medium",
                "warnings": ["Snow forecasted", "Temperature too cold (high of 32F)"],
                "condition": "Snow",
                "high_temp": 32,
                "low_temp": 20
            },
            ...
        ]
    """
    enriched_dates = []

    try:
        weather = weather_data.get('weather', {})
        forecast_list = weather.get('forecast', [])

        # Build forecast lookup by date
        forecast_by_date = {}
        for day in forecast_list:
            date_str = day.get('date')
            if date_str:
                forecast_by_date[date_str] = day

        for date_str in available_dates:
            # Parse date for display
            try:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                day_name = date_obj.strftime("%A")
                month_day = date_obj.strftime("%b %d")
            except:
                day_name = date_str
                month_day = date_str

            date_info = {
                "date": date_str,
                "day_name": day_name,
                "month_day": month_day,
                "suitable": True,
                "indicator": "[GOOD]",
                "severity": "low",
                "warnings": [],
                "condition": "Unknown",
                "high_temp": None,
                "low_temp": None
            }

            # Check if we have forecast for this date
            if date_str in forecast_by_date:
                forecast = forecast_by_date[date_str]
                assessment = analyze_weather_suitability(forecast, category, date_str)

                date_info["condition"] = forecast.get('condition', 'Unknown')
                date_info["high_temp"] = forecast.get('max_temp_f')
                date_info["low_temp"] = forecast.get('min_temp_f')
                date_info["precipitation"] = forecast.get('precipitation_probability', 0)
                date_info["suitable"] = assessment['suitable']
                date_info["severity"] = assessment['severity']
                date_info["warnings"] = assessment['warnings']

                # Set indicator based on assessment
                if assessment['suitable']:
                    date_info["indicator"] = "[GOOD]"
                elif assessment['severity'] == "high":
                    date_info["indicator"] = "[BAD]"
                else:
                    date_info["indicator"] = "[WARN]"

            enriched_dates.append(date_info)

        # Log summary
        good_count = sum(1 for d in enriched_dates if d['suitable'])
        logger.info(f"Weather enrichment: {good_count}/{len(enriched_dates)} dates suitable for {category}")

        return enriched_dates

    except Exception as e:
        logger.error(f"Error adding weather indicators: {e}")
        # Return basic date info without weather
        return [{"date": d, "suitable": True, "indicator": "", "warnings": []} for d in available_dates]


def extract_location_from_context(workflow_state: Dict) -> Optional[str]:
    """
    Extract location (City, State) from workflow state context

    Args:
        workflow_state: Current workflow state with context

    Returns:
        Location string "City, State" or None
    """
    if not workflow_state:
        return None

    context = workflow_state.get('context', {})

    # Check if location already stored
    if 'location' in context:
        return context['location']

    # Try to build from city/state
    city = context.get('city')
    state = context.get('state')

    if city and state:
        return f"{city}, {state}"

    # Try to extract from address
    address = context.get('address')
    if address and isinstance(address, str):
        # Simple extraction - look for "City, State" pattern
        parts = address.split(',')
        if len(parts) >= 2:
            # Typically: "Street, City, State Zip"
            city = parts[-2].strip()
            state_zip = parts[-1].strip().split()
            if state_zip:
                state = state_zip[0]
                return f"{city}, {state}"

    return None
