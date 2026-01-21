"""
Intelligent Workflow State Management
Uses DynamoDB to persist workflow state across conversation turns
NO HARDCODING - State is fully dynamic and context-aware
"""
import boto3
import time
import logging
from typing import Dict, Any, Optional
from decimal import Decimal

logger = logging.getLogger()

# DynamoDB client singleton
_dynamodb = None


def get_dynamodb():
    """Get or create DynamoDB resource"""
    global _dynamodb
    if _dynamodb is None:
        _dynamodb = boto3.resource('dynamodb')
    return _dynamodb


class WorkflowStateManager:
    """
    Manages workflow state in DynamoDB with intelligent context retention

    State Structure:
    {
        'session_id': 'session-123',
        'workflow_type': 'schedule_appointment',
        'current_stage': 'awaiting_time_selection',
        'context': {
            'project_id': '7751748',
            'date': '2025-11-27',
            'available_dates': ['2025-11-27', '2025-11-28'],
            'available_times': ['09:00 AM', '10:00 AM']
        },
        'viewed_projects': [
            {'project_id': '7751741', 'category': 'Decking', 'status': 'Ready To Schedule', 'viewed_at': 1234567880},
            {'project_id': '7751748', 'category': 'Storm Door', 'status': 'Ready To Schedule', 'viewed_at': 1234567890}
        ],
        'project_mapping': {
            '7751741': {'category': 'Decking', 'status': 'Ready To Schedule'},
            '7751748': {'category': 'Storm Door', 'status': 'Ready To Schedule'}
        },
        'conversation_summary': 'User wants to schedule project 7751748 for Nov 27',
        'last_action': 'showed_time_slots',
        'timestamp': 1234567890,
        'ttl': 1234567890
    }
    """

    def __init__(self, table_name: str = 'pf-workflow-states-dev'):
        self.dynamodb = get_dynamodb()
        self.table = self.dynamodb.Table(table_name)
        self.state_ttl = 3600  # 1 hour

    def get_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get workflow state for session
        Returns None if no active workflow
        """
        try:
            response = self.table.get_item(Key={'session_id': session_id})

            if 'Item' not in response:
                logger.info(f"No workflow state found for session {session_id}")
                return None

            state = response['Item']

            # Convert Decimal to int/float for JSON serialization
            state = self._convert_decimals(state)

            logger.info(f"[STATE] Loaded workflow state: type={state.get('workflow_type')}, stage={state.get('current_stage')}")
            return state

        except Exception as e:
            logger.error(f"Error loading workflow state: {e}")
            return None

    def save_state(self, session_id: str, state: Dict[str, Any]) -> bool:
        """
        Save workflow state to DynamoDB
        Automatically adds timestamp and TTL
        """
        try:
            current_time = int(time.time())

            item = {
                'session_id': session_id,
                'workflow_type': state.get('workflow_type', 'unknown'),
                'current_stage': state.get('current_stage', 'start'),
                'context': state.get('context', {}),
                'viewed_projects': state.get('viewed_projects', []),
                'project_mapping': state.get('project_mapping', {}),
                'conversation_summary': state.get('conversation_summary', ''),
                'last_action': state.get('last_action', ''),
                'timestamp': current_time,
                'ttl': current_time + self.state_ttl
            }

            self.table.put_item(Item=item)

            viewed_count = len(item.get('viewed_projects', []))
            logger.info(f"[SAVE] Saved workflow state: session={session_id}, type={item['workflow_type']}, stage={item['current_stage']}, viewed_projects={viewed_count}")
            return True

        except Exception as e:
            logger.error(f"Error saving workflow state: {e}")
            return False

    def update_context(self, session_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update specific fields in workflow context without replacing entire state
        """
        try:
            state = self.get_state(session_id)

            if not state:
                logger.warning(f"Cannot update context - no state found for {session_id}")
                return False

            # Merge updates into existing context
            context = state.get('context', {})
            context.update(updates)
            state['context'] = context

            return self.save_state(session_id, state)

        except Exception as e:
            logger.error(f"Error updating workflow context: {e}")
            return False

    def clear_state(self, session_id: str) -> bool:
        """
        Clear workflow state when workflow completes or is cancelled.
        WARNING: This deletes EVERYTHING including project_mapping and viewed_projects.
        Use reset_workflow_state() instead if you want to preserve memory.
        """
        try:
            self.table.delete_item(Key={'session_id': session_id})
            logger.info(f"[CLEAR]  Cleared workflow state for session {session_id}")
            return True

        except Exception as e:
            logger.error(f"Error clearing workflow state: {e}")
            return False

    def reset_workflow_state(self, session_id: str) -> bool:
        """
        Reset workflow state while PRESERVING memory (project_mapping, viewed_projects, last_action).

        Use this after completing an action (scheduling, canceling, etc.) to allow
        the user to continue with other projects without losing context.

        Preserves:
            - project_mapping (ordinal -> project_id mapping from last list)
            - viewed_projects (history of projects user has looked at)
            - context.last_project_id (most recently referenced project)
            - last_action (what was just completed)

        Clears:
            - workflow_type (ready for new workflow)
            - current_stage (reset to initial)
            - conversation_summary
            - pending_confirmation
        """
        try:
            state = self.get_state(session_id)
            if not state:
                logger.info(f"[RESET] No state to reset for session {session_id}")
                return True

            # Preserve memory fields
            preserved = {
                'project_mapping': state.get('project_mapping', {}),
                'viewed_projects': state.get('viewed_projects', []),
                'last_action': state.get('last_action', ''),
            }

            # Preserve last_project_id from context if available
            context = state.get('context', {})
            last_project_id = context.get('last_project_id', '')

            # Create fresh state with preserved memory
            new_state = {
                'workflow_type': None,
                'current_stage': None,
                'context': {
                    'last_project_id': last_project_id
                },
                'project_mapping': preserved['project_mapping'],
                'viewed_projects': preserved['viewed_projects'],
                'last_action': preserved['last_action'],
            }

            success = self.save_state(session_id, new_state)

            if success:
                logger.info(f"[RESET] Reset workflow state for {session_id}, preserved {len(preserved['project_mapping'])} project mappings, {len(preserved['viewed_projects'])} viewed projects")

            return success

        except Exception as e:
            logger.error(f"Error resetting workflow state: {e}")
            return False

    def add_viewed_project(self, session_id: str, project_info: Dict[str, Any]) -> bool:
        """
        Add a project to the viewed_projects history.
        If project already exists in history, update its viewed_at timestamp.
        Keeps the 10 most recently viewed projects.

        Args:
            session_id: Session ID
            project_info: Dict with project_id, category, status, city, state, etc.
        """
        try:
            state = self.get_state(session_id)
            if not state:
                # Create minimal state just to track viewed projects
                state = {
                    'workflow_type': 'browsing',
                    'current_stage': 'viewing',
                    'context': {},
                    'viewed_projects': [],
                    'project_mapping': {}
                }

            viewed_projects = state.get('viewed_projects', [])
            project_id = str(project_info.get('project_id', ''))

            if not project_id:
                logger.warning("[VIEWED] Cannot add project without project_id")
                return False

            # Remove existing entry for this project (we'll add updated one)
            viewed_projects = [p for p in viewed_projects if str(p.get('project_id', '')) != project_id]

            # Add new entry with current timestamp
            viewed_entry = {
                'project_id': project_id,
                'category': project_info.get('category', ''),
                'status': project_info.get('status', ''),
                'city': project_info.get('city', ''),
                'state': project_info.get('state', ''),
                'address': project_info.get('address', ''),
                'viewed_at': int(time.time())
            }
            viewed_projects.append(viewed_entry)

            # Keep only the 10 most recent (sorted by viewed_at)
            viewed_projects = sorted(viewed_projects, key=lambda x: x.get('viewed_at', 0), reverse=True)[:10]

            state['viewed_projects'] = viewed_projects

            logger.info(f"[VIEWED] Added project {project_id} ({project_info.get('category', 'unknown')}) to history. Total: {len(viewed_projects)}")
            return self.save_state(session_id, state)

        except Exception as e:
            logger.error(f"Error adding viewed project: {e}")
            return False

    def switch_project_context(self, session_id: str, new_project_info: Dict[str, Any],
                                preserve_workflow: bool = False) -> bool:
        """
        Switch to a new project while preserving viewed_projects history.
        This is used when user mentions a different project.

        Args:
            session_id: Session ID
            new_project_info: Dict with the new project's details
            preserve_workflow: If True, keep workflow_type and current_stage.
                              If False, reset to 'browsing' state.
        """
        try:
            state = self.get_state(session_id)
            if not state:
                state = {
                    'workflow_type': 'browsing',
                    'current_stage': 'viewing',
                    'context': {},
                    'viewed_projects': [],
                    'project_mapping': {}
                }

            # First, add current project to viewed history (if exists)
            current_context = state.get('context', {})
            current_project_id = current_context.get('project_id')
            if current_project_id:
                # Add current project to history before switching
                self.add_viewed_project(session_id, current_context)
                # Reload state after adding (it was modified)
                state = self.get_state(session_id) or state

            # Update context with new project
            new_context = {
                'project_id': str(new_project_info.get('project_id', '')),
                'category': new_project_info.get('category', ''),
                'status': new_project_info.get('status', ''),
                'city': new_project_info.get('city', ''),
                'state': new_project_info.get('state', ''),
                'address': new_project_info.get('address', ''),
            }

            # Preserve project_mapping if it exists
            project_mapping = state.get('project_mapping', {})
            viewed_projects = state.get('viewed_projects', [])

            if preserve_workflow:
                # Keep existing workflow
                state['context'] = new_context
            else:
                # Reset workflow state but preserve history
                state = {
                    'workflow_type': 'browsing',
                    'current_stage': 'viewing',
                    'context': new_context,
                    'viewed_projects': viewed_projects,
                    'project_mapping': project_mapping,
                    'conversation_summary': f"User switched to project {new_context.get('project_id')}",
                    'last_action': 'context_switch'
                }

            logger.info(f"[SWITCH] Context switched to project {new_context.get('project_id')} ({new_context.get('category')})")
            return self.save_state(session_id, state)

        except Exception as e:
            logger.error(f"Error switching project context: {e}")
            return False

    def get_viewed_projects(self, session_id: str) -> list:
        """
        Get list of recently viewed projects for this session.
        Returns empty list if no state exists.
        """
        state = self.get_state(session_id)
        if not state:
            return []
        return state.get('viewed_projects', [])

    def find_project_in_history(self, session_id: str, search_term: str) -> Optional[Dict[str, Any]]:
        """
        Find a project in viewed history by category, status, or partial match.
        Useful for resolving references like "the Decking project" or "the first one".

        Args:
            session_id: Session ID
            search_term: Category name, status, or reference like "first", "last"

        Returns:
            Project info dict if found, None otherwise
        """
        viewed_projects = self.get_viewed_projects(session_id)
        if not viewed_projects:
            return None

        search_lower = search_term.lower()

        # Handle ordinal references
        if search_lower in ['first', '1st', 'first one']:
            # Return the first project viewed (oldest in sorted list by viewed_at)
            sorted_by_time = sorted(viewed_projects, key=lambda x: x.get('viewed_at', 0))
            return sorted_by_time[0] if sorted_by_time else None

        if search_lower in ['last', 'latest', 'last one', 'previous', 'other one']:
            # Return the second most recent (the one before current)
            sorted_by_time = sorted(viewed_projects, key=lambda x: x.get('viewed_at', 0), reverse=True)
            return sorted_by_time[1] if len(sorted_by_time) > 1 else (sorted_by_time[0] if sorted_by_time else None)

        if search_lower in ['second', '2nd', 'second one']:
            sorted_by_time = sorted(viewed_projects, key=lambda x: x.get('viewed_at', 0))
            return sorted_by_time[1] if len(sorted_by_time) > 1 else None

        # Search by category
        for project in viewed_projects:
            category = (project.get('category', '') or '').lower()
            if search_lower in category or category in search_lower:
                return project

        # Search by status
        for project in viewed_projects:
            status = (project.get('status', '') or '').lower()
            if search_lower in status:
                return project

        return None

    def find_project_by_partial_id(self, session_id: str, partial_id: str) -> Optional[Dict[str, Any]]:
        """
        Find a project by partial ID match (e.g., "ending in 717" matches "7751717").
        Searches both viewed_projects and project_mapping.

        Args:
            session_id: Session ID
            partial_id: The partial ID to match (e.g., "717", "60000")

        Returns:
            Project info dict if exactly one match found, None otherwise
        """
        if not partial_id or not partial_id.isdigit():
            return None

        state = self.get_state(session_id)
        if not state:
            return None

        matches = []

        # Search in viewed_projects (has full project info)
        viewed_projects = state.get('viewed_projects', [])
        for project in viewed_projects:
            project_id = str(project.get('project_id', ''))
            if project_id.endswith(partial_id) or project_id.startswith(partial_id):
                matches.append(project)

        # If no matches in viewed_projects, search project_mapping
        if not matches:
            project_mapping = state.get('project_mapping', {})
            for project_id, project_info in project_mapping.items():
                if str(project_id).endswith(partial_id) or str(project_id).startswith(partial_id):
                    # Convert mapping entry to full project info format
                    matches.append({
                        'project_id': project_id,
                        'category': project_info.get('category', ''),
                        'status': project_info.get('status', ''),
                        'city': project_info.get('city', ''),
                        'state': project_info.get('state', ''),
                        'address': project_info.get('address', '')
                    })

        if len(matches) == 1:
            logger.info(f"[PARTIAL_ID] Found unique match for partial ID '{partial_id}': {matches[0].get('project_id')}")
            return matches[0]
        elif len(matches) > 1:
            # Multiple matches - return None (ambiguous)
            logger.warning(f"[PARTIAL_ID] Multiple matches for partial ID '{partial_id}': {[m.get('project_id') for m in matches]}")
            return None
        else:
            logger.info(f"[PARTIAL_ID] No matches found for partial ID '{partial_id}'")
            return None

    def update_project_mapping(self, session_id: str, project_mapping: Dict[str, Any]) -> bool:
        """
        Update the project_mapping with all customer's projects.
        This is called after fetching customer projects list.
        """
        try:
            state = self.get_state(session_id)
            if not state:
                state = {
                    'workflow_type': 'browsing',
                    'current_stage': 'viewing',
                    'context': {},
                    'viewed_projects': [],
                    'project_mapping': {}
                }

            state['project_mapping'] = project_mapping
            logger.info(f"[MAPPING] Updated project mapping with {len(project_mapping)} projects")
            return self.save_state(session_id, state)

        except Exception as e:
            logger.error(f"Error updating project mapping: {e}")
            return False

    def _convert_decimals(self, obj):
        """
        Convert DynamoDB Decimal types to int/float for JSON serialization
        """
        if isinstance(obj, list):
            return [self._convert_decimals(item) for item in obj]
        elif isinstance(obj, dict):
            return {key: self._convert_decimals(value) for key, value in obj.items()}
        elif isinstance(obj, Decimal):
            if obj % 1 == 0:
                return int(obj)
            else:
                return float(obj)
        else:
            return obj


# Singleton instance
_state_manager = None


def get_state_manager() -> WorkflowStateManager:
    """Get or create workflow state manager singleton"""
    global _state_manager
    if _state_manager is None:
        from config import get_config
        config = get_config()
        _state_manager = WorkflowStateManager(config.workflow_state_table)
    return _state_manager
