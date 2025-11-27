#!/usr/bin/env python3
"""
Weather Evaluator Lambda Function
Evaluates weather conditions for project suitability
"""

import json
import logging
from typing import Dict, List, Any
from datetime import datetime

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Project type weather requirements
WEATHER_REQUIREMENTS = {
    'outdoor': {
        'min_temp_f': 40,
        'max_temp_f': 95,
        'max_wind_mph': 25,
        'conditions_avoid': ['rain', 'snow', 'thunderstorm', 'heavy'],
        'min_visibility_miles': 5
    },
    'roofing': {
        'min_temp_f': 45,
        'max_temp_f': 90,
        'max_wind_mph': 15,  # Stricter for roofing
        'conditions_avoid': ['rain', 'snow', 'thunderstorm', 'heavy', 'fog'],
        'min_visibility_miles': 8
    },
    'painting': {
        'min_temp_f': 50,
        'max_temp_f': 85,
        'max_wind_mph': 20,
        'max_humidity': 85,
        'conditions_avoid': ['rain', 'snow', 'heavy']
    },
    'flooring': {
        'min_temp_f': 45,
        'max_temp_f': 90,
        'max_wind_mph': 30,  # Less sensitive to wind
        'conditions_avoid': ['rain', 'snow', 'thunderstorm']
    },
    'deck': {
        'min_temp_f': 40,
        'max_temp_f': 95,
        'max_wind_mph': 20,
        'conditions_avoid': ['rain', 'snow', 'heavy']
    }
}

def is_weather_suitable(weather_data: Dict, project_category: str) -> Dict[str, Any]:
    """
    Evaluate if weather conditions are suitable for a project

    Args:
        weather_data: Weather forecast data from wttr.in or similar
        project_category: Category of project (flooring, roofing, deck, etc.)

    Returns:
        Dict with suitability assessment and reasoning
    """
    try:
        # Normalize project category
        category_lower = project_category.lower()

        # Determine requirements based on project type
        if 'roof' in category_lower:
            requirements = WEATHER_REQUIREMENTS['roofing']
            project_type = 'roofing'
        elif 'paint' in category_lower:
            requirements = WEATHER_REQUIREMENTS['painting']
            project_type = 'painting'
        elif 'floor' in category_lower or 'flooring' in category_lower:
            requirements = WEATHER_REQUIREMENTS['flooring']
            project_type = 'flooring'
        elif 'deck' in category_lower:
            requirements = WEATHER_REQUIREMENTS['deck']
            project_type = 'deck'
        else:
            # Default to general outdoor requirements
            requirements = WEATHER_REQUIREMENTS['outdoor']
            project_type = 'outdoor'

        logger.info(f"Evaluating weather for {project_type} project with requirements: {requirements}")

        # Extract weather info
        current = weather_data.get('current', {})
        temp_f = float(current.get('temp_f', 0))
        condition = current.get('condition', '').lower()
        humidity = int(current.get('humidity', 0))
        wind_mph = float(current.get('wind_mph', 0))

        # Evaluation results
        issues = []
        warnings = []

        # Temperature check
        if temp_f < requirements['min_temp_f']:
            issues.append(f"Temperature too low ({temp_f}F < {requirements['min_temp_f']}F minimum)")
        elif temp_f > requirements['max_temp_f']:
            issues.append(f"Temperature too high ({temp_f}F > {requirements['max_temp_f']}F maximum)")
        elif temp_f < requirements['min_temp_f'] + 5:
            warnings.append(f"Temperature is borderline low ({temp_f}F)")
        elif temp_f > requirements['max_temp_f'] - 5:
            warnings.append(f"Temperature is borderline high ({temp_f}F)")

        # Wind check
        if wind_mph > requirements['max_wind_mph']:
            issues.append(f"Wind too strong ({wind_mph} mph > {requirements['max_wind_mph']} mph maximum)")
        elif wind_mph > requirements['max_wind_mph'] - 5:
            warnings.append(f"Wind is borderline strong ({wind_mph} mph)")

        # Humidity check (if applicable)
        if 'max_humidity' in requirements and humidity > requirements['max_humidity']:
            issues.append(f"Humidity too high ({humidity}% > {requirements['max_humidity']}% maximum)")

        # Condition check
        for avoid_condition in requirements['conditions_avoid']:
            if avoid_condition in condition:
                issues.append(f"Unsuitable weather condition: {condition}")
                break

        # Determine suitability
        is_suitable = len(issues) == 0
        confidence_score = 100 if is_suitable and len(warnings) == 0 else (
            80 if is_suitable and len(warnings) > 0 else
            50 if len(issues) == 1 else
            0
        )

        result = {
            'suitable': is_suitable,
            'confidence_score': confidence_score,
            'project_type': project_type,
            'weather_summary': {
                'temperature': f"{temp_f}F",
                'condition': condition,
                'wind': f"{wind_mph} mph",
                'humidity': f"{humidity}%"
            },
            'issues': issues,
            'warnings': warnings,
            'recommendation': _generate_recommendation(is_suitable, issues, warnings, temp_f, condition)
        }

        logger.info(f"Weather evaluation result: {result}")
        return result

    except Exception as e:
        logger.error(f"Error evaluating weather: {e}", exc_info=True)
        return {
            'suitable': False,
            'confidence_score': 0,
            'error': str(e),
            'recommendation': 'Unable to evaluate weather conditions'
        }

