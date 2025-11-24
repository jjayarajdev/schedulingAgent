"""
Conversation History Management using DynamoDB
Replaces Redis/ElastiCache for serverless session storage
"""
import json
import time
import logging
from typing import List, Dict, Optional
import boto3
from botocore.exceptions import ClientError

from config import get_config

logger = logging.getLogger()


class ConversationManager:
    """Manages conversation history in DynamoDB with TTL"""

    def __init__(self):
        self.config = get_config()
        self._dynamodb = None
        self._table = None

    @property
    def table(self):
        """Lazy-load DynamoDB table (reused across Lambda invocations)"""
        if self._table is None:
            self._dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
            self._table = self._dynamodb.Table('pf-sessions-dev')
            logger.info(f"DynamoDB table connected: pf-sessions-dev")
        return self._table

    def get_conversation_history(self, session_id: str, limit: Optional[int] = None) -> List[Dict]:
        """
        Get conversation history for a session

        Args:
            session_id: Session identifier
            limit: Maximum number of messages to return (default: from config)

        Returns:
            List of message dictionaries with role, content, timestamp, metadata
        """
        if limit is None:
            limit = self.config.max_history_messages

        try:
            response = self.table.get_item(
                Key={'session_id': session_id}
            )

            if 'Item' not in response:
                logger.debug(f"No history found for session {session_id}")
                return []

            session_data = response['Item']
            messages = json.loads(session_data.get('messages', '[]'))

            # Return most recent messages up to limit
            limited_messages = messages[-limit:] if limit > 0 else messages

            logger.info(f"Retrieved {len(limited_messages)} messages for session {session_id}")
            return limited_messages

        except ClientError as e:
            logger.error(f"DynamoDB error getting conversation history: {e}")
            return []  # Graceful degradation
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error for session {session_id}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error getting conversation history: {e}")
            return []

    def add_to_conversation_history(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict] = None
    ):
        """
        Add a message to conversation history

        Args:
            session_id: Session identifier
            role: Message role (user/assistant)
            content: Message content
            metadata: Optional metadata (action, intent, performance, etc.)
        """
        try:
            timestamp = int(time.time() * 1000)
            ttl = int(time.time()) + self.config.session_timeout  # TTL in seconds

            # Get existing session data
            try:
                response = self.table.get_item(
                    Key={'session_id': session_id}
                )
                if 'Item' in response:
                    session_data = response['Item']
                    messages = json.loads(session_data.get('messages', '[]'))
                    created_at = session_data.get('created_at', timestamp)
                else:
                    messages = []
                    created_at = timestamp
            except Exception:
                messages = []
                created_at = timestamp

            # Add new message
            message = {
                'role': role,
                'content': content,
                'timestamp': timestamp,
                'metadata': metadata or {}
            }

            messages.append(message)

            # Keep only recent messages to prevent unbounded growth
            if len(messages) > self.config.max_history_messages:
                messages = messages[-self.config.max_history_messages:]
                logger.debug(f"Trimmed history to {self.config.max_history_messages} messages")

            # Save to DynamoDB with TTL
            self.table.put_item(
                Item={
                    'session_id': session_id,
                    'messages': json.dumps(messages),
                    'created_at': created_at,
                    'last_activity': timestamp,
                    'ttl': ttl,
                    'message_count': len(messages)
                }
            )

            logger.debug(f"Added {role} message to session {session_id} (total: {len(messages)})")

        except ClientError as e:
            logger.error(f"DynamoDB error adding to conversation history: {e}")
            # Don't fail the request if DynamoDB is unavailable
        except Exception as e:
            logger.error(f"Unexpected error adding to conversation: {e}")

    def cleanup_old_sessions(self):
        """
        Cleanup sessions that are inactive beyond threshold
        Note: DynamoDB TTL handles most cleanup automatically
        """
        # DynamoDB TTL handles this automatically
        # This method exists for compatibility but is a no-op
        logger.debug("Session cleanup delegated to DynamoDB TTL")

    def get_session_count(self) -> int:
        """Get count of active sessions"""
        try:
            response = self.table.scan(
                Select='COUNT'
            )
            return response.get('Count', 0)
        except ClientError as e:
            logger.error(f"DynamoDB error counting sessions: {e}")
            return 0
        except Exception as e:
            logger.error(f"Unexpected error counting sessions: {e}")
            return 0

    def delete_session(self, session_id: str):
        """Delete a specific session"""
        try:
            self.table.delete_item(
                Key={'session_id': session_id}
            )
            logger.info(f"Deleted session {session_id}")
        except ClientError as e:
            logger.error(f"DynamoDB error deleting session: {e}")
        except Exception as e:
            logger.error(f"Unexpected error deleting session: {e}")


# Singleton instance
_conversation_manager = None

def get_conversation_manager() -> ConversationManager:
    """Get or create ConversationManager singleton"""
    global _conversation_manager
    if _conversation_manager is None:
        _conversation_manager = ConversationManager()
    return _conversation_manager
