#!/usr/bin/env python3
"""
Filter Projects Lambda Function
Filters project lists based on various criteria (urgency, type, status, etc.)
"""

import json
import logging

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def filter_by_priority(projects, priority='HIGH'):
    """Filter projects by priority level"""
    filtered = [
        p for p in projects
        if p.get('priority', '').upper() == priority.upper()
    ]
    logger.info(f"Filtered {len(filtered)} projects with priority={priority}")
    return filtered

def filter_by_status(projects, status):
    """Filter projects by status"""
    filtered = [
        p for p in projects
        if p.get('status', '').lower() == status.lower()
    ]
    logger.info(f"Filtered {len(filtered)} projects with status={status}")
    return filtered

def filter_by_type(projects, project_type):
    """Filter projects by type (outdoor, indoor, etc.)"""
    filtered = [
        p for p in projects
        if project_type.lower() in p.get('type', '').lower() or
           project_type.lower() in p.get('category', '').lower()
    ]
    logger.info(f"Filtered {len(filtered)} projects with type={project_type}")
    return filtered

def find_most_urgent(projects):
    """
    Find the most urgent project based on priority and status

    Priority order:
    1. Status = "Urgent"
    2. Priority = "HIGH"
    3. Status = "Scheduled" (has a date, needs attention)
    4. First project in list
    """
    if not projects:
        return None

    # Check for explicit "Urgent" status
    urgent_status = [p for p in projects if p.get('status', '').lower() == 'urgent']
    if urgent_status:
        logger.info(f"Found urgent project by status: {urgent_status[0].get('project_id')}")
        return urgent_status[0]

    # Check for HIGH priority
    high_priority = [p for p in projects if p.get('priority', '').upper() == 'HIGH']
    if high_priority:
        logger.info(f"Found urgent project by priority: {high_priority[0].get('project_id')}")
        return high_priority[0]

    # Check for Scheduled projects (have dates, need attention)
    scheduled = [p for p in projects if p.get('status', '').lower() == 'scheduled']
    if scheduled:
        logger.info(f"Found scheduled project: {scheduled[0].get('project_id')}")
        return scheduled[0]

    # Default to first project
    logger.info(f"Using first project: {projects[0].get('project_id')}")
    return projects[0]

def lambda_handler(event, context):
    """
    Main handler for project filtering

    Input event structure:
    {
        "projects": [...],
        "filterCriteria": "urgent" | "priority" | "status" | "type",
        "filterValue": "..." (optional, depends on criteria)
    }

    Output:
    {
        "filteredProjects": [...],
        "count": N,
        "mostUrgent": {...} (if criteria is "urgent")
    }
    """
    try:
        logger.info(f"Filter projects invoked with event: {json.dumps(event)[:200]}...")

        # Extract input
        projects = event.get('projects', [])
        filter_criteria = event.get('filterCriteria', 'urgent').lower()
        filter_value = event.get('filterValue', '')

        if not projects:
            logger.warning("No projects provided")
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'filteredProjects': [],
                    'count': 0,
                    'message': 'No projects to filter'
                })
            }

        logger.info(f"Filtering {len(projects)} projects by {filter_criteria}")

        # Apply filter based on criteria
        if filter_criteria == 'urgent':
            most_urgent = find_most_urgent(projects)
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'mostUrgent': most_urgent,
                    'found': most_urgent is not None
                })
            }

        elif filter_criteria == 'priority':
            priority = filter_value or 'HIGH'
            filtered = filter_by_priority(projects, priority)
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'filteredProjects': filtered,
                    'count': len(filtered)
                })
            }

        elif filter_criteria == 'status':
            status = filter_value or 'Pending'
            filtered = filter_by_status(projects, status)
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'filteredProjects': filtered,
                    'count': len(filtered)
                })
            }

        elif filter_criteria == 'type':
            project_type = filter_value or 'outdoor'
            filtered = filter_by_type(projects, project_type)
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'filteredProjects': filtered,
                    'count': len(filtered)
                })
            }

        else:
            logger.warning(f"Unknown filter criteria: {filter_criteria}")
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'filteredProjects': projects,
                    'count': len(projects),
                    'message': f'Unknown criteria {filter_criteria}, returning all'
                })
            }

    except Exception as e:
        logger.error(f"Error filtering projects: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'filteredProjects': [],
                'count': 0
            })
        }
