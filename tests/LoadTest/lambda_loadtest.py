"""
Lambda Function Load Test for AWS Scheduling Agent
Tests Lambda function performance, concurrency, and error handling

Usage:
    # Basic test with web UI
    locust -f lambda_loadtest.py

    # Headless mode - bulk ops only
    locust -f lambda_loadtest.py --headless -u 20 -r 2 -t 5m --html lambda_report.html

    # Distributed mode
    locust -f lambda_loadtest.py --master
"""

import json
import random
import time
from typing import Dict

from locust import HttpUser, TaskSet, between, events, task

from config import BULK_OPS_PAYLOADS, LAMBDA_FUNCTIONS, SCHEDULING_PAYLOADS
from utils import invoke_lambda


# ============================================================================
# Task Sets - Lambda Function Behaviors
# ============================================================================


class BulkOperationsTasks(TaskSet):
    """Task set for bulk operations Lambda testing"""

    @task(4)
    def optimize_route(self):
        """Test route optimization (40%)"""
        payload = BULK_OPS_PAYLOADS["optimize_route"]

        start_time = time.time()
        request_name = "lambda:bulk_ops:optimize_route"

        try:
            result = invoke_lambda(
                function_name=LAMBDA_FUNCTIONS["bulk_ops"], payload=payload
            )

            elapsed_ms = result["elapsed_ms"]

            if result["success"] and result["status_code"] == 200:
                events.request.fire(
                    request_type="lambda",
                    name=request_name,
                    response_time=elapsed_ms,
                    response_length=len(json.dumps(result["response"])),
                    exception=None,
                    context={"operation": "optimize_route"},
                )
            else:
                events.request.fire(
                    request_type="lambda",
                    name=request_name,
                    response_time=elapsed_ms,
                    response_length=0,
                    exception=Exception(result.get("error", "Unknown error")),
                    context={},
                )

        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            events.request.fire(
                request_type="lambda",
                name=request_name,
                response_time=elapsed_ms,
                response_length=0,
                exception=e,
                context={},
            )

    @task(3)
    def bulk_assign_teams(self):
        """Test bulk team assignment (30%)"""
        payload = BULK_OPS_PAYLOADS["bulk_assign"]

        start_time = time.time()
        request_name = "lambda:bulk_ops:bulk_assign"

        try:
            result = invoke_lambda(
                function_name=LAMBDA_FUNCTIONS["bulk_ops"], payload=payload
            )

            elapsed_ms = result["elapsed_ms"]

            if result["success"] and result["status_code"] == 200:
                events.request.fire(
                    request_type="lambda",
                    name=request_name,
                    response_time=elapsed_ms,
                    response_length=len(json.dumps(result["response"])),
                    exception=None,
                    context={"operation": "bulk_assign"},
                )
            else:
                events.request.fire(
                    request_type="lambda",
                    name=request_name,
                    response_time=elapsed_ms,
                    response_length=0,
                    exception=Exception(result.get("error", "Unknown error")),
                    context={},
                )

        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            events.request.fire(
                request_type="lambda",
                name=request_name,
                response_time=elapsed_ms,
                response_length=0,
                exception=e,
                context={},
            )

    @task(2)
    def validate_projects(self):
        """Test project validation (20%)"""
        payload = BULK_OPS_PAYLOADS["validate_projects"]

        start_time = time.time()
        request_name = "lambda:bulk_ops:validate_projects"

        try:
            result = invoke_lambda(
                function_name=LAMBDA_FUNCTIONS["bulk_ops"], payload=payload
            )

            elapsed_ms = result["elapsed_ms"]

            if result["success"] and result["status_code"] == 200:
                events.request.fire(
                    request_type="lambda",
                    name=request_name,
                    response_time=elapsed_ms,
                    response_length=len(json.dumps(result["response"])),
                    exception=None,
                    context={"operation": "validate_projects"},
                )
            else:
                events.request.fire(
                    request_type="lambda",
                    name=request_name,
                    response_time=elapsed_ms,
                    response_length=0,
                    exception=Exception(result.get("error", "Unknown error")),
                    context={},
                )

        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            events.request.fire(
                request_type="lambda",
                name=request_name,
                response_time=elapsed_ms,
                response_length=0,
                exception=e,
                context={},
            )

    @task(1)
    def detect_conflicts(self):
        """Test conflict detection (10%)"""
        payload = BULK_OPS_PAYLOADS["detect_conflicts"]

        start_time = time.time()
        request_name = "lambda:bulk_ops:detect_conflicts"

        try:
            result = invoke_lambda(
                function_name=LAMBDA_FUNCTIONS["bulk_ops"], payload=payload
            )

            elapsed_ms = result["elapsed_ms"]

            if result["success"] and result["status_code"] == 200:
                events.request.fire(
                    request_type="lambda",
                    name=request_name,
                    response_time=elapsed_ms,
                    response_length=len(json.dumps(result["response"])),
                    exception=None,
                    context={"operation": "detect_conflicts"},
                )
            else:
                events.request.fire(
                    request_type="lambda",
                    name=request_name,
                    response_time=elapsed_ms,
                    response_length=0,
                    exception=Exception(result.get("error", "Unknown error")),
                    context={},
                )

        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            events.request.fire(
                request_type="lambda",
                name=request_name,
                response_time=elapsed_ms,
                response_length=0,
                exception=e,
                context={},
            )


