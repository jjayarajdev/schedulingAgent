"""
VAPI Dashboard - Daily Report Generator Lambda
Generates detailed call analysis reports for each tenant

Triggered daily by EventBridge at 6:00 AM UTC
Analyzes previous day's calls and stores report in DynamoDB
"""
import json
import os
import re
import urllib.request
import urllib.error
import boto3
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from decimal import Decimal

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Configuration
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
REGION = os.environ.get('AWS_REGION', 'us-east-1')
TENANTS_TABLE = os.environ.get('TENANTS_TABLE', f'pf-syn-vapi-dashboard-tenants-{ENVIRONMENT}')
REPORTS_TABLE = os.environ.get('REPORTS_TABLE', f'pf-syn-vapi-dashboard-reports-{ENVIRONMENT}')
VAPI_API_KEY = os.environ.get('VAPI_API_KEY', '')

# DynamoDB
dynamodb = boto3.resource('dynamodb', region_name=REGION)
tenants_table = dynamodb.Table(TENANTS_TABLE)
reports_table = dynamodb.Table(REPORTS_TABLE)

# VAPI API
VAPI_BASE_URL = 'https://api.vapi.ai'

# Frustration indicators
FRUSTRATION_PHRASES = [
    (r'\b(frustrated|frustrating|annoying|annoyed)\b', 3),
    (r'\b(doesn\'t work|not working|broken)\b', 2),
    (r'\b(terrible|horrible|awful|worst)\b', 3),
    (r'\b(stupid|dumb|useless)\b', 3),
    (r'\b(bye|goodbye|hanging up)\b.*\b(angry|mad|upset)\b', 2),
    (r'\b(wait|waiting|forever|long time)\b', 1),
    (r'\b(repeat|again|said that)\b', 1),
    (r'\b(real person|human|representative|agent)\b', 2),
    (r'\b(can\'t hear|not understand|what\?)\b', 1),
]


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main handler - generates reports for all tenants.
    Can be triggered by:
    - EventBridge schedule (daily)
    - Manual invocation with specific tenant_id and date
    """
    logger.info(f"Report generator started: {json.dumps(event)}")

    # Check for manual invocation parameters
    tenant_id = event.get('tenant_id')
    report_date = event.get('date')  # Format: YYYY-MM-DD

    if report_date:
        target_date = datetime.strptime(report_date, '%Y-%m-%d')
    else:
        # Default: yesterday
        target_date = datetime.utcnow() - timedelta(days=1)

    date_str = target_date.strftime('%Y-%m-%d')

    try:
        if tenant_id:
            # Generate for specific tenant
            tenant = get_tenant(tenant_id)
            if not tenant:
                return {'statusCode': 404, 'body': f'Tenant {tenant_id} not found'}

            report = generate_tenant_report(tenant, target_date)
            store_report(tenant_id, date_str, report)

            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': f'Report generated for {tenant_id}',
                    'date': date_str,
                    'calls_analyzed': report.get('total_calls', 0)
                })
            }
        else:
            # Generate for all tenants
            tenants = get_all_tenants()
            results = []

            for tenant in tenants:
                tid = tenant.get('tenant_id')
                try:
                    report = generate_tenant_report(tenant, target_date)
                    store_report(tid, date_str, report)
                    results.append({
                        'tenant_id': tid,
                        'status': 'success',
                        'calls': report.get('total_calls', 0)
                    })
                except Exception as e:
                    logger.error(f"Error generating report for {tid}: {e}")
                    results.append({
                        'tenant_id': tid,
                        'status': 'error',
                        'error': str(e)
                    })

            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Reports generated',
                    'date': date_str,
                    'results': results
                })
            }

    except Exception as e:
        logger.error(f"Report generation failed: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


def generate_tenant_report(tenant: Dict, target_date: datetime) -> Dict:
    """Generate detailed report for a tenant."""
    tenant_id = tenant.get('tenant_id')
    tenant_name = tenant.get('name', tenant_id)
    phone_number_id = tenant.get('vapi_phone_number_id')

    if not phone_number_id:
        logger.warning(f"Tenant {tenant_id} has no VAPI phone number")
        return {'error': 'No VAPI phone number configured', 'total_calls': 0}

    # Fetch calls for the target date
    start_date = target_date.strftime('%Y-%m-%dT00:00:00Z')
    end_date = target_date.strftime('%Y-%m-%dT23:59:59Z')

    calls = fetch_vapi_calls(phone_number_id, start_date, end_date)

    if not calls:
        logger.info(f"No calls found for {tenant_id} on {target_date.strftime('%Y-%m-%d')}")
        return {
            'total_calls': 0,
            'markdown': generate_empty_report(tenant_name, target_date),
            'metrics': {}
        }

    # Analyze each call
    analyzed_calls = []
    for call in calls:
        analyzed = analyze_call(call)
        analyzed_calls.append(analyzed)

    # Generate metrics
    metrics = calculate_metrics(analyzed_calls)

    # Generate markdown report
    markdown = generate_markdown_report(tenant_name, tenant_id, target_date, analyzed_calls, metrics)

    return {
        'total_calls': len(calls),
        'markdown': markdown,
        'metrics': metrics,
        'calls': analyzed_calls
    }


def analyze_call(call: Dict) -> Dict:
    """Analyze a single call and extract insights."""
    call_id = call.get('id', '')
    status = call.get('status', 'unknown')
    ended_reason = call.get('endedReason', 'unknown')

    # Cost data - handle both old format (cost as dict) and new format (cost as float, costBreakdown as dict)
    cost_value = call.get('cost')
    cost_breakdown_data = call.get('costBreakdown') or {}

    # Calculate duration from startedAt/endedAt timestamps
    duration_seconds = 0
    started_at = call.get('startedAt')
    ended_at = call.get('endedAt')
    if started_at and ended_at:
        try:
            started = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
            ended = datetime.fromisoformat(ended_at.replace('Z', '+00:00'))
            duration_seconds = (ended - started).total_seconds()
        except Exception:
            pass
    # Fallback to durationSeconds if available
    if not duration_seconds:
        duration_seconds = call.get('durationSeconds', 0) or 0
    # Fallback to cost dict totalDuration (older API)
    if not duration_seconds and isinstance(cost_value, dict):
        duration_seconds = cost_value.get('totalDuration', 0) or 0

    # Handle new format: cost is a float, costBreakdown has components
    if isinstance(cost_value, (int, float)):
        total_cost = float(cost_value)
        cost_breakdown = {
            'llm': cost_breakdown_data.get('llm', 0) or 0,
            'stt': cost_breakdown_data.get('stt', 0) or 0,
            'tts': cost_breakdown_data.get('tts', 0) or 0,
            'vapi': cost_breakdown_data.get('vapi', 0) or 0,
            'transport': cost_breakdown_data.get('transport', 0) or 0
        }
    # Handle old format: cost is a dict with all info
    elif isinstance(cost_value, dict):
        cost_breakdown = {
            'llm': cost_value.get('llm', 0) or 0,
            'stt': cost_value.get('stt', 0) or 0,
            'tts': cost_value.get('tts', 0) or 0,
            'vapi': cost_value.get('vapi', 0) or 0,
            'transport': cost_value.get('transport', 0) or 0
        }
        total_cost = sum(cost_breakdown.values())
    else:
        cost_breakdown = {'llm': 0, 'stt': 0, 'tts': 0, 'vapi': 0, 'transport': 0}
        total_cost = 0

    # Analysis data
    analysis = call.get('analysis') or {}
    success = analysis.get('successEvaluation')
    summary = analysis.get('summary', '')

    # Customer info
    customer = call.get('customer') or {}
    customer_number = customer.get('number', 'Unknown')
    # Clean phone number
    if customer_number.startswith('+1'):
        customer_number = customer_number[2:]
    customer_number = re.sub(r'\D', '', customer_number)

    # Transcript and messages
    transcript = call.get('transcript', '')
    messages = call.get('messages', [])

    # Extract customer name from transcript
    customer_name = extract_customer_name(transcript, messages)

    # Analyze frustration
    frustration_score, frustration_indicators = analyze_frustration(transcript, messages)

    # Analyze tool calls
    tool_calls, max_latency = analyze_tool_calls(messages)

    # Determine root cause
    root_cause, recommendations = determine_root_cause(
        ended_reason, success, max_latency, frustration_score, transcript
    )

    # Format duration
    duration_formatted = format_duration(duration_seconds)

    return {
        'call_id': call_id,
        'customer_name': customer_name,
        'customer_number': customer_number,
        'status': status,
        'ended_reason': ended_reason,
        'duration_seconds': duration_seconds,
        'duration_formatted': duration_formatted,
        'success': success,
        'success_display': format_success(success),
        'total_cost': round(total_cost, 4),
        'cost_breakdown': cost_breakdown,
        'summary': summary,
        'transcript': transcript,
        'frustration_score': frustration_score,
        'frustration_indicators': frustration_indicators,
        'tool_calls': tool_calls,
        'tool_call_count': len(tool_calls),
        'max_latency': max_latency,
        'root_cause': root_cause,
        'recommendations': recommendations,
        'created_at': call.get('createdAt', ''),
        'started_at': call.get('startedAt', ''),
        'ended_at': call.get('endedAt', '')
    }


def extract_customer_name(transcript: str, messages: List) -> str:
    """Extract customer name from transcript or messages."""
    # Try to find name in greeting pattern
    patterns = [
        r"Hello,?\s+([A-Z][a-z]+)\.",
        r"Hi,?\s+([A-Z][a-z]+)\.",
        r"Good (?:morning|afternoon|evening),?\s+([A-Z][a-z]+)\.",
    ]

    for pattern in patterns:
        match = re.search(pattern, transcript)
        if match:
            return match.group(1)

    # Try from messages
    for msg in messages:
        if msg.get('role') == 'assistant':
            content = msg.get('content', '') or msg.get('message', '')
            for pattern in patterns:
                match = re.search(pattern, content)
                if match:
                    return match.group(1)

    return "Unknown"


def analyze_frustration(transcript: str, messages: List) -> Tuple[int, List[str]]:
    """Analyze user frustration from transcript."""
    score = 0
    indicators = []

    # Combine transcript and user messages
    user_text = transcript
    for msg in messages:
        if msg.get('role') == 'user':
            content = msg.get('content', '') or msg.get('message', '')
            user_text += ' ' + content

    user_text = user_text.lower()

    for pattern, points in FRUSTRATION_PHRASES:
        if re.search(pattern, user_text, re.IGNORECASE):
            score += points
            # Extract the indicator phrase
            match = re.search(pattern, user_text, re.IGNORECASE)
            if match:
                indicators.append(match.group(0).strip())

    # Cap at 10
    score = min(score, 10)

    return score, indicators


def analyze_tool_calls(messages: List) -> Tuple[List[Dict], float]:
    """Extract tool calls and latencies from messages."""
    tool_calls = []
    max_latency = 0.0

    for i, msg in enumerate(messages):
        if msg.get('role') == 'tool_calls' or msg.get('toolCalls'):
            tool_data = msg.get('toolCalls', [msg]) if msg.get('toolCalls') else [msg]

            for tc in tool_data:
                func = tc.get('function', {})
                name = func.get('name', tc.get('name', 'unknown'))

                # Calculate latency - time between tool call and result
                call_time = msg.get('secondsFromStart', 0)

                # Find corresponding tool result
                result_time = call_time
                result_preview = ''
                for j in range(i+1, min(i+5, len(messages))):
                    result_msg = messages[j]
                    if result_msg.get('role') == 'tool_result' or result_msg.get('toolCallId'):
                        result_time = result_msg.get('secondsFromStart', call_time)
                        result_content = result_msg.get('result', '') or result_msg.get('content', '')
                        if isinstance(result_content, str):
                            result_preview = result_content[:50]
                        break

                latency = result_time - call_time
                max_latency = max(max_latency, latency)

                tool_calls.append({
                    'time': call_time,
                    'action': name,
                    'latency': round(latency, 1),
                    'result_preview': result_preview
                })

    return tool_calls, round(max_latency, 1)


def determine_root_cause(ended_reason: str, success: Any, max_latency: float,
                         frustration_score: int, transcript: str) -> Tuple[str, str]:
    """Determine root cause and recommendations."""

    # Check for specific end reasons
    if 'silence-timed-out' in ended_reason:
        return "Silence timeout - user disengaged", "Review if AI responses are engaging"

    if 'customer-did-not-give-microphone-permission' in ended_reason:
        return "Microphone permission denied", "N/A - user issue"

    if 'twilio-reported-customer-misdialed' in ended_reason:
        return "Customer misdialed", "N/A"

    if 'assistant-error' in ended_reason or 'pipeline-error' in ended_reason:
        return "System error", "Investigate VAPI/Lambda logs"

    # Check latency
    if max_latency > 15:
        return "Very slow API response", "Investigate ProjectForce API performance"
    elif max_latency > 10:
        return "Slow API response (>10s)", "Optimize API response times"

    # Check frustration
    if frustration_score >= 5:
        return "Customer frustration", "Review call flow and responses"

    # Check success
    if success == 'false' or success == False:
        if 'missing parameter' in transcript.lower():
            return "Missing parameters in API call", "Check parameter extraction logic"
        return "Task not completed", "Review conversation flow"

    if success == 'true' or success == True:
        return "Normal operation", "N/A"

    return "Unknown", "Review call details"


def calculate_metrics(calls: List[Dict]) -> Dict:
    """Calculate aggregate metrics from analyzed calls."""
    if not calls:
        return {}

    total = len(calls)
    successful = sum(1 for c in calls if c['success'] == 'true' or c['success'] == True)
    failed = sum(1 for c in calls if c['success'] == 'false' or c['success'] == False)
    high_frustration = sum(1 for c in calls if c['frustration_score'] >= 3)

    total_duration = sum(c['duration_seconds'] for c in calls)
    total_cost = sum(c['total_cost'] for c in calls)

    avg_duration = total_duration / total if total > 0 else 0
    avg_cost = total_cost / total if total > 0 else 0
    success_rate = (successful / total * 100) if total > 0 else 0

    # End reason breakdown
    end_reasons = {}
    for c in calls:
        reason = c['ended_reason']
        end_reasons[reason] = end_reasons.get(reason, 0) + 1

    # Aggregate cost breakdown for chargeback
    cost_breakdown_totals = {
        'llm': sum(c['cost_breakdown']['llm'] for c in calls),
        'stt': sum(c['cost_breakdown']['stt'] for c in calls),
        'tts': sum(c['cost_breakdown']['tts'] for c in calls),
        'vapi': sum(c['cost_breakdown']['vapi'] for c in calls),
        'transport': sum(c['cost_breakdown']['transport'] for c in calls)
    }

    return {
        'total_calls': total,
        'successful': successful,
        'failed': failed,
        'success_rate': round(success_rate, 1),
        'high_frustration': high_frustration,
        'total_duration': round(total_duration, 1),
        'avg_duration': round(avg_duration, 1),
        'avg_duration_formatted': format_duration(avg_duration),
        'total_cost': round(total_cost, 4),
        'avg_cost': round(avg_cost, 4),
        'cost_breakdown': cost_breakdown_totals,
        'end_reasons': end_reasons
    }


def generate_markdown_report(tenant_name: str, tenant_id: str, target_date: datetime,
                             calls: List[Dict], metrics: Dict) -> str:
    """Generate the full markdown report."""
    date_str = target_date.strftime('%B %d, %Y')
    date_short = target_date.strftime('%Y-%m-%d')

    md = f"""# VAPI Call Analysis Report

