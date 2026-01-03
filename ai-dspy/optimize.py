"""
DSPy Optimization for ProjectForce Orchestrator

Uses teleprompters to automatically optimize prompts
based on training examples and evaluation metrics.
"""
import dspy
from dspy.teleprompt import BootstrapFewShot, BootstrapFewShotWithRandomSearch
from dspy.evaluate import Evaluate
import json
from typing import List

from config import configure_dspy
from modules import (
    ProjectForceClassifier,
    ProjectForceEntityExtractor,
    ProjectForceWeatherResolver,
    ProjectForceGuard,
    ProjectForceOrchestrator,
    ProjectForceDateInterpreter,
    ProjectForceContextResolver,
    ProjectForceResponseStyler,
    ProjectForceSlotRanker
)
from training_data import get_trainset


# =============================================================================
# EVALUATION METRICS
# =============================================================================

def classification_accuracy(example, prediction, trace=None):
    """
    Metric for intent classification.
    Returns 1.0 if both intent and action match, 0.5 if only intent matches.
    """
    intent_match = example.intent.lower() == prediction.intent.lower()
    action_match = example.action.lower() == prediction.action.lower()

    if intent_match and action_match:
        return 1.0
    elif intent_match:
        return 0.5
    else:
        return 0.0


def entity_extraction_accuracy(example, prediction, trace=None):
    """
    Metric for entity extraction.
    Returns fraction of correctly extracted entities.
    """
    fields = ['project_id', 'category', 'date', 'time', 'location', 'status_filter']
    correct = 0
    total = 0

    for field in fields:
        expected = getattr(example, field, "")
        predicted = getattr(prediction, field, "")

        # Only count non-empty expected values
        if expected:
            total += 1
            if expected.lower().strip() == predicted.lower().strip():
                correct += 1

    return correct / total if total > 0 else 1.0


def weather_context_accuracy(example, prediction, trace=None):
    """
    Metric for weather context resolution.
    Returns 1.0 if both location and date match.
    """
    location_match = example.location.lower() == prediction.location.lower()
    date_match = example.target_date == prediction.target_date

    if location_match and date_match:
        return 1.0
    elif location_match or date_match:
        return 0.5
    else:
        return 0.0


def guard_accuracy(example, prediction, trace=None):
    """
    Metric for action guard.
    Returns 1.0 if final action matches.
    """
    return 1.0 if example.final_action == prediction.final_action else 0.0


def date_interpreter_accuracy(example, prediction, trace=None):
    """
    Metric for date interpretation.
    Returns 1.0 if both start and end dates match.
    """
    start_match = example.start_date == prediction.start_date
    end_match = example.end_date == prediction.end_date

    if start_match and end_match:
        return 1.0
    elif start_match or end_match:
        return 0.5
    else:
        return 0.0


def context_resolver_accuracy(example, prediction, trace=None):
    """
    Metric for context resolution.
    Returns 1.0 if resolution type and confidence match.
    """
    try:
        # Parse JSON entities
        expected_entities = json.loads(example.resolved_entities)
        predicted_entities = json.loads(prediction.resolved_entities)

        # Check if key entities match
        key_fields = ['project_id', 'time', 'date']
        matches = 0
        total = 0

        for field in key_fields:
            if field in expected_entities:
                total += 1
                if expected_entities.get(field) == predicted_entities.get(field):
                    matches += 1

        if total == 0:
            return 1.0 if example.resolution_type == prediction.resolution_type else 0.5

        return matches / total
    except:
        return 0.0


def response_style_accuracy(example, prediction, trace=None):
    """
    Metric for response styling.
    Simple check if styled response is appropriate length for channel.
    """
    channel = example.channel
    styled = prediction.styled_response

    if channel == "sms":
        # SMS should be short (under 160 chars)
        return 1.0 if len(styled) < 160 else 0.5
    elif channel == "voice":
        # Voice should be conversational (under 200 chars, no markdown)
        has_markdown = any(c in styled for c in ['**', '##', '|', '•'])
        return 1.0 if len(styled) < 200 and not has_markdown else 0.5
    else:  # chat
        return 1.0  # Chat can be any format


def slot_ranker_accuracy(example, prediction, trace=None):
    """
    Metric for slot ranking.
    Returns 1.0 if recommendation matches.
    """
    return 1.0 if example.recommendation == prediction.recommendation else 0.0


# =============================================================================
# OPTIMIZATION FUNCTIONS
# =============================================================================

