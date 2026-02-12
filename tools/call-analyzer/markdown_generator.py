"""
Markdown Report Generator
"""
import os
from datetime import datetime
from typing import List, Dict
from transcript_analyzer import generate_summary_stats


def generate_markdown_report(
    calls: List[Dict],
    output_path: str,
    start_date: datetime,
    end_date: datetime
) -> str:
    """
    Generate detailed Markdown report from analyzed calls.

    Args:
        calls: List of analyzed call dictionaries
        output_path: Path for output markdown file
        start_date: Report start date
        end_date: Report end date

    Returns:
        Path to generated file
    """
    stats = generate_summary_stats(calls)

    # Format date range for title
    if start_date.date() == end_date.date():
        date_str = start_date.strftime("%B %d, %Y")
    else:
        date_str = f"{start_date.strftime('%B %d')}-{end_date.strftime('%d, %Y')}"

    sections = []

    # Header
    sections.append(f"# Call Analysis Report - {date_str}\n")

    # Executive Summary
    sections.append(_generate_executive_summary(stats))

    # Call Outcomes Summary
    sections.append(_generate_outcomes_table(stats))

    # Detailed Call Analysis
    sections.append(_generate_detailed_analysis(calls))

    # Key Findings
    sections.append(_generate_key_findings(calls, stats))

    # Recommendations
    sections.append(_generate_recommendations(calls, stats))

    # Appendix
    sections.append(_generate_appendix(calls))

    # Footer
    sections.append(f"\n---\n\n*Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n")
    sections.append("*Analysis by: Call Analyzer Tool*\n")

    # Combine and write
    content = '\n'.join(sections)

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, 'w') as f:
        f.write(content)

    return output_path


def _generate_executive_summary(stats: Dict) -> str:
    """Generate executive summary section."""
    lines = [
        "## Executive Summary\n",
        "| Metric | Value |",
        "|--------|-------|",
        f"| **Total Calls** | {stats['total_calls']} |",
        f"| **Successful Appointments** | {stats['by_category'].get('SUCCESS', 0)} ({stats.get('success_rate', 0)}%) |",
        f"| **No Availability Issues** | {stats['by_category'].get('NO_AVAILABILITY', 0)} ({stats.get('no_availability_rate', 0)}%) |",
        f"| **Office Handoffs** | {stats['by_category'].get('OFFICE_HANDOFF', 0)} |",
        f"| **Calls with AWS Logs** | {stats['with_logs']} |",
        f"| **API Timeout Errors** | {stats['issues_count'].get('timeout', 0)} |",
        "\n---\n",
    ]
    return '\n'.join(lines)


def _generate_outcomes_table(stats: Dict) -> str:
    """Generate outcomes summary table."""
    lines = [
        "## Call Outcomes Summary\n",
        "| Outcome | Count | Percentage |",
        "|---------|-------|------------|",
    ]

    total = stats['total_calls'] or 1
    for category, count in sorted(stats['by_category'].items(), key=lambda x: -x[1]):
        pct = round(count / total * 100, 1)
        lines.append(f"| {category} | {count} | {pct}% |")

    lines.append("\n---\n")
    return '\n'.join(lines)


def _generate_detailed_analysis(calls: List[Dict]) -> str:
    """Generate detailed analysis for each call."""
    lines = ["## Detailed Call Analysis\n"]

    for i, call in enumerate(calls, 1):
        lines.append(_format_single_call(i, call))

    return '\n'.join(lines)


def _format_single_call(index: int, call: Dict) -> str:
    """Format a single call for the report."""
    analysis = call.get('analysis', {})
    log_insights = call.get('log_insights', {})

    # Extract customer name from transcript if available
    transcript = call.get('transcript', '')
    customer_name = _extract_customer_name(transcript)

    # Format created_at
    created_at = call.get('created_at', '')
    if created_at:
        try:
            dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            time_str = dt.strftime('%H:%M UTC')
            date_str = dt.strftime('%b %d')
        except:
            time_str = created_at
            date_str = ''
    else:
        time_str = 'Unknown'
        date_str = ''

    lines = [
        f"### Call {index}: {customer_name} - {call.get('category', 'Unknown')} ({date_str} {time_str})",
        f"**ID:** `{call.get('id', 'N/A')}`",
        f"**End Reason:** {call.get('end_reason', 'N/A')}",
        f"**Outcome:** {analysis.get('outcome', 'unknown')}",
        "",
        "```",
    ]

    # Format transcript nicely
    if transcript:
        for line in transcript.split('\n')[:20]:  # Limit to 20 lines
            lines.append(line)
        if transcript.count('\n') > 20:
            lines.append("... [truncated]")
    else:
        lines.append("No transcript available")

    lines.append("```")
    lines.append("")

    # Analysis section
    lines.append("**Analysis:**")

    issues = analysis.get('issues', [])
    if issues:
        lines.append(f"- Issues detected: {', '.join(issues)}")

    key_phrases = analysis.get('key_phrases', [])
    if key_phrases:
        lines.append(f"- Key phrases: {', '.join(key_phrases)}")

    # Log insights
    if log_insights.get('has_logs'):
        lines.append(f"- Lambdas invoked: {', '.join(log_insights.get('lambdas_invoked', []))}")
        if log_insights.get('errors'):
            lines.append(f"- Errors in logs: {len(log_insights['errors'])}")
        if log_insights.get('api_calls'):
            lines.append(f"- API calls: {', '.join(log_insights['api_calls'])}")
    else:
        lines.append("- No AWS logs found")

    # Inference
    inference = _generate_call_inference(call)
    if inference:
        lines.append(f"\n**Inference:** {inference}")

    lines.append("\n---\n")
    return '\n'.join(lines)


