"""
DSPy ProjectForce Orchestrator Demo

Run this to test the DSPy-based orchestrator pipeline.
"""
import json
import dspy
from config import configure_dspy
from modules import (
    ProjectForceClassifier,
    ProjectForceEntityExtractor,
    ProjectForceWeatherResolver,
    ProjectForceOrchestrator,
    ProjectForceOrchestratorWithAssertions
)


def demo_classifier():
    """Demo the intent classifier."""
    print("\n" + "=" * 60)
    print("INTENT CLASSIFIER DEMO")
    print("=" * 60)

    classifier = ProjectForceClassifier()

    test_messages = [
        ("list my projects", ""),
        ("schedule my decking project", ""),
        ("what's the weather like", "Viewing time slots for Jan 6 in Minneapolis"),
        ("just the kitchen ones", "Assistant showed 10 projects"),
        ("8 AM please", "Time slots shown: 8 AM, 8:30 AM, 1 PM"),
        ("hi", ""),
    ]

    for message, context in test_messages:
        result = classifier(message=message, conversation_summary=context)
        print(f"\nMessage: '{message}'")
        print(f"Context: '{context}'")
        print(f"  Intent: {result.intent}")
        print(f"  Action: {result.action}")
        print(f"  Confidence: {result.confidence}")
        print(f"  Reasoning: {result.reasoning[:100]}...")


def demo_entity_extractor():
    """Demo entity extraction."""
    print("\n" + "=" * 60)
    print("ENTITY EXTRACTOR DEMO")
    print("=" * 60)

    extractor = ProjectForceEntityExtractor()

    test_cases = [
        {
            "message": "schedule project 9000489",
            "action": "get_available_dates",
            "available_projects": '[{"id": "9000489", "category": "Decking"}]',
            "workflow_context": "{}"
        },
        {
            "message": "January 6th",
            "action": "get_time_slots",
            "available_projects": "[]",
            "workflow_context": '{"project_id": "9000489", "city": "Minneapolis", "state": "MN"}'
        },
        {
            "message": "show my scheduled appointments",
            "action": "list_projects",
            "available_projects": "[]",
            "workflow_context": "{}"
        }
    ]

    for case in test_cases:
        result = extractor(**case)
        print(f"\nMessage: '{case['message']}'")
        print(f"Action: {case['action']}")
        print(f"  Extracted:")
        print(f"    project_id: {result.project_id}")
        print(f"    category: {result.category}")
        print(f"    date: {result.date}")
        print(f"    time: {result.time}")
        print(f"    location: {result.location}")
        print(f"    status_filter: {result.status_filter}")


def demo_weather_resolver():
    """Demo weather context resolution."""
    print("\n" + "=" * 60)
    print("WEATHER CONTEXT RESOLVER DEMO")
    print("=" * 60)

    resolver = ProjectForceWeatherResolver()

    test_cases = [
        {
            "message": "what's the weather like",
            "workflow_context": json.dumps({
                "project_id": "9000489",
                "city": "Minneapolis",
                "state": "MN",
                "date": "2026-01-06",
                "category": "Decking"
            }),
            "conversation_summary": "User viewing time slots for Decking project"
        },
        {
            "message": "how is the weather for tomorrow",
            "workflow_context": json.dumps({
                "project_id": "9000407",
                "city": "Chicago",
                "state": "IL"
            }),
            "conversation_summary": ""
        }
    ]

    for case in test_cases:
        result = resolver(**case)
        print(f"\nMessage: '{case['message']}'")
        print(f"Workflow: {case['workflow_context'][:50]}...")
        print(f"  Location: {result.location}")
        print(f"  Target Date: {result.target_date}")
        print(f"  Reasoning: {result.reasoning}")