def optimize_classifier(trainset: List = None, num_candidates: int = 5):
    """
    Optimize the intent classifier using BootstrapFewShot.

    This finds the best few-shot examples to include in the prompt.
    """
    if trainset is None:
        trainset = get_trainset('classification')

    # Split into train/dev
    train_size = int(len(trainset) * 0.8)
    train_examples = trainset[:train_size]
    dev_examples = trainset[train_size:]

    print(f"Training classifier with {len(train_examples)} examples...")
    print(f"Dev set: {len(dev_examples)} examples")

    # Create optimizer
    optimizer = BootstrapFewShot(
        metric=classification_accuracy,
        max_bootstrapped_demos=4,
        max_labeled_demos=4
    )

    # Compile (optimize) the classifier
    classifier = ProjectForceClassifier()
    optimized_classifier = optimizer.compile(
        classifier,
        trainset=train_examples
    )

    # Evaluate on dev set
    evaluator = Evaluate(
        devset=dev_examples,
        metric=classification_accuracy,
        num_threads=1,
        display_progress=True
    )

    result = evaluator(optimized_classifier)
    # DSPy returns (correct_count / total) as percentage already in the logs
    # Extract numeric score - could be EvaluationResult or float
    if hasattr(result, 'score'):
        score = result.score
    else:
        score = float(result) / len(dev_examples)  # Convert count to ratio
    print(f"Dev set accuracy: {score:.2%}")

    return optimized_classifier


def optimize_entity_extractor(trainset: List = None):
    """Optimize entity extraction module."""
    if trainset is None:
        trainset = get_trainset('entity_extraction')

    train_size = int(len(trainset) * 0.8)
    train_examples = trainset[:train_size]

    optimizer = BootstrapFewShot(
        metric=entity_extraction_accuracy,
        max_bootstrapped_demos=3
    )

    extractor = ProjectForceEntityExtractor()
    optimized = optimizer.compile(extractor, trainset=train_examples)

    return optimized


def optimize_weather_resolver(trainset: List = None):
    """Optimize weather context resolver."""
    if trainset is None:
        trainset = get_trainset('weather_context')

    optimizer = BootstrapFewShot(
        metric=weather_context_accuracy,
        max_bootstrapped_demos=3
    )

    resolver = ProjectForceWeatherResolver()
    optimized = optimizer.compile(resolver, trainset=trainset)

    return optimized


def optimize_date_interpreter(trainset: List = None):
    """Optimize date interpreter module."""
    if trainset is None:
        trainset = get_trainset('date_interpreter')

    print(f"Training date interpreter with {len(trainset)} examples...")

    optimizer = BootstrapFewShot(
        metric=date_interpreter_accuracy,
        max_bootstrapped_demos=4
    )

    interpreter = ProjectForceDateInterpreter()
    optimized = optimizer.compile(interpreter, trainset=trainset)

    return optimized


def optimize_context_resolver(trainset: List = None):
    """Optimize context resolver module."""
    if trainset is None:
        trainset = get_trainset('context_resolver')

    print(f"Training context resolver with {len(trainset)} examples...")

    optimizer = BootstrapFewShot(
        metric=context_resolver_accuracy,
        max_bootstrapped_demos=4
    )

    resolver = ProjectForceContextResolver()
    optimized = optimizer.compile(resolver, trainset=trainset)

    return optimized


def optimize_response_styler(trainset: List = None):
    """Optimize response styler module."""
    if trainset is None:
        trainset = get_trainset('response_style')

    print(f"Training response styler with {len(trainset)} examples...")

    optimizer = BootstrapFewShot(
        metric=response_style_accuracy,
        max_bootstrapped_demos=4
    )

    styler = ProjectForceResponseStyler()
    optimized = optimizer.compile(styler, trainset=trainset)

    return optimized


def optimize_slot_ranker(trainset: List = None):
    """Optimize slot ranker module."""
    if trainset is None:
        trainset = get_trainset('slot_ranker')

    print(f"Training slot ranker with {len(trainset)} examples...")

    optimizer = BootstrapFewShot(
        metric=slot_ranker_accuracy,
        max_bootstrapped_demos=4
    )

    ranker = ProjectForceSlotRanker()
    optimized = optimizer.compile(ranker, trainset=trainset)

    return optimized


def optimize_full_pipeline():
    """
    Optimize the full orchestrator pipeline.

    Uses BootstrapFewShotWithRandomSearch for better optimization.
    """
    print("=" * 60)
    print("OPTIMIZING FULL PROJECTFORCE PIPELINE")
    print("=" * 60)

    # Optimize each component
    print("\n1. Optimizing Classifier...")
    opt_classifier = optimize_classifier()

    print("\n2. Optimizing Entity Extractor...")
    opt_extractor = optimize_entity_extractor()

    print("\n3. Optimizing Weather Resolver...")
    opt_weather = optimize_weather_resolver()

    # Create optimized orchestrator
    orchestrator = ProjectForceOrchestrator()
    orchestrator.classifier = opt_classifier
    orchestrator.extractor = opt_extractor
    orchestrator.weather_resolver = opt_weather

    print("\n" + "=" * 60)
    print("OPTIMIZATION COMPLETE")
    print("=" * 60)

    return orchestrator