def _extract_customer_name(transcript: str) -> str:
    """Extract customer name from transcript greeting."""
    import re
    match = re.search(r"Hello,?\s+(\w+)", transcript)
    if match:
        return match.group(1)
    return "Unknown"


def _generate_call_inference(call: Dict) -> str:
    """Generate inference for a single call."""
    analysis = call.get('analysis', {})
    category = call.get('category', '')

    inferences = []

    if category == 'SUCCESS':
        inferences.append("Appointment booked successfully")
    elif category == 'NO_AVAILABILITY':
        inferences.append("Backend schedule capacity issue - not AI problem")
    elif category == 'OFFICE_HANDOFF':
        reason = analysis.get('outcome', '')
        if reason == 'cancellation_request':
            inferences.append("Customer wanted to cancel - correctly redirected to office")
        else:
            inferences.append("Appropriately escalated to human support")
    elif category == 'NOT_SCHEDULABLE':
        inferences.append("Project status in backend prevents scheduling")

    issues = analysis.get('issues', [])
    if 'repeat_response' in issues:
        inferences.append("Loop detected - may need UX improvement")
    if 'customer_frustration' in issues:
        inferences.append("Customer frustration detected")

    return '; '.join(inferences)


def _generate_key_findings(calls: List[Dict], stats: Dict) -> str:
    """Generate key findings section."""
    lines = ["## Key Findings\n"]

    # Positive findings
    lines.append("### Positive Observations\n")

    success_count = stats['by_category'].get('SUCCESS', 0)
    if success_count > 0:
        lines.append(f"1. **{success_count} successful appointments** booked ({stats.get('success_rate', 0)}% success rate)")

    timeout_count = stats['issues_count'].get('timeout', 0)
    if timeout_count == 0:
        lines.append("2. **No API timeout errors** detected")

    lines.append("")

    # Issues found
    lines.append("### Issues Identified\n")
    lines.append("| Issue | Count | Impact |")
    lines.append("|-------|-------|--------|")

    no_avail = stats['by_category'].get('NO_AVAILABILITY', 0)
    if no_avail > 0:
        lines.append(f"| No appointments available | {no_avail} | High - customers can't schedule |")

    for issue, count in stats['issues_count'].items():
        impact = _get_issue_impact(issue)
        lines.append(f"| {issue} | {count} | {impact} |")

    lines.append("\n---\n")
    return '\n'.join(lines)


def _get_issue_impact(issue: str) -> str:
    """Get impact level for an issue."""
    high_impact = ['timeout', 'api_error', 'check_further_loop', 'time_format_confusion', 'customer_frustration']
    medium_impact = ['repeat_response', 'phone_number_inconsistency']
    low_impact = ['silence_timeout', 'expected_call_transfer']

    if issue in high_impact:
        return "High - affects user experience"
    elif issue in medium_impact:
        return "Medium - may cause confusion"
    elif issue in low_impact:
        return "Low - minor impact"
    else:
        return "Unknown"


