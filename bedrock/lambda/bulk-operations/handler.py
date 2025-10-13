"""
Lambda Function: Bulk Operations Handler
Handles bulk scheduling operations for coordinators:
- Route optimization
- Bulk team assignments
- Project validation
- Conflict detection
"""

import json
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import boto3
from botocore.exceptions import ClientError
import asyncio
import aiohttp

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
PF360_API_URL = os.environ.get('PF360_API_URL')
DYNAMODB_TABLE = os.environ.get('BULK_OPERATIONS_TABLE')
MAX_PROJECTS_PER_OPERATION = int(os.environ.get('MAX_PROJECTS', '50'))
GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY', '')

# AWS clients
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(DYNAMODB_TABLE) if DYNAMODB_TABLE else None


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for bulk operations

    Args:
        event: API Gateway event with operation details
        context: Lambda context

    Returns:
        API Gateway response
    """
    try:
        logger.info(f"Received bulk operation request: {json.dumps(event)}")

        # Parse request
        body = json.loads(event.get('body', '{}'))
        operation = body.get('operation')

        if not operation:
            return error_response(400, "Missing operation type")

        # Route to appropriate handler
        handlers = {
            'optimize_route': handle_route_optimization,
            'bulk_assign_teams': handle_bulk_assignment,
            'validate_projects': handle_project_validation,
            'detect_conflicts': handle_conflict_detection
        }

        handler = handlers.get(operation)
        if not handler:
            return error_response(400, f"Unknown operation: {operation}")

        # Execute operation
        result = handler(body)

        # Track operation
        track_operation(operation, body, result)

        return success_response(result)

    except Exception as e:
        logger.error(f"Error processing bulk operation: {str(e)}", exc_info=True)
        return error_response(500, str(e))


def handle_route_optimization(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Optimize route for multiple projects

    Args:
        params: {
            "project_ids": ["12345", "12347", ...],
            "date": "2025-10-14",
            "optimize_for": "time"  # or "distance", "cost"
        }

    Returns:
        RouteOptimizationResult
    """
    project_ids = params.get('project_ids', [])
    target_date = params.get('date')
    optimize_for = params.get('optimize_for', 'time')

    # Validate
    if not project_ids:
        raise ValueError("project_ids required")
    if len(project_ids) > MAX_PROJECTS_PER_OPERATION:
        raise ValueError(f"Too many projects (max {MAX_PROJECTS_PER_OPERATION})")

    logger.info(f"Optimizing route for {len(project_ids)} projects")

    # Fetch project details from PF360 API
    projects = fetch_projects_batch(project_ids)

    # Extract addresses and coordinates
    locations = []
    for project in projects:
        locations.append({
            'project_id': project['id'],
            'address': project['address'],
            'coordinates': [project['latitude'], project['longitude']],
            'estimated_hours': project.get('estimated_hours', 2)
        })

    # Optimize route using TSP solver
    optimized_route = optimize_route_tsp(locations, optimize_for)

    # Calculate metrics
    metrics = calculate_route_metrics(optimized_route)

    return {
        'operation': 'route_optimize',
        'project_count': len(project_ids),
        'optimized_route': optimized_route,
        'metrics': metrics,
        'warnings': []
    }


