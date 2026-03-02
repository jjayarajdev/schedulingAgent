#!/usr/bin/env python3
"""
Test script to generate a sample report locally
Tests the Cost Analytics section for WTU chargeback
"""
import os
import sys
from datetime import datetime, timedelta

# Set up environment
os.environ['VAPI_API_KEY'] = os.environ.get('VAPI_KEY', 'a4ed6edd-9a1c-4a67-ba61-2a1fa2186c6c')
os.environ['ENVIRONMENT'] = 'local'

# Import report handler functions
from reports.handler import (
    fetch_vapi_calls,
    analyze_call,
    calculate_metrics,
    generate_markdown_report
)

def test_report(phone_number_id: str, phone_name: str, days_ago: int = 1):
    """Generate a test report for a specific phone number."""

    target_date = datetime.utcnow() - timedelta(days=days_ago)
    start_date = target_date.strftime('%Y-%m-%dT00:00:00Z')
    end_date = target_date.strftime('%Y-%m-%dT23:59:59Z')

    print(f"\n{'='*60}")
    print(f"Testing Report Generation for: {phone_name}")
    print(f"Phone ID: {phone_number_id}")
    print(f"Date: {target_date.strftime('%Y-%m-%d')}")
    print(f"{'='*60}\n")

    # Fetch calls
    print("Fetching calls from VAPI API...")
    calls = fetch_vapi_calls(phone_number_id, start_date, end_date)

    if not calls:
        print(f"No calls found for {target_date.strftime('%Y-%m-%d')}")
        print("Try a different date with: python test-report.py [days_ago]")
        return

    print(f"Found {len(calls)} calls\n")

    # Analyze calls
    print("Analyzing calls...")
    analyzed_calls = []
    for call in calls:
        analyzed = analyze_call(call)
        analyzed_calls.append(analyzed)
        print(f"  - Call {analyzed['call_id'][:8]}... | "
              f"Duration: {analyzed['duration_formatted']} | "
              f"Cost: ${analyzed['total_cost']:.4f}")

    # Calculate metrics
    print("\nCalculating metrics...")
    metrics = calculate_metrics(analyzed_calls)

    print(f"\nMetrics Summary:")
    print(f"  Total Calls: {metrics['total_calls']}")
    print(f"  Success Rate: {metrics['success_rate']}%")
    print(f"  Total Cost: ${metrics['total_cost']:.2f}")
    print(f"  Avg Cost per Call: ${metrics['avg_cost']:.4f}")

    if 'cost_breakdown' in metrics:
        print(f"\nCost Breakdown:")
        cb = metrics['cost_breakdown']
        print(f"  LLM: ${cb.get('llm', 0):.4f}")
        print(f"  STT: ${cb.get('stt', 0):.4f}")
        print(f"  TTS: ${cb.get('tts', 0):.4f}")
        print(f"  VAPI: ${cb.get('vapi', 0):.4f}")
        print(f"  Transport: ${cb.get('transport', 0):.4f}")

    # Generate markdown
    print("\nGenerating markdown report...")
    markdown = generate_markdown_report("WTU Test", "wtu", target_date, analyzed_calls, metrics)

    # Save to file
    output_file = f"test-report-{target_date.strftime('%Y-%m-%d')}.md"
    with open(output_file, 'w') as f:
        f.write(markdown)

    print(f"\nReport saved to: {output_file}")
    print(f"File size: {len(markdown)} bytes")

    # Show Cost Analytics section
    print("\n" + "="*60)
    print("COST ANALYTICS SECTION PREVIEW:")
    print("="*60)

    start_idx = markdown.find("## Cost Analytics")
    end_idx = markdown.find("## Critical Issues")
    if start_idx != -1 and end_idx != -1:
        print(markdown[start_idx:end_idx])
    else:
        print("Could not find Cost Analytics section")

if __name__ == "__main__":
    # Phone numbers
    PHONES = {
        'wtu': ('04839e46-2cbc-467e-8e01-638900654c36', 'WTU Tenant'),
        'pf': ('6b7ac954-1f6e-460d-962a-48883d31c1f0', 'PF-Agent'),
        'pf-dev': ('1c99c266-9778-4809-bf5e-dba30326a0ae', 'PF-Agent-Dev'),
    }

    # Default to WTU
    phone_key = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in PHONES else 'wtu'
    days_ago = int(sys.argv[2]) if len(sys.argv) > 2 else 1

    phone_id, phone_name = PHONES[phone_key]
    test_report(phone_id, phone_name, days_ago)