def _generate_recommendations(calls: List[Dict], stats: Dict) -> str:
    """Generate comprehensive overall analysis section."""
    lines = ["## Overall Analysis\n"]

    total = stats['total_calls'] or 1

    # Success Rate breakdown
    lines.append("### Success Rate\n")
    success_count = stats['by_category'].get('SUCCESS', 0)
    handoff_count = stats['by_category'].get('OFFICE_HANDOFF', 0)
    no_avail_count = stats['by_category'].get('NO_AVAILABILITY', 0)
    other_count = stats['by_category'].get('OTHER', 0) + stats['by_category'].get('CANCELLATION', 0) + stats['by_category'].get('NOT_SCHEDULABLE', 0)

    # Get customer names for successful appointments
    success_names = []
    for call in calls:
        if call.get('category') == 'SUCCESS':
            transcript = call.get('transcript', '')
            import re
            match = re.search(r"Hello,?\s+(\w+)", transcript)
            if match:
                success_names.append(match.group(1))

    success_str = f"({', '.join(success_names)})" if success_names else ""

    lines.append(f"- **{success_count} successful appointments** {success_str} - {round(success_count/total*100, 1)}%")
    lines.append(f"- **{handoff_count} office handoffs** - {round(handoff_count/total*100, 1)}%")
    lines.append(f"- **{no_avail_count} no availability** - {round(no_avail_count/total*100, 1)}%")
    lines.append(f"- **{other_count} other** (errors, abandoned, etc.) - {round(other_count/total*100, 1)}%")
    lines.append("")

    # Key Patterns table
    lines.append("### Key Patterns\n")
    lines.append("| Issue | Frequency | Impact |")
    lines.append("|-------|-----------|--------|")

    issue_impacts = {
        'phone_number_inconsistency': ('Medium', 'users had to ask for repeat'),
        'time_format_confusion': ('High', 'caused confusion and abandonment'),
        'timeout': ('High', 'users called back or gave up'),
        'api_error': ('High', 'users called back or gave up'),
        'check_further_loop': ('High', 'frustrated users'),
        'repeat_response': ('Medium', 'may cause confusion'),
        'expected_call_transfer': ('Low', 'expectation mismatch'),
        'customer_frustration': ('High', 'poor user experience'),
        'silence_timeout': ('Low', 'user may have been distracted'),
    }

    for issue, count in sorted(stats['issues_count'].items(), key=lambda x: -x[1]):
        impact_level, impact_desc = issue_impacts.get(issue, ('Medium', 'affects user experience'))
        issue_display = issue.replace('_', ' ').title()
        lines.append(f"| {issue_display} | {count} calls | {impact_level} - {impact_desc} |")

    lines.append("")

    # What's Working Well
    lines.append("### What's Working Well\n")
    working_well = []

    if success_count > 0:
        working_well.append(f"**Appointment status checks** - {success_count} successful bookings")

    if handoff_count > 0:
        working_well.append("**Graceful escalation to office** - When AI can't help, it offers human option")

    # Check for project context in greetings
    has_project_context = any('project' in call.get('transcript', '').lower()[:200] for call in calls)
    if has_project_context:
        working_well.append("**Project context in greeting** - Sets context for the conversation")

    for i, item in enumerate(working_well, 1):
        lines.append(f"{i}. {item}")
    lines.append("")

    # What Needs Improvement
    lines.append("### What Needs Improvement\n")
    improvements = []

    if stats['issues_count'].get('time_format_confusion', 0) > 0:
        improvements.append("**Time slot voice formatting** - Confusing format needs clearer presentation")

    if stats['issues_count'].get('phone_number_inconsistency', 0) > 0:
        improvements.append("**Phone number consistency** - Sometimes missing digits on repeat")

    if stats['issues_count'].get('timeout', 0) > 0 or stats['issues_count'].get('api_error', 0) > 0:
        improvements.append("**API reliability** - Timeouts causing failed calls")

    if stats['issues_count'].get('check_further_loop', 0) > 0:
        improvements.append("**\"Check further out\" loop** - Should offer office number instead of looping")

    if not improvements:
        improvements.append("No major improvements needed based on this call set")

    for i, item in enumerate(improvements, 1):
        lines.append(f"{i}. {item}")
    lines.append("")

    # Positive Signs
    lines.append("### Positive Signs\n")
    lines.append("- Users who got clear information were satisfied")
    lines.append("- The AI knows when to escalate vs. when to keep trying")
    if has_project_context:
        lines.append("- Greeting with project context helps orient the conversation")
    lines.append("")

    # The Real Issue
    lines.append("### The Real Issue\n")
    lines.append(f"Looking at the {total} calls, the biggest problems are:\n")

    real_issues = []
    if no_avail_count > 0:
        real_issues.append("**Backend availability** - Calls failed because no dates were available or API timed out")

    if stats['issues_count'].get('phone_number_inconsistency', 0) > 0 or stats['issues_count'].get('time_format_confusion', 0) > 0:
        real_issues.append("**Voice formatting** - Phone numbers and times are sometimes garbled")

    if stats['issues_count'].get('check_further_loop', 0) > 0:
        real_issues.append("**Loop issue** - System asked to check further when already at max range")

    if not real_issues:
        real_issues.append("No critical systemic issues detected")

    for i, item in enumerate(real_issues, 1):
        lines.append(f"{i}. {item}")

    lines.append("\nThe AI logic itself is mostly sound. The issues are at the edges: formatting, API reliability, and backend availability.")

    lines.append("\n---\n")
    return '\n'.join(lines)


def _generate_appendix(calls: List[Dict]) -> str:
    """Generate appendix with all call IDs."""
    lines = ["## Appendix: All Call IDs\n"]
    lines.append("| # | Call ID | Customer | Outcome |")
    lines.append("|---|---------|----------|---------|")

    for i, call in enumerate(calls, 1):
        customer = _extract_customer_name(call.get('transcript', ''))
        category = call.get('category', 'OTHER')
        call_id = call.get('id', 'N/A')
        outcome_str = f"**{category}**" if category == 'SUCCESS' else category
        lines.append(f"| {i} | {call_id[:20]}... | {customer} | {outcome_str} |")

    return '\n'.join(lines)