**Generated:** {datetime.utcnow().strftime('%B %d, %Y at %H:%M UTC')}
**Client:** {tenant_name} ({tenant_id})
**Total Calls:** {metrics.get('total_calls', 0)}
**Analysis Period:** {date_str}

## Table of Contents

- [Executive Summary](#executive-summary)
- [Key Metrics](#key-metrics)
- [Cost Analytics (Chargeback)](#cost-analytics)
- [Critical Issues](#critical-issues)
- [Calls by Customer](#calls-by-customer)
"""

    # Add TOC entries for each call
    for i, call in enumerate(calls, 1):
        name = call['customer_name']
        phone = call['customer_number']
        md += f"  - [Call {i}: {name} ({phone})](#call-{i})\n"

    md += """- [Summary Statistics](#summary-statistics)
- [Recommendations](#recommendations)

## Executive Summary

<a id="executive-summary"></a>

"""

    md += f"""This report analyzes **{metrics.get('total_calls', 0)} calls** from the VAPI voice AI system for {tenant_name}.

### Key Findings

- **Success Rate:** {metrics.get('successful', 0)}/{metrics.get('total_calls', 0)} ({metrics.get('success_rate', 0)}%)
- **Failed Calls:** {metrics.get('failed', 0)} ({round(metrics.get('failed', 0) / max(metrics.get('total_calls', 1), 1) * 100)}%)
- **Frustrated Customers:** {metrics.get('high_frustration', 0)} ({round(metrics.get('high_frustration', 0) / max(metrics.get('total_calls', 1), 1) * 100)}%)
- **Average Duration:** {metrics.get('avg_duration_formatted', '0:00')}
- **Total Cost:** ${metrics.get('total_cost', 0):.2f}

## Key Metrics

<a id="key-metrics"></a>

| Metric | Value |
|--------|-------|
| Total Calls | {metrics.get('total_calls', 0)} |
| Successful | {metrics.get('successful', 0)} ({metrics.get('success_rate', 0)}%) |
| Failed | {metrics.get('failed', 0)} ({round(metrics.get('failed', 0) / max(metrics.get('total_calls', 1), 1) * 100)}%) |
| High Frustration (score ≥3) | {metrics.get('high_frustration', 0)} |
| Average Call Duration | {metrics.get('avg_duration_formatted', '0:00')} |
| Total Cost | ${metrics.get('total_cost', 0):.2f} |
| Average Cost per Call | ${metrics.get('avg_cost', 0):.4f} |

"""

    # Cost Analytics section for WTU chargeback
    cb = metrics.get('cost_breakdown', {})
    total_cost = metrics.get('total_cost', 0.0001) or 0.0001  # Avoid division by zero
    llm_cost = cb.get('llm', 0)
    stt_cost = cb.get('stt', 0)
    tts_cost = cb.get('tts', 0)
    vapi_cost = cb.get('vapi', 0)
    transport_cost = cb.get('transport', 0)

    md += f"""## Cost Analytics (Chargeback)

<a id="cost-analytics"></a>

This section provides detailed cost breakdown for **WTU chargeback purposes**.

### Cost Summary

| Item | Value |
|------|-------|
| **Billing Period** | {date_str} |
| **Total Calls** | {metrics.get('total_calls', 0)} |
| **Total Duration** | {format_duration(metrics.get('total_duration', 0))} |
| **Total Cost** | **${metrics.get('total_cost', 0):.2f}** |

### Cost Breakdown by Component

| Component | Cost | % of Total |
|-----------|------|------------|
| LLM (Language Model) | ${llm_cost:.4f} | {(llm_cost / total_cost * 100):.1f}% |
| STT (Speech-to-Text) | ${stt_cost:.4f} | {(stt_cost / total_cost * 100):.1f}% |
| TTS (Text-to-Speech) | ${tts_cost:.4f} | {(tts_cost / total_cost * 100):.1f}% |
| VAPI Platform | ${vapi_cost:.4f} | {(vapi_cost / total_cost * 100):.1f}% |
| Transport (Telephony) | ${transport_cost:.4f} | {(transport_cost / total_cost * 100):.1f}% |
| **TOTAL** | **${metrics.get('total_cost', 0):.2f}** | **100%** |

### Per-Call Cost Details

| # | Time (UTC) | Customer | Duration | Cost |
|---|------------|----------|----------|------|
"""

    # Add per-call cost rows
    for i, call in enumerate(calls, 1):
        call_time = call.get('started_at', '')[:16].replace('T', ' ') if call.get('started_at') else '-'
        md += f"| {i} | {call_time} | {call['customer_number']} | {call['duration_formatted']} | ${call['total_cost']:.4f} |\n"

    md += f"""| | | **TOTAL** | **{format_duration(metrics.get('total_duration', 0))}** | **${metrics.get('total_cost', 0):.2f}** |

---

## Critical Issues

<a id="critical-issues"></a>

The following calls had significant issues:

| Call # | Customer | Phone | Frustration | Root Cause |
|--------|----------|-------|-------------|------------|
"""

    # Add critical issues (failed calls or high frustration or slow latency)
    for i, call in enumerate(calls, 1):
        if (call['success'] == 'false' or call['success'] == False or
            call['frustration_score'] >= 3 or call['max_latency'] > 10):
            md += f"| [{i}](#call-{i}) | {call['customer_name']} | {call['customer_number']} | {call['frustration_score']}/10 | {call['root_cause']} |\n"

    md += """
## Calls by Customer

<a id="calls-by-customer"></a>

"""

    # Add individual call details
    for i, call in enumerate(calls, 1):
        md += generate_call_section(i, call)

    # Summary statistics
    md += """## Summary Statistics

<a id="summary-statistics"></a>

### End Reasons

| Reason | Count |
|--------|-------|
"""

    for reason, count in metrics.get('end_reasons', {}).items():
        md += f"| {reason} | {count} |\n"

    md += """
## Recommendations

<a id="recommendations"></a>

Based on the analysis:

"""

    # Generate recommendations based on issues found
    recommendations = set()
    for call in calls:
        if call['recommendations'] and call['recommendations'] != 'N/A':
            recommendations.add(call['recommendations'])

    for i, rec in enumerate(recommendations, 1):
        md += f"{i}. {rec}\n"

    if not recommendations:
        md += "No specific recommendations - calls performed as expected.\n"

    return md


def generate_call_section(call_num: int, call: Dict) -> str:
    """Generate markdown section for a single call."""
    md = f"""## Call {call_num}: {call['customer_name']} ({call['customer_number']})

<a id="call-{call_num}"></a>

### Overview

| Field | Value |
|-------|-------|
| **Customer** | {call['customer_name']} |
| **Phone** | {call['customer_number']} |
| **Call ID** | `{call['call_id'][:20]}...` |
| **Start Time (UTC)** | {call['started_at'] or 'None'} |
| **Duration** | {call['duration_formatted']} |
| **Status** | {call['status']} |
| **Ended Reason** | {call['ended_reason']} |
| **Success** | {call['success_display']} |
| **Cost** | ${call['total_cost']:.4f} |

### Analysis

| Metric | Value |
|--------|-------|
| **Frustration Score** | {call['frustration_score']}/10 |
| **Frustration Indicators** | {', '.join(call['frustration_indicators']) if call['frustration_indicators'] else 'None'} |
| **Tool Calls** | {call['tool_call_count']} |
"""

    if call['max_latency'] > 0:
        md += f"| **Max API Latency** | {call['max_latency']}s |\n"

    md += f"""| **Root Cause** | {call['root_cause']} |
| **Recommendations** | {call['recommendations']} |

### AI Summary

> {call['summary'] or 'No summary available'}

### Transcript

```
{call['transcript'] or 'No transcript available'}
```

"""

    # Add API calls table if any
    if call['tool_calls']:
        md += """### API Calls

| Time (s) | Action | Latency | Result |
|----------|--------|---------|--------|
"""
        for tc in call['tool_calls']:
            result = tc['result_preview'].replace('|', '\\|')
            md += f"| {tc['time']} | {tc['action']} | {tc['latency']}s | {result}... |\n"
        md += "\n"

    # Add cost breakdown
    md += f"""### Cost Breakdown

| Component | Cost |
|-----------|------|
| LLM | ${call['cost_breakdown']['llm']:.4f} |
| STT | ${call['cost_breakdown']['stt']:.4f} |
| TTS | ${call['cost_breakdown']['tts']:.4f} |
| VAPI | ${call['cost_breakdown']['vapi']:.4f} |
| **Total** | **${call['total_cost']:.4f}** |

---

"""
    return md


def generate_empty_report(tenant_name: str, target_date: datetime) -> str:
    """Generate report when no calls found."""
    return f"""# VAPI Call Analysis Report

**Generated:** {datetime.utcnow().strftime('%B %d, %Y at %H:%M UTC')}
**Client:** {tenant_name}
**Analysis Period:** {target_date.strftime('%B %d, %Y')}

## Summary

No calls were recorded for this period.
"""


# ===========================================================================
# Helper Functions
# ===========================================================================

def format_duration(seconds: float) -> str:
    """Format seconds as M:SS."""
    if not seconds:
        return "0:00"
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}:{secs:02d}"


def format_success(success: Any) -> str:
    """Format success value for display."""
    if success == 'true' or success == True:
        return "✅ Success"
    elif success == 'false' or success == False:
        return "❌ Failed"
    return "⚠️ Unknown"


def fetch_vapi_calls(phone_number_id: str, start_date: str, end_date: str) -> List[Dict]:
    """Fetch calls from VAPI API."""
    # Re-read API key at call time (supports runtime configuration)
    api_key = os.environ.get('VAPI_API_KEY', '') or VAPI_API_KEY
    if not api_key:
        logger.error("VAPI_API_KEY not configured")
        return []

    url = f"{VAPI_BASE_URL}/call"
    params = {
        'phoneNumberId': phone_number_id,
        'createdAtGe': start_date,
        'createdAtLe': end_date,
        'limit': '100'  # VAPI limits to 100
    }
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }

    try:
        import requests
        resp = requests.get(url, headers=headers, params=params, timeout=60)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error(f"VAPI API error: {e}")
        import traceback
        traceback.print_exc()
        return []


def get_tenant(tenant_id: str) -> Optional[Dict]:
    """Get tenant from DynamoDB."""
    try:
        result = tenants_table.get_item(Key={'tenant_id': tenant_id})
        return result.get('Item')
    except Exception as e:
        logger.error(f"Error getting tenant: {e}")
        return None


def get_all_tenants() -> List[Dict]:
    """Get all tenants from DynamoDB."""
    try:
        result = tenants_table.scan()
        return result.get('Items', [])
    except Exception as e:
        logger.error(f"Error scanning tenants: {e}")
        return []


def store_report(tenant_id: str, date: str, report: Dict) -> None:
    """Store report in DynamoDB."""
    try:
        # Convert floats to Decimal for DynamoDB
        item = {
            'tenant_id': tenant_id,
            'report_date': date,
            'generated_at': datetime.utcnow().isoformat(),
            'total_calls': report.get('total_calls', 0),
            'markdown': report.get('markdown', ''),
            'metrics': json.loads(json.dumps(report.get('metrics', {})), parse_float=Decimal)
        }

        reports_table.put_item(Item=item)
        logger.info(f"Stored report for {tenant_id} on {date}")

    except Exception as e:
        logger.error(f"Error storing report: {e}")
        raise


# For local testing
if __name__ == "__main__":
    # Test with mock data
    test_event = {
        'tenant_id': 'wtu',
        'date': '2026-02-05'
    }
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))