def demo_full_pipeline():
    """Demo the full orchestrator pipeline."""
    print("\n" + "=" * 60)
    print("FULL ORCHESTRATOR PIPELINE DEMO")
    print("=" * 60)

    orchestrator = ProjectForceOrchestrator()

    # Simulate a conversation flow
    conversation = [
        {
            "message": "list my projects",
            "workflow_context": "{}",
            "workflow_stage": "none",
            "available_projects": json.dumps([
                {"id": "9000489", "category": "Decking", "status": "Ready To Schedule"},
                {"id": "9000407", "category": "Kitchen Sink", "status": "Ready To Schedule"}
            ])
        },
        {
            "message": "schedule the decking one",
            "workflow_context": json.dumps({"project_ids": ["9000489", "9000407"]}),
            "workflow_stage": "listing_projects",
            "previous_action": "list_projects",
            "available_projects": json.dumps([
                {"id": "9000489", "category": "Decking", "status": "Ready To Schedule"}
            ])
        },
        {
            "message": "January 6th",
            "workflow_context": json.dumps({
                "project_id": "9000489",
                "city": "Minneapolis",
                "state": "MN",
                "category": "Decking"
            }),
            "workflow_stage": "awaiting_date_selection",
            "previous_action": "get_available_dates"
        },
        {
            "message": "what's the weather like",
            "workflow_context": json.dumps({
                "project_id": "9000489",
                "city": "Minneapolis",
                "state": "MN",
                "date": "2026-01-06",
                "category": "Decking"
            }),
            "workflow_stage": "awaiting_time_selection",
            "previous_action": "get_time_slots"
        }
    ]

    for i, turn in enumerate(conversation):
        print(f"\n--- Turn {i+1} ---")
        print(f"User: {turn['message']}")

        result = orchestrator(
            message=turn["message"],
            workflow_context=turn.get("workflow_context", "{}"),
            workflow_stage=turn.get("workflow_stage", "none"),
            previous_action=turn.get("previous_action", ""),
            available_projects=turn.get("available_projects", "[]")
        )

        print(f"Classification: {result['classification']['action']} "
              f"({result['classification']['confidence']})")

        if result['guard']['was_corrected']:
            print(f"Guard corrected: {result['guard']['guard_reason']}")

        print(f"Final Action: {result['final_action']}")
        print(f"Entities: {json.dumps({k: v for k, v in result['entities'].items() if v}, indent=2)}")

        if 'weather_context' in result:
            print(f"Weather: {result['weather_context']['location']} on {result['weather_context']['target_date']}")


def interactive_mode():
    """Run interactive demo."""
    print("\n" + "=" * 60)
    print("INTERACTIVE MODE")
    print("=" * 60)
    print("Type messages to test the orchestrator. Type 'quit' to exit.")
    print("Type 'reset' to clear context.")

    orchestrator = ProjectForceOrchestrator()
    workflow_context = {}
    previous_action = ""
    workflow_stage = "none"

    while True:
        try:
            message = input("\nYou: ").strip()

            if message.lower() == 'quit':
                break
            elif message.lower() == 'reset':
                workflow_context = {}
                previous_action = ""
                workflow_stage = "none"
                print("Context reset.")
                continue

            result = orchestrator(
                message=message,
                workflow_context=json.dumps(workflow_context),
                workflow_stage=workflow_stage,
                previous_action=previous_action
            )

            print(f"\nIntent: {result['classification']['intent']}")
            print(f"Action: {result['final_action']}")
            print(f"Entities: {result['entities']}")

            # Update context for next turn
            previous_action = result['final_action']

        except KeyboardInterrupt:
            break

    print("\nGoodbye!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="DSPy ProjectForce Demo")
    parser.add_argument(
        "--demo",
        choices=["classifier", "extractor", "weather", "full", "interactive", "all"],
        default="all",
        help="Which demo to run"
    )

    args = parser.parse_args()

    # Configure DSPy
    print("Configuring DSPy with Claude...")
    configure_dspy()

    if args.demo == "classifier" or args.demo == "all":
        demo_classifier()

    if args.demo == "extractor" or args.demo == "all":
        demo_entity_extractor()

    if args.demo == "weather" or args.demo == "all":
        demo_weather_resolver()

    if args.demo == "full" or args.demo == "all":
        demo_full_pipeline()

    if args.demo == "interactive":
        interactive_mode()

    print("\n" + "=" * 60)
    print("DEMO COMPLETE")
    print("=" * 60)
