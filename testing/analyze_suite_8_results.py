#!/usr/bin/env python3
"""
Test Suite 8 Results Analyzer
Analyzes multi-intent edge case test results and provides actionable insights
"""

import json
import sys
from datetime import datetime
from typing import Dict, List, Any
from collections import defaultdict

class TestResultAnalyzer:
    def __init__(self, results_file: str):
        self.results_file = results_file
        self.results = []
        self.load_results()

    def load_results(self):
        """Load test results from JSON file"""
        try:
            with open(self.results_file, 'r') as f:
                self.results = json.load(f)
            print(f"✅ Loaded {len(self.results)} test results from {self.results_file}")
        except Exception as e:
            print(f"❌ Error loading results: {e}")
            sys.exit(1)

    def analyze(self):
        """Run comprehensive analysis"""
        print("\n" + "="*80)
        print("TEST SUITE 8: MULTI-INTENT EDGE CASES - ANALYSIS REPORT")
        print("="*80)
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total Tests: {len(self.results)}")
        print("="*80 + "\n")

        self.print_summary_stats()
        self.print_routing_analysis()
        self.print_classification_analysis()
        self.print_performance_analysis()
        self.print_category_analysis()
        self.print_failure_analysis()
        self.print_recommendations()

    def print_summary_stats(self):
        """Print overall summary statistics"""
        print("📊 SUMMARY STATISTICS")
        print("-" * 80)

        successful = sum(1 for r in self.results if self._is_successful(r))
        failed = len(self.results) - successful

        direct_lambda = sum(1 for r in self.results if r.get('response', {}).get('direct_call', False))
        agent_calls = len(self.results) - direct_lambda

        print(f"  Successful Responses:  {successful}/{len(self.results)} ({successful/len(self.results)*100:.1f}%)")
        print(f"  Failed/Error Responses: {failed}/{len(self.results)} ({failed/len(self.results)*100:.1f}%)")
        print(f"  Direct Lambda Calls:    {direct_lambda}/{len(self.results)} ({direct_lambda/len(self.results)*100:.1f}%)")
        print(f"  Agent Calls:            {agent_calls}/{len(self.results)} ({agent_calls/len(self.results)*100:.1f}%)")
        print()

    def print_routing_analysis(self):
        """Analyze routing decisions"""
        print("🚦 ROUTING ANALYSIS")
        print("-" * 80)

        routing_stats = defaultdict(int)
        for result in self.results:
            response = result.get('response', {})
            agent_name = response.get('agent_name', 'Unknown')
            routing_stats[agent_name] += 1

        print("  Agent Distribution:")
        for agent, count in sorted(routing_stats.items(), key=lambda x: x[1], reverse=True):
            percentage = count / len(self.results) * 100
            print(f"    {agent:30s}: {count:3d} ({percentage:5.1f}%)")
        print()

    def print_classification_analysis(self):
        """Analyze intent classification"""
        print("🎯 CLASSIFICATION ANALYSIS")
        print("-" * 80)

        intent_stats = defaultdict(int)
        action_stats = defaultdict(int)

        for result in self.results:
            response = result.get('response', {})
            intent = response.get('intent', 'Unknown')
            action = response.get('action', 'No Action')

            intent_stats[intent] += 1
            if action:
                action_stats[action] += 1

        print("  Intent Distribution:")
        for intent, count in sorted(intent_stats.items(), key=lambda x: x[1], reverse=True):
            percentage = count / len(self.results) * 100
            print(f"    {intent:20s}: {count:3d} ({percentage:5.1f}%)")

        print("\n  Action Distribution:")
        for action, count in sorted(action_stats.items(), key=lambda x: x[1], reverse=True):
            percentage = count / len(self.results) * 100
            print(f"    {action:30s}: {count:3d} ({percentage:5.1f}%)")
        print()

    def print_performance_analysis(self):
        """Analyze performance metrics"""
        print("⚡ PERFORMANCE ANALYSIS")
        print("-" * 80)

        times = []
        for result in self.results:
            response = result.get('response', {})
            timing = response.get('performance', {})
            total_time = timing.get('total', 0)
            if total_time > 0:
                times.append(total_time)

        if times:
            avg_time = sum(times) / len(times)
            min_time = min(times)
            max_time = max(times)

            print(f"  Average Response Time: {avg_time:.2f}s")
            print(f"  Fastest Response:      {min_time:.2f}s")
            print(f"  Slowest Response:      {max_time:.2f}s")

            # Response time distribution
            fast = sum(1 for t in times if t < 3)
            medium = sum(1 for t in times if 3 <= t < 7)
            slow = sum(1 for t in times if t >= 7)

            print(f"\n  Response Time Distribution:")
            print(f"    Fast (< 3s):    {fast:3d} ({fast/len(times)*100:.1f}%)")
            print(f"    Medium (3-7s):  {medium:3d} ({medium/len(times)*100:.1f}%)")
            print(f"    Slow (>= 7s):   {slow:3d} ({slow/len(times)*100:.1f}%)")
        else:
            print("  No performance data available")
        print()

    def print_category_analysis(self):
        """Analyze results by test category"""
        print("📂 CATEGORY-BY-CATEGORY BREAKDOWN")
        print("-" * 80)

        categories = {
            "1": "Query + Action Hybrid",
            "2": "Conditional Multi-Intent",
            "3": "Sequential Multi-Step",
            "4": "Multiple Entity Queries",
            "5": "Ambiguous Intent",
            "6": "Malformed / Edge Inputs",
            "7": "Context Stress Tests",
            "8": "Performance Edge Cases"
        }

        for cat_num, cat_name in categories.items():
            cat_results = [r for r in self.results if r.get('test', '').startswith(f'8.{cat_num}')]

            if not cat_results:
                continue

            successful = sum(1 for r in cat_results if self._is_successful(r))
            direct = sum(1 for r in cat_results if r.get('response', {}).get('direct_call', False))

            print(f"\n  Category {cat_num}: {cat_name}")
            print(f"  {'-' * 78}")
            print(f"    Total Tests:     {len(cat_results)}")
            print(f"    Successful:      {successful}/{len(cat_results)} ({successful/len(cat_results)*100:.1f}%)")
            print(f"    Direct Lambda:   {direct}/{len(cat_results)}")

            # Print each test in category
            for result in cat_results:
                test_id = result.get('test', 'Unknown')
                name = result.get('name', 'Unknown')
                response = result.get('response', {})
                agent = response.get('agent_name', 'Unknown')
                intent = response.get('intent', 'Unknown')
                action = response.get('action', 'None')
                direct_call = response.get('direct_call', False)

                status = "✅" if self._is_successful(result) else "❌"
                route = "⚡ Direct" if direct_call else f"🤖 {agent}"

                print(f"    {status} {test_id}: {route:25s} | Intent: {intent:15s} | Action: {str(action):20s}")
        print()

    def print_failure_analysis(self):
        """Analyze failures and unexpected behaviors"""
        print("🔍 FAILURE & UNEXPECTED BEHAVIOR ANALYSIS")
        print("-" * 80)

        failures = [r for r in self.results if not self._is_successful(r)]

        if failures:
            print(f"  Found {len(failures)} failures or unexpected responses:\n")
            for result in failures:
                test_id = result.get('test', 'Unknown')
                name = result.get('name', 'Unknown')
                message = result.get('message', 'Unknown')
                expected = result.get('expected', 'Unknown')
                response = result.get('response', {})

                print(f"  Test {test_id}: {name}")
                print(f"    Message:  \"{message}\"")
                print(f"    Expected: {expected}")

                if 'error' in response:
                    print(f"    ❌ Error:   {response.get('error', 'Unknown error')}")
                else:
                    print(f"    Actual:   Agent={response.get('agent_name', 'Unknown')}, "
                          f"Intent={response.get('intent', 'Unknown')}, "
                          f"Action={response.get('action', 'None')}")
                print()
        else:
            print("  ✅ No failures detected (all tests returned responses)")
        print()

    def print_recommendations(self):
        """Print recommendations based on analysis"""
        print("💡 RECOMMENDATIONS")
        print("-" * 80)

        # Analyze multi-intent handling
        multi_intent_tests = [r for r in self.results if '1.' in r.get('test', '') or '2.' in r.get('test', '') or '3.' in r.get('test', '')]
        multi_intent_agents = sum(1 for r in multi_intent_tests if 'Multi-Agent' in r.get('response', {}).get('agent_name', ''))

        print("\n  1. Multi-Intent Handling:")
        if multi_intent_agents > 0:
            print(f"     ✅ System successfully used multi-agent orchestration in {multi_intent_agents} cases")
        else:
            print(f"     ⚠️  Multi-agent orchestration not detected. Consider:")
            print(f"        - Verify ENABLE_MULTI_AGENT_ORCHESTRATION is set to 'true'")
            print(f"        - Check multi_agent_classifier.py for complex query detection")

        # Analyze context resolution
        context_tests = [r for r in self.results if '7.' in r.get('test', '')]
        context_failures = sum(1 for r in context_tests if not self._is_successful(r))

        print("\n  2. Context Resolution:")
        if context_failures == 0:
            print(f"     ✅ All context resolution tests passed")
        else:
            print(f"     ⚠️  {context_failures}/{len(context_tests)} context tests had issues. Consider:")
            print(f"        - Enhancing context_resolver.py to handle edge cases")
            print(f"        - Adding explicit error messages for ambiguous references")

        # Analyze ambiguous handling
        ambiguous_tests = [r for r in self.results if '5.' in r.get('test', '')]
        clarification_count = sum(1 for r in ambiguous_tests if 'clarif' in str(r.get('response', {})).lower())

        print("\n  3. Ambiguity Handling:")
        if clarification_count > len(ambiguous_tests) * 0.5:
            print(f"     ✅ System appropriately asks for clarification on ambiguous queries")
        else:
            print(f"     ⚠️  Consider adding more clarification prompts for ambiguous intents")
            print(f"        - Enhance classifier.py to detect ambiguous patterns")
            print(f"        - Add 'needs_clarification' flag to classification response")

        # Performance recommendations
        avg_times = []
        for r in self.results:
            total = r.get('response', {}).get('performance', {}).get('total', 0)
            if total > 0:
                avg_times.append(total)

        if avg_times:
            avg = sum(avg_times) / len(avg_times)
            print(f"\n  4. Performance:")
            if avg < 5:
                print(f"     ✅ Good average response time: {avg:.2f}s")
            else:
                print(f"     ⚠️  Average response time is {avg:.2f}s. Consider:")
                print(f"        - Increasing direct Lambda optimization coverage")
                print(f"        - Optimizing agent prompts for faster responses")

        print("\n  5. General Improvements:")
        print("     - Add explicit error messages for unsupported multi-intent patterns")
        print("     - Implement query decomposition for complex requests")
        print("     - Consider adding a 'task planner' for sequential multi-step queries")
        print("     - Enhance filter extraction to support negative filters (NOT operator)")
        print()

    def _is_successful(self, result: Dict) -> bool:
        """Check if a test result is considered successful"""
        response = result.get('response', {})

        # Has error
        if 'error' in response:
            return False

        # Missing required fields
        if not response.get('agent_name') or not response.get('intent'):
            return False

        # Has a response
        if response.get('response'):
            return True

        return False

    def export_csv(self, output_file: str):
        """Export results to CSV for spreadsheet analysis"""
        import csv

        with open(output_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'Test ID', 'Category', 'Name', 'Message', 'Expected',
                'Agent', 'Intent', 'Action', 'Direct Call', 'Success',
                'Response Time', 'Error'
            ])
            writer.writeheader()

            for result in self.results:
                response = result.get('response', {})
                writer.writerow({
                    'Test ID': result.get('test', ''),
                    'Category': result.get('test', '').split('.')[1] if '.' in result.get('test', '') else '',
                    'Name': result.get('name', ''),
                    'Message': result.get('message', ''),
                    'Expected': result.get('expected', ''),
                    'Agent': response.get('agent_name', ''),
                    'Intent': response.get('intent', ''),
                    'Action': response.get('action', ''),
                    'Direct Call': response.get('direct_call', False),
                    'Success': self._is_successful(result),
                    'Response Time': response.get('performance', {}).get('total', 0),
                    'Error': response.get('error', '')
                })

        print(f"✅ Results exported to {output_file}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 analyze_suite_8_results.py <results_file.json> [--csv output.csv]")
        sys.exit(1)

    results_file = sys.argv[1]
    analyzer = TestResultAnalyzer(results_file)
    analyzer.analyze()

    # Export to CSV if requested
    if '--csv' in sys.argv:
        csv_index = sys.argv.index('--csv') + 1
        if csv_index < len(sys.argv):
            csv_file = sys.argv[csv_index]
            analyzer.export_csv(csv_file)


if __name__ == '__main__':
    main()
