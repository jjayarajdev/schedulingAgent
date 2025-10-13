# TCPA Compliance Service

Python module for handling TCPA 2025 compliance requirements for multi-channel opt-outs.

## TCPA 2025 Requirements

Effective **April 11, 2025**, new TCPA regulations require:

1. **10-Day Processing**: Opt-out requests must be honored within 10 business days
2. **Multi-Channel Opt-Out**: Opt-out from ANY channel (SMS, email, voice, web) applies to ALL electronic channels
3. **Universal Opt-Out**: Customer can opt out via any method, not just reply
4. **Audit Trail**: 4-year retention of all opt-out records
5. **Single Clarification**: Can ask ONE clarifying question if intent is unclear
6. **No Conditions**: Cannot condition opt-out on providing reasons or additional info

## Features

✅ Multi-channel opt-out tracking
✅ 10 business day deadline calculation
✅ Automatic channel blocking (SMS opt-out = voice blocked too)
✅ 4-year audit trail retention
✅ Pre-send consent validation
✅ Opt-in (resubscribe) support
✅ Pending opt-out monitoring
✅ DynamoDB-backed persistence

## Usage

### Initialize Service

```python
from tcpa_service import TCPAComplianceService, OptOutMethod, Channel

service = TCPAComplianceService(
    region='us-east-1',
    consent_table_name='scheduling-agent-sms-consent-dev',
    opt_out_tracking_table_name='scheduling-agent-opt-out-tracking-dev'
)
```

### Check Consent Before Sending

```python
can_send, reason = service.check_consent_before_send(
    phone_number='+14255551234',
    channel=Channel.SMS
)

if can_send:
    # Safe to send message
    send_sms(phone_number, message)
else:
    logger.warning(f"Cannot send: {reason}")
```

### Record Opt-Out

```python
# Customer opts out via SMS
result = service.record_opt_out(
    phone_number='+14255551234',
    method=OptOutMethod.SMS,
    original_message='STOP',
    customer_id='CUST123'
)

print(f"Opt-out pending until: {result['deadline']}")
print(f"Applies to channels: {result['applies_to_channels']}")
# Output: ['sms', 'voice'] - automatically blocks both
```

### Record Opt-In (Resubscribe)

```python
result = service.record_opt_in(
    phone_number='+14255551234',
    method=OptOutMethod.SMS,
    customer_id='CUST123',
    consent_text='Customer replied START to resubscribe'
)
```

### Get Consent Status

```python
status = service.get_consent_status('+14255551234')

print(f"Status: {status['status']}")
print(f"Can send: {status['can_send']}")
print(f"Channels blocked: {status['applies_to_channels']}")
```

### Monitor Pending Opt-Outs

```python
# Get opt-outs approaching deadline (within 5 days)
pending = service.get_pending_opt_outs(days_until_deadline=5)

for record in pending:
    phone = record['phone_number']
    deadline = record['opt_out_deadline']
    print(f"Alert: {phone} opt-out deadline {deadline}")
```

## Data Models

### Consent Table Schema

```python
{
    'phone_number': str,              # Partition key
    'consent_status': str,            # 'opted_in', 'opted_out', 'pending_opt_out'
    'opt_out_method': str,            # 'sms', 'email', 'voice', 'web', 'manual'
    'opt_out_requested_at': str,      # ISO datetime
    'opt_out_deadline': str,          # ISO datetime (10 business days)
    'applies_to_channels': List[str], # ['sms', 'voice', 'email']
    'original_message': str,          # Original opt-out message
    'customer_id': str,               # Optional customer ID
    'notes': str,                     # Optional admin notes
    'updated_at': str,                # Last update timestamp
    'ttl': int                        # Expiry (4 years from now)
}
```

### Opt-Out Tracking Table Schema

