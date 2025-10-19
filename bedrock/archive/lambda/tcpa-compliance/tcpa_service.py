"""
TCPA Compliance Service
Handles multi-channel opt-out requirements per TCPA 2025 regulations
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple, List
from enum import Enum
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class OptOutMethod(str, Enum):
    """Opt-out method enum"""
    SMS = "sms"
    EMAIL = "email"
    VOICE = "voice"
    WEB = "web"
    MANUAL = "manual"


class Channel(str, Enum):
    """Communication channel enum"""
    SMS = "sms"
    EMAIL = "email"
    VOICE = "voice"


class ConsentStatus(str, Enum):
    """Consent status enum"""
    OPTED_IN = "opted_in"
    OPTED_OUT = "opted_out"
    PENDING_OPT_OUT = "pending_opt_out"
    EXPIRED = "expired"


class TCPAComplianceService:
    """
    TCPA 2025 Compliance Service

    Key Requirements:
    1. Multi-channel opt-out: SMS opt-out applies to voice calls too
    2. 10-day deadline: Opt-out must be honored within 10 business days
    3. Universal opt-out: Any channel opt-out stops all channels
    4. Audit trail: 4-year retention of opt-out records
    5. Clarification allowed: Can ask clarifying questions once
    """

    def __init__(
        self,
        region: str = 'us-east-1',
        consent_table_name: Optional[str] = None,
        opt_out_tracking_table_name: Optional[str] = None
    ):
        """
        Initialize TCPA Compliance Service

        Args:
            region: AWS region
            consent_table_name: DynamoDB consent table name
            opt_out_tracking_table_name: DynamoDB opt-out tracking table name
        """
        self.dynamodb = boto3.resource('dynamodb', region_name=region)
        self.consent_table = self.dynamodb.Table(consent_table_name)
        self.tracking_table = self.dynamodb.Table(opt_out_tracking_table_name)

    def check_consent_before_send(
        self,
        phone_number: str,
        channel: Channel = Channel.SMS
    ) -> Tuple[bool, str]:
        """
        Check if message can be sent to customer (pre-send validation)

        Args:
            phone_number: Customer phone number
            channel: Communication channel

        Returns:
            Tuple of (can_send: bool, reason: str)
        """
        try:
            # Get consent record
            response = self.consent_table.get_item(
                Key={'phone_number': phone_number}
            )

            if 'Item' not in response:
                # No record = no explicit consent (should have been obtained during signup)
                logger.warning(f"No consent record for {phone_number}")
                return False, "No consent record found"

            consent = response['Item']
            status = consent.get('consent_status')

            # Check if opted out
            if status == ConsentStatus.OPTED_OUT:
                opt_out_date = consent.get('opt_out_requested_at')
                return False, f"Customer opted out on {opt_out_date}"

            # Check if opt-out is pending (within 10-day window)
            if status == ConsentStatus.PENDING_OPT_OUT:
                deadline = datetime.fromisoformat(consent['opt_out_deadline'])
                if datetime.utcnow() >= deadline:
                    # Deadline passed - mark as opted out
                    self._finalize_opt_out(phone_number)
                    return False, "Opt-out deadline reached"

                return False, f"Opt-out pending (deadline: {deadline.date()})"

            # Check if channel is included in opt-out
            opted_out_channels = consent.get('applies_to_channels', [])
            if channel.value in opted_out_channels:
                return False, f"Customer opted out of {channel.value} channel"

            # All checks passed
            return True, "Consent verified"

        except Exception as e:
            logger.error(f"Error checking consent: {str(e)}", exc_info=True)
            # Fail closed - don't send if we can't verify consent
            return False, f"Error checking consent: {str(e)}"

    def record_opt_out(
        self,
        phone_number: str,
        method: OptOutMethod,
        original_message: Optional[str] = None,
        customer_id: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Record opt-out request (any channel)

        Per TCPA 2025:
        - Must honor within 10 business days
        - Applies to all channels (SMS opt-out = voice opt-out too)
        - Must keep audit trail for 4 years

        Args:
            phone_number: Customer phone number
            method: How customer opted out
            original_message: Original opt-out message
            customer_id: Optional customer ID
            notes: Optional admin notes

        Returns:
            Opt-out record
        """
        try:
            now = datetime.utcnow()
            deadline = self._calculate_opt_out_deadline(now, business_days=10)

            # Per TCPA 2025: Opt-out from any channel applies to all electronic channels
            applies_to_channels = [Channel.SMS.value, Channel.VOICE.value]

            # Update consent table
            consent_record = {
                'phone_number': phone_number,
                'consent_status': ConsentStatus.PENDING_OPT_OUT.value,
                'opt_out_method': method.value,
                'opt_out_requested_at': now.isoformat(),
                'opt_out_deadline': deadline.isoformat(),
                'applies_to_channels': applies_to_channels,
                'original_message': original_message,
                'customer_id': customer_id,
                'notes': notes,
                'updated_at': now.isoformat(),
                'ttl': int((now + timedelta(days=1460)).timestamp())  # 4 years retention
            }

            self.consent_table.put_item(Item=consent_record)

            # Track in opt-out tracking table
            tracking_id = f"{phone_number}#{now.isoformat()}"
            tracking_record = {
                'tracking_id': tracking_id,
                'timestamp': now.isoformat(),
                'phone_number': phone_number,
                'method': method.value,
                'status': 'pending_processing',
                'deadline': deadline.isoformat(),
                'original_request': original_message,
                'customer_id': customer_id,
                'business_days_to_honor': 10
            }

            self.tracking_table.put_item(Item=tracking_record)

            logger.info(f"Opt-out recorded for {phone_number} via {method.value}")

            return {
                'phone_number': phone_number,
                'status': 'pending',
                'deadline': deadline.isoformat(),
                'tracking_id': tracking_id,
                'applies_to_channels': applies_to_channels
            }

        except Exception as e:
            logger.error(f"Error recording opt-out: {str(e)}", exc_info=True)
            raise

    def record_opt_in(
        self,
        phone_number: str,
        method: OptOutMethod,
        customer_id: Optional[str] = None,
        consent_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Record opt-in (resubscribe)

        Args:
            phone_number: Customer phone number
            method: How customer opted in
            customer_id: Optional customer ID
            consent_text: Consent text/disclosure

        Returns:
            Opt-in record
        """
        try:
            now = datetime.utcnow()

            # Update consent table
            consent_record = {
                'phone_number': phone_number,
                'consent_status': ConsentStatus.OPTED_IN.value,
                'opt_in_method': method.value,
                'opt_in_at': now.isoformat(),
                'customer_id': customer_id,
                'consent_text': consent_text,
                'applies_to_channels': [Channel.SMS.value, Channel.VOICE.value],
                'updated_at': now.isoformat(),
                'ttl': int((now + timedelta(days=1460)).timestamp())
            }

            self.consent_table.put_item(Item=consent_record)

            # Track in opt-out tracking table
            tracking_id = f"{phone_number}#{now.isoformat()}"
            self.tracking_table.put_item(
                Item={
                    'tracking_id': tracking_id,
                    'timestamp': now.isoformat(),
                    'phone_number': phone_number,
                    'method': method.value,
                    'status': 'opted_in',
                    'customer_id': customer_id
                }
            )

            logger.info(f"Opt-in recorded for {phone_number}")

            return {
                'phone_number': phone_number,
                'status': 'opted_in',
                'timestamp': now.isoformat(),
                'tracking_id': tracking_id
            }

        except Exception as e:
            logger.error(f"Error recording opt-in: {str(e)}", exc_info=True)
            raise

    def get_consent_status(self, phone_number: str) -> Dict[str, Any]:
        """
        Get current consent status for phone number

        Args:
            phone_number: Customer phone number

        Returns:
            Consent status dictionary
        """
        try:
            response = self.consent_table.get_item(
                Key={'phone_number': phone_number}
            )

            if 'Item' not in response:
                return {
                    'phone_number': phone_number,
                    'status': 'no_record',
                    'can_send': False
                }

            consent = response['Item']
            status = consent.get('consent_status')

            return {
                'phone_number': phone_number,
                'status': status,
                'can_send': status == ConsentStatus.OPTED_IN.value,
                'opt_out_method': consent.get('opt_out_method'),
                'opt_out_date': consent.get('opt_out_requested_at'),
                'opt_out_deadline': consent.get('opt_out_deadline'),
                'applies_to_channels': consent.get('applies_to_channels', [])
            }

        except Exception as e:
            logger.error(f"Error getting consent status: {str(e)}", exc_info=True)
            return {
                'phone_number': phone_number,
                'status': 'error',
                'can_send': False,
                'error': str(e)
            }

    def get_pending_opt_outs(self, days_until_deadline: int = 5) -> List[Dict[str, Any]]:
        """
        Get opt-outs approaching deadline

        Args:
            days_until_deadline: Number of days before deadline to alert

        Returns:
            List of pending opt-out records
        """
        try:
            cutoff_date = datetime.utcnow() + timedelta(days=days_until_deadline)

            # Scan for pending opt-outs (in production, use GSI with deadline)
            response = self.consent_table.scan(
                FilterExpression='consent_status = :status AND opt_out_deadline <= :cutoff',
                ExpressionAttributeValues={
                    ':status': ConsentStatus.PENDING_OPT_OUT.value,
                    ':cutoff': cutoff_date.isoformat()
                }
            )

            return response.get('Items', [])

        except Exception as e:
            logger.error(f"Error getting pending opt-outs: {str(e)}", exc_info=True)
            return []

    def _finalize_opt_out(self, phone_number: str) -> None:
        """
        Finalize opt-out after deadline

        Args:
            phone_number: Customer phone number
        """
        try:
            self.consent_table.update_item(
                Key={'phone_number': phone_number},
                UpdateExpression='SET consent_status = :status, finalized_at = :now',
                ExpressionAttributeValues={
                    ':status': ConsentStatus.OPTED_OUT.value,
                    ':now': datetime.utcnow().isoformat()
                }
            )

            logger.info(f"Finalized opt-out for {phone_number}")

        except Exception as e:
            logger.error(f"Error finalizing opt-out: {str(e)}", exc_info=True)

    @staticmethod
    def _calculate_opt_out_deadline(
        start_date: datetime,
        business_days: int = 10
    ) -> datetime:
        """
        Calculate opt-out deadline (business days)

        TCPA 2025 requires processing within 10 business days

        Args:
            start_date: Start date
            business_days: Number of business days

        Returns:
            Deadline datetime
        """
        current_date = start_date
        days_added = 0

        while days_added < business_days:
            current_date += timedelta(days=1)
            # Skip weekends (0 = Monday, 6 = Sunday)
            if current_date.weekday() < 5:
                days_added += 1

        return current_date

    @staticmethod
    def is_opt_out_keyword(message: str) -> bool:
        """
        Check if message is an opt-out keyword

        Args:
            message: Message text

        Returns:
            True if opt-out keyword detected
        """
        opt_out_keywords = [
            'STOP', 'QUIT', 'END', 'REVOKE',
            'OPT OUT', 'OPTOUT', 'CANCEL', 'UNSUBSCRIBE'
        ]

        message_upper = message.upper().strip()
        return any(keyword in message_upper for keyword in opt_out_keywords)

    @staticmethod
    def is_opt_in_keyword(message: str) -> bool:
        """
        Check if message is an opt-in keyword

        Args:
            message: Message text

        Returns:
            True if opt-in keyword detected
        """
        opt_in_keywords = ['START', 'UNSTOP', 'YES', 'SUBSCRIBE']

        message_upper = message.upper().strip()
        return any(keyword in message_upper for keyword in opt_in_keywords)