def _generate_recommendation(is_suitable: bool, issues: List[str], warnings: List[str],
                            temp_f: float, condition: str) -> str:
    """Generate human-readable recommendation"""
    if is_suitable and len(warnings) == 0:
        return f"Perfect conditions! {temp_f}F and {condition}. Ideal for outdoor work."
    elif is_suitable and len(warnings) > 0:
        return f"Acceptable conditions with minor concerns: {'; '.join(warnings)}. Proceed with caution."
    else:
        return f"Not recommended: {'; '.join(issues)}. Consider rescheduling."

def find_suitable_dates(weather_forecast: List[Dict], project_category: str,
                       num_days: int = 7) -> List[Dict]:
    """
    Find suitable dates from weather forecast

    Args:
        weather_forecast: List of daily forecasts
        project_category: Category of project
        num_days: Number of days to check

    Returns:
        List of suitable dates with evaluation
    """
    suitable_dates = []

    for i, day_forecast in enumerate(weather_forecast[:num_days]):
        # Create weather data dict for this day
        weather_data = {
            'current': {
                'temp_f': day_forecast.get('avg_temp_f', day_forecast.get('max_temp_f', 70)),
                'condition': day_forecast.get('condition', 'clear'),
                'humidity': day_forecast.get('humidity', 50),
                'wind_mph': day_forecast.get('wind_mph', 5)
            }
        }

        evaluation = is_weather_suitable(weather_data, project_category)

        if evaluation['suitable']:
            suitable_dates.append({
                'date': day_forecast.get('date'),
                'day_index': i,
                'evaluation': evaluation,
                'priority': evaluation['confidence_score']
            })

    # Sort by confidence score
    suitable_dates.sort(key=lambda x: x['priority'], reverse=True)

    return suitable_dates

def lambda_handler(event, context):
    """
    Main Lambda handler for weather evaluation

    Input event structure:
    {
        "weather": {...},  # Weather data from wttr.in API
        "project": {
            "category": "Flooring",
            "type": "outdoor"
        },
        "evaluation_type": "current" | "forecast"  # Evaluate current or find suitable dates
    }

    Output:
    {
        "statusCode": 200,
        "body": {
            "suitable": true/false,
            "confidence_score": 0-100,
            "recommendation": "...",
            ...
        }
    }
    """
    try:
        logger.info(f"Weather evaluator invoked with event: {json.dumps(event)[:300]}...")

        # Extract input
        weather_data = event.get('weather', {})
        project = event.get('project', {})
        project_category = project.get('category', 'outdoor')
        evaluation_type = event.get('evaluation_type', 'current')

        if not weather_data:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'No weather data provided',
                    'suitable': False
                })
            }

        # Evaluate based on type
        if evaluation_type == 'forecast':
            # Find suitable dates from forecast
            weather_forecast = weather_data.get('forecast', [])
            num_days = event.get('num_days', 7)

            suitable_dates = find_suitable_dates(weather_forecast, project_category, num_days)

            return {
                'statusCode': 200,
                'body': json.dumps({
                    'evaluation_type': 'forecast',
                    'suitable_dates': suitable_dates,
                    'total_suitable_days': len(suitable_dates),
                    'project_category': project_category
                })
            }
        else:
            # Evaluate current/specific date weather
            evaluation = is_weather_suitable(weather_data, project_category)

            return {
                'statusCode': 200,
                'body': json.dumps(evaluation)
            }

    except Exception as e:
        logger.error(f"Error in weather evaluator: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'suitable': False,
                'recommendation': 'Unable to evaluate weather conditions'
            })
        }

# For local testing
if __name__ == "__main__":
    # Test with sample weather data
    test_event = {
        "weather": {
            "current": {
                "temp_f": 75,
                "condition": "clear",
                "humidity": 60,
                "wind_mph": 8
            }
        },
        "project": {
            "category": "Flooring",
            "type": "outdoor"
        },
        "evaluation_type": "current"
    }

    response = lambda_handler(test_event, None)
    print(json.dumps(response, indent=2))