class SchedulingActionsTasks(TaskSet):
    """Task set for scheduling actions Lambda testing (if deployed)"""

    @task(5)
    def list_projects(self):
        """Test list projects action (50%)"""
        payload = SCHEDULING_PAYLOADS["list_projects"]

        start_time = time.time()
        request_name = "lambda:scheduling:list_projects"

        try:
            # Check if Lambda exists
            if LAMBDA_FUNCTIONS.get("scheduling"):
                result = invoke_lambda(
                    function_name=LAMBDA_FUNCTIONS["scheduling"], payload=payload
                )

                elapsed_ms = result["elapsed_ms"]

                if result["success"] and result["status_code"] == 200:
                    events.request.fire(
                        request_type="lambda",
                        name=request_name,
                        response_time=elapsed_ms,
                        response_length=len(json.dumps(result["response"])),
                        exception=None,
                        context={"action": "list_projects"},
                    )
                else:
                    events.request.fire(
                        request_type="lambda",
                        name=request_name,
                        response_time=elapsed_ms,
                        response_length=0,
                        exception=Exception(result.get("error", "Unknown error")),
                        context={},
                    )
            else:
                # Skip if not deployed
                print(
                    "Scheduling Lambda not configured, skipping list_projects test"
                )

        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            events.request.fire(
                request_type="lambda",
                name=request_name,
                response_time=elapsed_ms,
                response_length=0,
                exception=e,
                context={},
            )

    @task(5)
    def get_available_dates(self):
        """Test get available dates action (50%)"""
        payload = SCHEDULING_PAYLOADS["get_available_dates"]

        start_time = time.time()
        request_name = "lambda:scheduling:get_available_dates"

        try:
            if LAMBDA_FUNCTIONS.get("scheduling"):
                result = invoke_lambda(
                    function_name=LAMBDA_FUNCTIONS["scheduling"], payload=payload
                )

                elapsed_ms = result["elapsed_ms"]

                if result["success"] and result["status_code"] == 200:
                    events.request.fire(
                        request_type="lambda",
                        name=request_name,
                        response_time=elapsed_ms,
                        response_length=len(json.dumps(result["response"])),
                        exception=None,
                        context={"action": "get_available_dates"},
                    )
                else:
                    events.request.fire(
                        request_type="lambda",
                        name=request_name,
                        response_time=elapsed_ms,
                        response_length=0,
                        exception=Exception(result.get("error", "Unknown error")),
                        context={},
                    )
            else:
                print(
                    "Scheduling Lambda not configured, skipping get_available_dates test"
                )

        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            events.request.fire(
                request_type="lambda",
                name=request_name,
                response_time=elapsed_ms,
                response_length=0,
                exception=e,
                context={},
            )


# ============================================================================
# User Classes
# ============================================================================


class BulkOperationsUser(HttpUser):
    """User that primarily tests bulk operations Lambda"""

    wait_time = between(1, 3)

    tasks = {BulkOperationsTasks: 1}


class MixedLambdaUser(HttpUser):
    """User that tests both bulk ops and scheduling Lambdas"""

    wait_time = between(2, 5)

    tasks = {BulkOperationsTasks: 7, SchedulingActionsTasks: 3}


# ============================================================================
# Event Handlers - Custom Metrics
# ============================================================================

lambda_stats = {
    "bulk_ops": {"success": 0, "failure": 0},
    "scheduling": {"success": 0, "failure": 0},
    "total_invocations": 0,
}


@events.request.add_listener
def on_lambda_request(
    request_type, name, response_time, response_length, exception, context, **kwargs
):
    """Track Lambda-specific metrics"""
    if request_type == "lambda":
        lambda_stats["total_invocations"] += 1

        if "bulk_ops" in name:
            if exception is None:
                lambda_stats["bulk_ops"]["success"] += 1
            else:
                lambda_stats["bulk_ops"]["failure"] += 1

        if "scheduling" in name:
            if exception is None:
                lambda_stats["scheduling"]["success"] += 1
            else:
                lambda_stats["scheduling"]["failure"] += 1


@events.test_stop.add_listener
def on_lambda_test_stop(environment, **kwargs):
    """Print Lambda test summary"""
    print("\n" + "=" * 80)
    print("LAMBDA FUNCTION LOAD TEST SUMMARY")
    print("=" * 80)

    print(f"\nTotal Lambda Invocations: {lambda_stats['total_invocations']}")

    print("\nBulk Operations Lambda:")
    print(f"  Success: {lambda_stats['bulk_ops']['success']}")
    print(f"  Failure: {lambda_stats['bulk_ops']['failure']}")
    if lambda_stats["bulk_ops"]["success"] + lambda_stats["bulk_ops"]["failure"] > 0:
        success_rate = (
            lambda_stats["bulk_ops"]["success"]
            / (lambda_stats["bulk_ops"]["success"] + lambda_stats["bulk_ops"]["failure"])
        ) * 100
        print(f"  Success Rate: {success_rate:.2f}%")

    print("\nScheduling Lambda:")
    print(f"  Success: {lambda_stats['scheduling']['success']}")
    print(f"  Failure: {lambda_stats['scheduling']['failure']}")
    if (
        lambda_stats["scheduling"]["success"] + lambda_stats["scheduling"]["failure"]
        > 0
    ):
        success_rate = (
            lambda_stats["scheduling"]["success"]
            / (
                lambda_stats["scheduling"]["success"]
                + lambda_stats["scheduling"]["failure"]
            )
        ) * 100
        print(f"  Success Rate: {success_rate:.2f}%")

    print("\n" + "=" * 80)


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import os

    os.system("locust -f lambda_loadtest.py")
