"""
Evaluate optimized DSPy modules vs baseline.
"""
import dspy
from config import configure_dspy
from modules import ProjectForceClassifier, ProjectForceEntityExtractor, ProjectForceWeatherResolver
from training_data import get_trainset


def load_optimized_classifier():
    """Load the optimized classifier from JSON."""
    classifier = ProjectForceClassifier()
    classifier.load("optimized_classifier.json")
    return classifier


def load_optimized_extractor():
    """Load the optimized entity extractor from JSON."""
    extractor = ProjectForceEntityExtractor()
    extractor.load("optimized_extractor.json")
    return extractor


def load_optimized_weather():
    """Load the optimized weather resolver from JSON."""
    resolver = ProjectForceWeatherResolver()
    resolver.load("optimized_weather.json")
    return resolver


def evaluate_classifier(classifier, test_examples, label=""):
    """Evaluate classifier on test set."""
    correct = 0
    total = len(test_examples)

    for ex in test_examples:
        result = classifier(message=ex.message, conversation_summary=ex.conversation_summary)
        if result.intent.lower() == ex.intent.lower() and result.action.lower() == ex.action.lower():
            correct += 1

    accuracy = correct / total if total > 0 else 0
    print(f"{label}: {correct}/{total} = {accuracy:.1%}")
    return accuracy


def compare_classifiers():
    """Compare baseline vs optimized classifier."""
    print("=" * 60)
    print("CLASSIFIER COMPARISON: Baseline vs Optimized")
    print("=" * 60)

    # Get test examples (last 20%)
    all_examples = get_trainset('classification')
    test_start = int(len(all_examples) * 0.8)
    test_examples = all_examples[test_start:]

    print(f"\nTest set: {len(test_examples)} examples")

    # Baseline
    baseline = ProjectForceClassifier()
    baseline_acc = evaluate_classifier(baseline, test_examples, "Baseline")

    # Optimized
    optimized = load_optimized_classifier()
    optimized_acc = evaluate_classifier(optimized, test_examples, "Optimized")

    improvement = (optimized_acc - baseline_acc) * 100
    print(f"\nImprovement: {improvement:+.1f} percentage points")

    return baseline_acc, optimized_acc


def show_learned_demos():
    """Display the few-shot examples DSPy learned."""
    import json

    print("\n" + "=" * 60)
    print("LEARNED FEW-SHOT EXAMPLES")
    print("=" * 60)

    with open("optimized_classifier.json", "r") as f:
        data = json.load(f)

    demos = data.get("classifier.predict", {}).get("demos", [])

    print(f"\nDSPy selected {len(demos)} optimal few-shot examples:\n")

    for i, demo in enumerate(demos, 1):
        print(f"{i}. Message: \"{demo['message']}\"")
        print(f"   Intent: {demo['intent']} | Action: {demo['action']}")
        print(f"   Reasoning: {demo['reasoning']}")
        print()


def extract_prompts():
    """Extract the optimized prompts for integration."""
    import json

    print("\n" + "=" * 60)
    print("EXTRACTED PROMPTS FOR INTEGRATION")
    print("=" * 60)

    # Classifier
    with open("optimized_classifier.json", "r") as f:
        classifier_data = json.load(f)

    demos = classifier_data.get("classifier.predict", {}).get("demos", [])

    print("\n## Classifier Few-Shot Examples (add to prompt):\n")
    print("```")
    for demo in demos:
        print(f"User: {demo['message']}")
        if demo.get('conversation_summary'):
            print(f"Context: {demo['conversation_summary']}")
        print(f"Reasoning: {demo['reasoning']}")
        print(f"Intent: {demo['intent']}")
        print(f"Action: {demo['action']}")
        print(f"Confidence: {demo['confidence']}")
        print("---")
    print("```")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--compare", action="store_true", help="Compare baseline vs optimized")
    parser.add_argument("--demos", action="store_true", help="Show learned demos")
    parser.add_argument("--extract", action="store_true", help="Extract prompts for integration")
    parser.add_argument("--all", action="store_true", help="Run all evaluations")

    args = parser.parse_args()

    print("Configuring DSPy...")
    configure_dspy()

    if args.all or args.compare:
        compare_classifiers()

    if args.all or args.demos:
        show_learned_demos()

    if args.all or args.extract:
        extract_prompts()

    if not any([args.compare, args.demos, args.extract, args.all]):
        print("Use --compare, --demos, --extract, or --all")