```python
{
    'tracking_id': str,          # Partition key: phone#timestamp
    'timestamp': str,            # Sort key: ISO datetime
    'phone_number': str,         # GSI partition key
    'method': str,               # How opted out
    'status': str,               # 'pending_processing', 'opted_out', 'opted_in'
    'deadline': str,             # Processing deadline
    'original_request': str,     # Original message/request
    'customer_id': str,          # Optional
    'business_days_to_honor': int # Usually 10
}
```

## Opt-Out Keywords

### Automatic Opt-Out

These keywords trigger immediate opt-out:
- STOP
- QUIT
- END
- REVOKE
- OPT OUT / OPTOUT
- CANCEL
- UNSUBSCRIBE

### Automatic Opt-In

These keywords trigger resubscription:
- START
- UNSTOP
- YES
- SUBSCRIBE

## Business Day Calculation

TCPA requires honoring opt-outs within **10 business days** (not calendar days).

**Example:**
- Opt-out received: Monday, Oct 15
- Deadline calculation: Skip weekends
- Deadline: Friday, Oct 26 (10 business days later)

```python
from datetime import datetime
from tcpa_service import TCPAComplianceService

start = datetime(2025, 10, 15)  # Monday
deadline = TCPAComplianceService._calculate_opt_out_deadline(
    start_date=start,
    business_days=10
)
print(deadline)  # Friday, Oct 26
```

## Multi-Channel Enforcement

**Per TCPA 2025**: Opt-out from ANY channel applies to ALL channels.

**Example:**
1. Customer replies "STOP" to SMS
2. System automatically blocks:
   - SMS messages ❌
   - Voice calls ❌
   - (Email handled separately per CAN-SPAM)

```python
service.record_opt_out(
    phone_number='+14255551234',
    method=OptOutMethod.SMS,
    original_message='STOP'
)

# Check SMS (blocked)
can_send_sms, _ = service.check_consent_before_send(
    phone_number='+14255551234',
    channel=Channel.SMS
)
print(can_send_sms)  # False

# Check Voice (also blocked!)
can_send_voice, _ = service.check_consent_before_send(
    phone_number='+14255551234',
    channel=Channel.VOICE
)
print(can_send_voice)  # False
```

## Testing

### Unit Tests

```bash
cd lambda/tcpa-compliance
python -m pytest tests/ -v
```

### Integration Tests

```bash
# Test with real DynamoDB
python -m pytest tests/integration/ -v --dynamodb-endpoint http://localhost:8000
```

## Monitoring

### Daily Opt-Out Report

```python
# Run as Lambda scheduled event (daily)
def lambda_handler(event, context):
    service = TCPAComplianceService(...)

    # Get opt-outs approaching deadline
    pending = service.get_pending_opt_outs(days_until_deadline=3)

    if pending:
        # Send alert to ops team
        for record in pending:
            alert_ops_team(record)
```

### CloudWatch Metrics

Custom metrics to publish:
- `OptOutsReceived` - Daily opt-out count
- `OptOutsPending` - Current pending count
- `OptOutsExpired` - Deadline violations (should be 0!)
- `ConsentChecks` - Pre-send validation count

## Compliance Checklist

- [ ] All opt-outs processed within 10 business days
- [ ] Multi-channel blocking enabled (SMS → Voice)
- [ ] 4-year audit trail retention configured
- [ ] Opt-out confirmation messages sent
- [ ] No conditions on opt-out (no "reply why" required)
- [ ] Web form opt-out available
- [ ] Email opt-out link included
- [ ] Voice call opt-out option (IVR or agent)
- [ ] Monitoring for deadline violations
- [ ] Legal review completed

## Cost Estimate

### DynamoDB Costs

**Consent Table:**
- Writes: 100/day opt-outs = $0.12/month
- Reads: 10,000/day checks = $0.25/month
- Storage: 10,000 records @ 1KB = $0.025/month

**Tracking Table:**
- Writes: 100/day events = $0.12/month
- Storage: Historical records = $0.05/month

**Total**: ~$0.55/month for opt-out management

## Version History

- **v1.0.0** (2025-10-13): Initial implementation with TCPA 2025 compliance
