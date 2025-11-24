"""
Locust Load Testing for Voice Lambda Functions

Tests performance and scalability of voice endpoints under load.

Usage:
    # Run locally
    locust -f locustfile.py --host=https://your-api-gateway-url

    # Run with specific user count
    locust -f locustfile.py --host=https://api.example.com --users=100 --spawn-rate=10

    # Headless mode for CI/CD
    locust -f locustfile.py --host=https://api.example.com --users=50 --spawn-rate=5 --run-time=5m --headless
"""

from locust import HttpUser, task, between, events
from locust.contrib.fasthttp import FastHttpUser
import json
import random
import uuid
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# Test Data Generators
# ============================================================================

class TestDataGenerator:
    """Generates realistic test data for load testing"""

    CUSTOMER_IDS = [f"CUST{i:04d}" for i in range(1, 101)]
    PROJECT_IDS = [f"PRJ-{i:03d}" for i in range(1, 51)]
    PHONE_NUMBERS = [f"+1800555{i:04d}" for i in range(1000, 2000)]

    INTENTS = [
        "Welcome",
        "ProjectInquiry",
        "CheckAvailability",
        "ScheduleAppointment",
        "UrgentRequest"
    ]

    TRANSCRIPTS = {
        "Welcome": [
            "hello",
            "hi there",
            "good morning",
            "hey"
        ],
        "ProjectInquiry": [
            "show me my projects",
            "what projects do I have",
            "list my projects",
            "tell me about my projects"
        ],
        "CheckAvailability": [
            "check availability for project {}",
            "what dates are available for project {}",
            "show me available times for project {}"
        ],
        "ScheduleAppointment": [
            "schedule an appointment for project {}",
            "book an appointment for next Tuesday",
            "I want to schedule project {} for next week"
        ],
        "UrgentRequest": [
            "I need urgent service",
            "this is urgent",
            "emergency appointment needed"
        ]
    }

    @classmethod
    def generate_lex_event(cls, intent_name: str = None) -> dict:
        """Generate realistic Lex V2 event"""

        if intent_name is None:
            intent_name = random.choice(cls.INTENTS)

        session_id = f"load-test-{uuid.uuid4()}"
        customer_id = random.choice(cls.CUSTOMER_IDS)
        phone_number = random.choice(cls.PHONE_NUMBERS)

        # Generate appropriate transcript
        transcripts = cls.TRANSCRIPTS.get(intent_name, ["test"])
        transcript_template = random.choice(transcripts)

        # Fill in project ID if needed
        if '{}' in transcript_template:
            project_id = random.choice(cls.PROJECT_IDS)
            transcript = transcript_template.format(project_id)
        else:
            transcript = transcript_template

        event = {
            "sessionId": session_id,
            "inputTranscript": transcript,
            "sessionState": {
                "sessionAttributes": {
                    "customer_id": customer_id,
                    "customer_phone": phone_number
                },
                "intent": {
                    "name": intent_name,
                    "slots": {},
                    "state": "InProgress"
                }
            },
            "requestAttributes": {
                "CustomerNumber": phone_number
            }
        }

        # Add slots for CheckAvailability
        if intent_name == "CheckAvailability":
            project_id = random.choice(cls.PROJECT_IDS)
            event["sessionState"]["intent"]["slots"] = {
                "ProjectId": {
                    "value": {
                        "interpretedValue": project_id
                    }
                }
            }

        return event

    @classmethod
    def generate_bedrock_request(cls) -> dict:
        """Generate realistic Bedrock bridge request"""

        return {
            "session_id": f"load-test-{uuid.uuid4()}",
            "customer_id": random.choice(cls.CUSTOMER_IDS),
            "input_text": random.choice(cls.TRANSCRIPTS["ScheduleAppointment"]).format(
                random.choice(cls.PROJECT_IDS)
            ),
            "channel": "voice",
            "session_attributes": {
                "customer_id": random.choice(cls.CUSTOMER_IDS)
            }
        }


# ============================================================================
# Locust User Classes
# ============================================================================