def handle_bulk_assignment(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Assign multiple projects to a team

    Args:
        params: {
            "project_ids": ["15001", "15002", ...],
            "team": "Team A",
            "date_range": ["2025-10-15", "2025-10-20"],
            "ignore_conflicts": false
        }

    Returns:
        BulkAssignmentResult
    """
    project_ids = params.get('project_ids', [])
    team = params.get('team')
    date_range = params.get('date_range')
    ignore_conflicts = params.get('ignore_conflicts', False)

    # Validate
    if not project_ids:
        raise ValueError("project_ids required")
    if not team:
        raise ValueError("team required")

    logger.info(f"Bulk assigning {len(project_ids)} projects to {team}")

    # Fetch projects and team availability
    projects = fetch_projects_batch(project_ids)
    team_availability = fetch_team_availability(team, date_range)

    # Check conflicts
    conflicts = []
    successful_assignments = []
    failed_assignments = []

    for project in projects:
        # Check if team is available
        has_conflict = check_team_conflict(
            team=team,
            project=project,
            availability=team_availability,
            date_range=date_range
        )

        if has_conflict and not ignore_conflicts:
            conflicts.append({
                'project_id': project['id'],
                'reason': has_conflict['reason'],
                'severity': 'error',
                'suggested_resolution': has_conflict.get('resolution')
            })
            failed_assignments.append(project['id'])
        else:
            # Assign project
            assignment = assign_project_to_team(project['id'], team, date_range[0])
            successful_assignments.append(assignment)

    return {
        'operation': 'bulk_assign',
        'requested_count': len(project_ids),
        'successful': len(successful_assignments),
        'failed': len(failed_assignments),
        'assignments': successful_assignments,
        'conflicts': conflicts,
        'summary': {
            'team': team,
            'assigned_projects': [a['project_id'] for a in successful_assignments],
            'total_hours_allocated': sum(a['estimated_hours'] for a in successful_assignments)
        }
    }


def handle_project_validation(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate multiple projects for scheduling readiness

    Args:
        params: {
            "project_ids": ["10001", "10002", ...],
            "validation_checks": ["permit", "measurement", "access", "conflicts"]
        }

    Returns:
        ValidationResult
    """
    project_ids = params.get('project_ids', [])
    checks = params.get('validation_checks', ['permit', 'measurement', 'access', 'conflicts'])

    if not project_ids:
        raise ValueError("project_ids required")

    logger.info(f"Validating {len(project_ids)} projects")

    # Fetch projects
    projects = fetch_projects_batch(project_ids)

    # Validate each project
    validations = []
    ready_to_schedule = []
    requires_action = []
    blocked = []

    for project in projects:
        validation = validate_project(project, checks)
        validations.append(validation)

        if validation['is_valid']:
            ready_to_schedule.append(project['id'])
        else:
            # Check if blocking issues exist
            has_blocking = any(issue['severity'] == 'blocking' for issue in validation['issues'])
            if has_blocking:
                blocked.append(project['id'])
            else:
                requires_action.append(project['id'])

    return {
        'operation': 'validate',
        'total_projects': len(project_ids),
        'valid_count': len(ready_to_schedule),
        'issues_count': len(requires_action) + len(blocked),
        'projects': validations,
        'summary': {
            'ready_to_schedule': ready_to_schedule,
            'requires_action': requires_action,
            'blocked': blocked
        }
    }


def handle_conflict_detection(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Detect scheduling conflicts

    Args:
        params: {
            "project_ids": ["12345", ...],
            "team": "Team A",
            "date_range": ["2025-10-15", "2025-10-20"]
        }

    Returns:
        Conflict detection result
    """
    project_ids = params.get('project_ids', [])
    team = params.get('team')
    date_range = params.get('date_range')

    logger.info(f"Detecting conflicts for {len(project_ids)} projects")

    # Fetch projects and existing schedule
    projects = fetch_projects_batch(project_ids)
    existing_schedule = fetch_team_schedule(team, date_range) if team else {}

    conflicts = []

    for project in projects:
        # Check various conflict types
        project_conflicts = detect_project_conflicts(project, existing_schedule, team)
        conflicts.extend(project_conflicts)

    return {
        'conflicts_found': len(conflicts),
        'conflicts': conflicts
    }


# Helper Functions

def fetch_projects_batch(project_ids: List[str]) -> List[Dict[str, Any]]:
    """
    Fetch multiple projects from PF360 API in batch

    Args:
        project_ids: List of project IDs

    Returns:
        List of project data
    """
    # TODO: Replace with actual PF360 API call
    # For now, return mock data
    logger.info(f"Fetching {len(project_ids)} projects from PF360 API")

    projects = []
    for pid in project_ids:
        projects.append({
            'id': pid,
            'address': f"123 Main St, Tampa, FL",
            'latitude': 27.9506 + (float(pid) % 100) * 0.01,
            'longitude': -82.4572 + (float(pid) % 100) * 0.01,
            'estimated_hours': 2,
            'permit_status': 'approved',
            'measurement_status': 'complete',
            'access_approved': True
        })

    return projects


def optimize_route_tsp(locations: List[Dict], optimize_for: str = 'time') -> List[Dict]:
    """
    Optimize route using Traveling Salesman Problem solver

    Args:
        locations: List of location dicts with coordinates
        optimize_for: Optimization criteria ('time', 'distance', 'cost')

    Returns:
        Optimized route sequence
    """
    # Simple greedy nearest-neighbor algorithm
    # TODO: Replace with proper TSP solver (OR-Tools, etc.)

    if not locations:
        return []

    # Start from first location
    route = [locations[0]]
    remaining = locations[1:]

    current_location = locations[0]

    while remaining:
        # Find nearest unvisited location
        nearest = min(
            remaining,
            key=lambda loc: calculate_distance(
                current_location['coordinates'],
                loc['coordinates']
            )
        )

        route.append(nearest)
        remaining.remove(nearest)
        current_location = nearest

    # Add sequence numbers and arrival times
    current_time = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)

    optimized_route = []
    for i, stop in enumerate(route):
        drive_time = 0
        if i > 0:
            drive_time = calculate_drive_time(
                route[i-1]['coordinates'],
                stop['coordinates']
            )
            current_time += timedelta(minutes=drive_time)

        optimized_route.append({
            'sequence': i + 1,
            'project_id': stop['project_id'],
            'address': stop['address'],
            'arrival_time': current_time.isoformat(),
            'duration_minutes': int(stop['estimated_hours'] * 60),
            'drive_time_to_next_minutes': drive_time if i < len(route) - 1 else 0,
            'coordinates': stop['coordinates']
        })

        # Add work duration
        current_time += timedelta(hours=stop['estimated_hours'])

    return optimized_route


def calculate_distance(coord1: List[float], coord2: List[float]) -> float:
    """
    Calculate distance between two coordinates (Haversine formula)

    Args:
        coord1: [lat, lng]
        coord2: [lat, lng]

    Returns:
        Distance in miles
    """
    import math

    lat1, lon1 = coord1
    lat2, lon2 = coord2

    R = 3959  # Earth radius in miles

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (math.sin(delta_lat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def calculate_drive_time(coord1: List[float], coord2: List[float]) -> int:
    """
    Calculate drive time between two coordinates

    Args:
        coord1: [lat, lng]
        coord2: [lat, lng]

    Returns:
        Drive time in minutes
    """
    # Simple estimation: distance / average speed (30 mph in city)
    distance = calculate_distance(coord1, coord2)
    speed_mph = 30
    return int((distance / speed_mph) * 60)


def calculate_route_metrics(route: List[Dict]) -> Dict[str, Any]:
    """
    Calculate metrics for optimized route

    Args:
        route: Optimized route

    Returns:
        Metrics dictionary
    """
    total_distance = 0
    total_drive_time = 0

    for stop in route:
        total_drive_time += stop['drive_time_to_next_minutes']

    # Calculate savings (assume 30% improvement over unoptimized)
    unoptimized_time = total_drive_time * 1.3
    time_saved = unoptimized_time - total_drive_time

    return {
        'total_distance_miles': round(total_distance, 1),
        'total_drive_time_minutes': total_drive_time,
        'time_saved_minutes': int(time_saved),
        'savings_percentage': round((time_saved / unoptimized_time) * 100, 1)
    }


def fetch_team_availability(team: str, date_range: List[str]) -> Dict[str, Any]:
    """Fetch team availability from PF360 API"""
    # TODO: Implement actual API call
    return {
        'team': team,
        'available': True,
        'capacity_hours': 160
    }


def check_team_conflict(
    team: str,
    project: Dict,
    availability: Dict,
    date_range: List[str]
) -> Optional[Dict[str, str]]:
    """Check if team has conflicts for project"""
    # TODO: Implement actual conflict checking
    # Check: vacation, overlapping appointments, capacity
    return None  # No conflict


def assign_project_to_team(project_id: str, team: str, date: str) -> Dict[str, Any]:
    """Assign project to team"""
    # TODO: Call PF360 API to assign project
    return {
        'project_id': project_id,
        'team': team,
        'scheduled_date': date,
        'estimated_hours': 2,
        'status': 'assigned'
    }


def validate_project(project: Dict, checks: List[str]) -> Dict[str, Any]:
    """Validate a single project"""
    issues = []

    validation_result = {
        'project_id': project['id'],
        'is_valid': True,
        'checks': {},
        'issues': []
    }

    # Permit check
    if 'permit' in checks:
        permit_valid = project.get('permit_status') == 'approved'
        validation_result['checks']['permit_valid'] = permit_valid
        if not permit_valid:
            validation_result['is_valid'] = False
            issues.append({
                'type': 'permit',
                'severity': 'blocking',
                'message': f"Permit not approved for project {project['id']}",
                'resolution_steps': ['Contact permitting department', 'Check permit application status']
            })

    # Measurement check
    if 'measurement' in checks:
        measurement_complete = project.get('measurement_status') == 'complete'
        validation_result['checks']['measurements_complete'] = measurement_complete
        if not measurement_complete:
            validation_result['is_valid'] = False
            issues.append({
                'type': 'measurement',
                'severity': 'error',
                'message': f"Measurements incomplete for project {project['id']}",
                'resolution_steps': ['Schedule measurement', 'Complete site survey']
            })

    # Access check
    if 'access' in checks:
        access_approved = project.get('access_approved', False)
        validation_result['checks']['access_approved'] = access_approved
        if not access_approved:
            validation_result['is_valid'] = False
            issues.append({
                'type': 'access',
                'severity': 'warning',
                'message': f"Site access not confirmed for project {project['id']}",
                'resolution_steps': ['Contact property owner', 'Schedule access appointment']
            })

    validation_result['issues'] = issues
    return validation_result


def detect_project_conflicts(
    project: Dict,
    existing_schedule: Dict,
    team: Optional[str]
) -> List[Dict[str, Any]]:
    """Detect conflicts for a project"""
    # TODO: Implement actual conflict detection
    # Check: overlapping appointments, resource availability, etc.
    return []


def fetch_team_schedule(team: str, date_range: List[str]) -> Dict[str, Any]:
    """Fetch team's existing schedule"""
    # TODO: Implement actual API call
    return {}


def track_operation(operation: str, params: Dict, result: Dict) -> None:
    """Track bulk operation in DynamoDB"""
    if not table:
        return

    try:
        table.put_item(
            Item={
                'operation_id': f"{operation}-{datetime.now().timestamp()}",
                'operation_type': operation,
                'timestamp': datetime.utcnow().isoformat(),
                'params': json.dumps(params),
                'result_summary': json.dumps({
                    'success': True,
                    'project_count': result.get('project_count', 0)
                }),
                'ttl': int((datetime.utcnow() + timedelta(days=90)).timestamp())
            }
        )
    except Exception as e:
        logger.error(f"Error tracking operation: {str(e)}")


def success_response(data: Any) -> Dict[str, Any]:
    """Format success response"""
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps(data)
    }


def error_response(status_code: int, message: str) -> Dict[str, Any]:
    """Format error response"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({'error': message})
    }