# =============================================================================
# SAVE/LOAD OPTIMIZED MODELS
# =============================================================================

def save_optimized_module(module, filepath: str):
    """Save optimized module to file."""
    module.save(filepath)
    print(f"Saved optimized module to: {filepath}")


def load_optimized_module(module_class, filepath: str):
    """Load optimized module from file."""
    module = module_class()
    module.load(filepath)
    print(f"Loaded optimized module from: {filepath}")
    return module


# =============================================================================
# OPTIMIZE ALL MODULES
# =============================================================================

def optimize_all_modules(save_dir: str = "."):
    """
    Optimize all DSPy modules and save to files.

    This is the recommended way to optimize all modules at once.
    """
    print("=" * 60)
    print("OPTIMIZING ALL PROJECTFORCE DSPy MODULES")
    print("=" * 60)

    results = {}

    # 1. Classifier (most important)
    print("\n1. Optimizing Classifier...")
    opt_classifier = optimize_classifier()
    opt_classifier.save(f"{save_dir}/optimized_classifier.json")
    results['classifier'] = True
    print(f"   Saved to {save_dir}/optimized_classifier.json")

    # 2. Entity Extractor
    print("\n2. Optimizing Entity Extractor...")
    opt_extractor = optimize_entity_extractor()
    opt_extractor.save(f"{save_dir}/optimized_extractor.json")
    results['extractor'] = True
    print(f"   Saved to {save_dir}/optimized_extractor.json")

    # 3. Weather Resolver
    print("\n3. Optimizing Weather Resolver...")
    opt_weather = optimize_weather_resolver()
    opt_weather.save(f"{save_dir}/optimized_weather.json")
    results['weather'] = True
    print(f"   Saved to {save_dir}/optimized_weather.json")

    # 4. Date Interpreter
    print("\n4. Optimizing Date Interpreter...")
    opt_date = optimize_date_interpreter()
    opt_date.save(f"{save_dir}/optimized_date_interpreter.json")
    results['date_interpreter'] = True
    print(f"   Saved to {save_dir}/optimized_date_interpreter.json")

    # 5. Context Resolver
    print("\n5. Optimizing Context Resolver...")
    opt_context = optimize_context_resolver()
    opt_context.save(f"{save_dir}/optimized_context_resolver.json")
    results['context_resolver'] = True
    print(f"   Saved to {save_dir}/optimized_context_resolver.json")

    # 6. Response Styler
    print("\n6. Optimizing Response Styler...")
    opt_styler = optimize_response_styler()
    opt_styler.save(f"{save_dir}/optimized_response_styler.json")
    results['response_styler'] = True
    print(f"   Saved to {save_dir}/optimized_response_styler.json")

    # 7. Slot Ranker
    print("\n7. Optimizing Slot Ranker...")
    opt_ranker = optimize_slot_ranker()
    opt_ranker.save(f"{save_dir}/optimized_slot_ranker.json")
    results['slot_ranker'] = True
    print(f"   Saved to {save_dir}/optimized_slot_ranker.json")

    print("\n" + "=" * 60)
    print("OPTIMIZATION COMPLETE")
    print("=" * 60)
    print(f"\nOptimized {len(results)} modules:")
    for name, success in results.items():
        status = "✓" if success else "✗"
        print(f"  {status} {name}")

    return results


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Optimize DSPy modules")
    parser.add_argument(
        "--component",
        choices=[
            "classifier", "extractor", "weather",
            "date", "context", "styler", "ranker",
            "full", "all"
        ],
        default="classifier",
        help="Which component to optimize"
    )
    parser.add_argument(
        "--save",
        type=str,
        default=None,
        help="Path to save optimized module (or directory for --all)"
    )

    args = parser.parse_args()

    # Configure DSPy
    print("Configuring DSPy with Claude...")
    configure_dspy()

    # Run optimization
    if args.component == "classifier":
        optimized = optimize_classifier()
    elif args.component == "extractor":
        optimized = optimize_entity_extractor()
    elif args.component == "weather":
        optimized = optimize_weather_resolver()
    elif args.component == "date":
        optimized = optimize_date_interpreter()
    elif args.component == "context":
        optimized = optimize_context_resolver()
    elif args.component == "styler":
        optimized = optimize_response_styler()
    elif args.component == "ranker":
        optimized = optimize_slot_ranker()
    elif args.component == "full":
        optimized = optimize_full_pipeline()
    elif args.component == "all":
        save_dir = args.save or "."
        optimize_all_modules(save_dir)
        optimized = None  # Already saved

    # Save if requested (for single component)
    if args.save and optimized:
        save_optimized_module(optimized, args.save)
