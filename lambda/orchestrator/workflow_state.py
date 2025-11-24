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

            logger.info(f"📦 Loaded workflow state: type={state.get('workflow_type')}, stage={state.get('current_stage')}")
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
                'conversation_summary': state.get('conversation_summary', ''),
                'last_action': state.get('last_action', ''),
                'timestamp': current_time,
                'ttl': current_time + self.state_ttl
            }

            self.table.put_item(Item=item)

            logger.info(f"💾 Saved workflow state: session={session_id}, type={item['workflow_type']}, stage={item['current_stage']}")
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
        Clear workflow state when workflow completes or is cancelled
        """
        try:
            self.table.delete_item(Key={'session_id': session_id})
            logger.info(f"🗑️  Cleared workflow state for session {session_id}")
            return True

        except Exception as e:
            logger.error(f"Error clearing workflow state: {e}")
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