class LexFulfillmentUser(FastHttpUser):
    """
    Simulates users calling the Lex Fulfillment Lambda

    Tests simple intent handling (Welcome, ProjectInquiry, CheckAvailability)
    """

    wait_time = between(2, 5)  # Wait 2-5 seconds between requests
    weight = 3  # 3x more likely than Bedrock users (simple intents are more common)

    def on_start(self):
        """Called when a user starts"""
        self.customer_id = random.choice(TestDataGenerator.CUSTOMER_IDS)
        logger.info(f"User started: {self.customer_id}")

    @task(5)
    def welcome_intent(self):
        """Test Welcome intent (most common)"""
        event = TestDataGenerator.generate_lex_event("Welcome")

        with self.client.post(
            "/lex-fulfillment",
            json=event,
            catch_response=True,
            name="Lex: Welcome"
        ) as response:
            if response.status_code == 200:
                response_data = response.json()
                if 'messages' in response_data and len(response_data['messages']) > 0:
                    response.success()
                else:
                    response.failure("Invalid response structure")
            else:
                response.failure(f"Status {response.status_code}")

    @task(3)
    def project_inquiry_intent(self):
        """Test ProjectInquiry intent"""
        event = TestDataGenerator.generate_lex_event("ProjectInquiry")

        with self.client.post(
            "/lex-fulfillment",
            json=event,
            catch_response=True,
            name="Lex: ProjectInquiry"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status {response.status_code}")

    @task(2)
    def check_availability_intent(self):
        """Test CheckAvailability intent"""
        event = TestDataGenerator.generate_lex_event("CheckAvailability")

        with self.client.post(
            "/lex-fulfillment",
            json=event,
            catch_response=True,
            name="Lex: CheckAvailability"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status {response.status_code}")


class BedrockBridgeUser(FastHttpUser):
    """
    Simulates users calling complex intents through Bedrock bridge

    Tests: ScheduleAppointment, UrgentRequest (CPU-intensive operations)
    """

    wait_time = between(3, 8)  # Longer wait for complex intents
    weight = 1  # Less common than simple intents

    def on_start(self):
        """Called when a user starts"""
        self.customer_id = random.choice(TestDataGenerator.CUSTOMER_IDS)
        self.session_id = f"bedrock-test-{uuid.uuid4()}"
        logger.info(f"Bedrock user started: {self.customer_id}")

    @task(3)
    def schedule_appointment(self):
        """Test schedule appointment via Bedrock"""
        request = TestDataGenerator.generate_bedrock_request()

        with self.client.post(
            "/voice-bedrock-bridge",
            json=request,
            catch_response=True,
            name="Bedrock: ScheduleAppointment",
            timeout=30  # Bedrock can be slow
        ) as response:
            if response.status_code == 200:
                response_data = response.json()
                if 'response' in response_data:
                    # Track response time
                    if response.elapsed.total_seconds() < 10:
                        response.success()
                    else:
                        response.failure(f"Slow response: {response.elapsed.total_seconds()}s")
                else:
                    response.failure("Invalid response structure")
            else:
                response.failure(f"Status {response.status_code}")

    @task(1)
    def urgent_request(self):
        """Test urgent request via Bedrock"""
        event = TestDataGenerator.generate_lex_event("UrgentRequest")

        with self.client.post(
            "/lex-fulfillment",
            json=event,
            catch_response=True,
            name="Lex: UrgentRequest (Bedrock handoff)",
            timeout=30
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status {response.status_code}")


class CustomerLookupUser(FastHttpUser):
    """
    Simulates customer lookup operations

    Tests phone number lookup for caller identification
    """

    wait_time = between(1, 3)
    weight = 2  # Common operation (every call starts with lookup)

    @task
    def lookup_by_phone(self):
        """Test customer lookup by phone number"""
        phone_number = random.choice(TestDataGenerator.PHONE_NUMBERS)

        request = {
            "action": "lookup_by_phone",
            "phone_number": phone_number
        }

        with self.client.post(
            "/customer-lookup",
            json=request,
            catch_response=True,
            name="Customer: Lookup by phone"
        ) as response:
            if response.status_code in [200, 404]:  # 404 is OK (customer not found)
                response.success()
            else:
                response.failure(f"Status {response.status_code}")


# ============================================================================
# Event Handlers (Metrics Collection)
# ============================================================================

@events.init_command_line_parser.add_listener
def add_custom_arguments(parser):
    """Add custom command line arguments"""
    parser.add_argument(
        "--test-scenario",
        type=str,
        default="mixed",
        choices=["mixed", "simple", "complex", "lookup"],
        help="Test scenario to run"
    )


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when load test starts"""
    logger.info("=" * 60)
    logger.info("VOICE LAMBDA LOAD TEST STARTED")
    logger.info(f"Target: {environment.host}")
    logger.info(f"Users: {environment.runner.target_user_count if hasattr(environment.runner, 'target_user_count') else 'N/A'}")
    logger.info("=" * 60)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when load test stops"""
    logger.info("=" * 60)
    logger.info("VOICE LAMBDA LOAD TEST COMPLETED")

    if environment.stats.total.fail_ratio > 0.05:  # More than 5% failures
        logger.error(f"⚠️  HIGH FAILURE RATE: {environment.stats.total.fail_ratio * 100:.2f}%")
    else:
        logger.info(f"✅ Success rate: {(1 - environment.stats.total.fail_ratio) * 100:.2f}%")

    logger.info(f"Total requests: {environment.stats.total.num_requests}")
    logger.info(f"RPS: {environment.stats.total.current_rps:.2f}")
    logger.info(f"Avg response time: {environment.stats.total.avg_response_time:.2f}ms")
    logger.info(f"Max response time: {environment.stats.total.max_response_time:.2f}ms")
    logger.info("=" * 60)


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, context, **kwargs):
    """Called after each request"""
    if exception:
        logger.error(f"Request failed: {name} - {exception}")


# ============================================================================
# Custom Load Shapes (Advanced)
# ============================================================================

from locust import LoadTestShape

class StepLoadShape(LoadTestShape):
    """
    Step load pattern: gradually increase load in steps

    1-2 min: 10 users
    2-4 min: 25 users
    4-6 min: 50 users
    6-8 min: 100 users
    8-10 min: 50 users (cooldown)
    """

    step_time = 120  # 2 minutes per step
    step_load = 10
    spawn_rate = 5
    time_limit = 600  # 10 minutes total

    def tick(self):
        run_time = self.get_run_time()

        if run_time > self.time_limit:
            return None

        current_step = (run_time // self.step_time) + 1

        if current_step == 1:
            user_count = 10
        elif current_step == 2:
            user_count = 25
        elif current_step == 3:
            user_count = 50
        elif current_step == 4:
            user_count = 100
        else:
            user_count = 50  # Cooldown

        return (user_count, self.spawn_rate)


class SpikeLoadShape(LoadTestShape):
    """
    Spike load pattern: sudden traffic spikes

    Simulates real-world scenarios like marketing campaigns
    """

    time_limit = 300  # 5 minutes

    def tick(self):
        run_time = self.get_run_time()

        if run_time > self.time_limit:
            return None

        # Normal load: 10 users
        # Spike every 60 seconds to 100 users for 10 seconds
        if int(run_time) % 60 < 10:
            return (100, 20)  # Spike
        else:
            return (10, 5)  # Normal


# ============================================================================
# Usage Examples
# ============================================================================

"""
# Basic load test
locust -f locustfile.py --host=https://api.projectforce.com

# Test with 100 concurrent users
locust -f locustfile.py --host=https://api.projectforce.com --users=100 --spawn-rate=10

# Headless mode for CI/CD
locust -f locustfile.py --host=https://api.projectforce.com --users=50 --spawn-rate=5 --run-time=5m --headless --html=report.html

# Step load test
locust -f locustfile.py --host=https://api.projectforce.com --headless --users=100 --spawn-rate=10 --shape=StepLoadShape

# Spike test
locust -f locustfile.py --host=https://api.projectforce.com --headless --users=100 --spawn-rate=20 --shape=SpikeLoadShape
"""
