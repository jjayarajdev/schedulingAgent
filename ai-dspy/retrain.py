#!/usr/bin/env python3
"""
DSPy Retraining Script for ProjectForce Orchestrator

This script:
1. Fetches new training examples from S3 logs
2. Merges with existing training data
3. Re-runs DSPy optimization
4. Uploads optimized models to S3
5. Optionally triggers Lambda deployment

Usage:
    # Full retraining with S3 data
    python retrain.py --fetch-from-s3 --upload

    # Retrain with local data only
    python retrain.py --local-only

    # Just upload existing optimized models to S3
    python retrain.py --upload-only

Environment Variables:
    AWS_PROFILE: AWS profile to use
    TRAINING_LOG_BUCKET: S3 bucket with training logs
    DSPY_MODEL_BUCKET: S3 bucket for optimized models
    ANTHROPIC_API_KEY: API key for DSPy optimization
"""
import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any

import boto3
from dotenv import load_dotenv

load_dotenv()

# Configuration
TRAINING_LOG_BUCKET = os.environ.get('TRAINING_LOG_BUCKET', 'projectforce-training-logs')
TRAINING_LOG_PREFIX = os.environ.get('TRAINING_LOG_PREFIX', 'classification-logs/')
DSPY_MODEL_BUCKET = os.environ.get('DSPY_MODEL_BUCKET', 'projectforce-dspy-models')
DSPY_MODEL_PREFIX = os.environ.get('DSPY_MODEL_PREFIX', 'optimized/')

# Import local modules
from config import configure_dspy
from training_data import CLASSIFICATION_EXAMPLES, ENTITY_EXAMPLES, WEATHER_CONTEXT_EXAMPLES, GUARD_EXAMPLES
from optimize import optimize_classifier, optimize_entity_extractor, optimize_weather_resolver


def fetch_training_logs(days: int = 30, min_examples: int = 10) -> List[Dict]:
    """
    Fetch training examples from S3 logs.

    Args:
        days: Number of days of logs to fetch
        min_examples: Minimum examples required

    Returns:
        List of training examples in DSPy format
    """
    print(f"Fetching training logs from last {days} days...")

    s3 = boto3.client('s3')
    examples = []

    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    current = start_date
    while current <= end_date:
        prefix = (
            f"{TRAINING_LOG_PREFIX}"
            f"year={current.year}/"
            f"month={current.month:02d}/"
            f"day={current.day:02d}/"
        )

        try:
            response = s3.list_objects_v2(
                Bucket=TRAINING_LOG_BUCKET,
                Prefix=prefix,
                MaxKeys=1000
            )

            for obj in response.get('Contents', []):
                try:
                    data = s3.get_object(
                        Bucket=TRAINING_LOG_BUCKET,
                        Key=obj['Key']
                    )
                    entry = json.loads(data['Body'].read().decode('utf-8'))
                    examples.append(entry)
                except Exception as e:
                    print(f"  Warning: Could not read {obj['Key']}: {e}")

        except Exception as e:
            print(f"  Warning: Could not list {prefix}: {e}")

        current += timedelta(days=1)

    print(f"  Found {len(examples)} logged examples")

    if len(examples) < min_examples:
        print(f"  Warning: Less than {min_examples} examples found")

    return examples


def convert_logs_to_dspy_format(logs: List[Dict]) -> Dict[str, List]:
    """
    Convert raw logs to DSPy training format.

    Prioritizes examples with feedback (corrections).
    """
    import dspy

    classification_examples = []
    entity_examples = []

    for log in logs:
        # Get the correct values (from feedback if available)
        feedback = log.get('feedback', {})
        classification = log.get('classification', {})

        intent = feedback.get('correct_intent') or classification.get('intent')
        action = feedback.get('correct_action') or classification.get('action')

        if not intent or not action:
            continue

        # Skip low confidence unless corrected
        if classification.get('confidence') == 'low' and not feedback:
            continue

        # Create classification example
        try:
            example = dspy.Example(
                message=log['message'],
                conversation_summary=log.get('conversation_context', ''),
                intent=intent,
                action=action,
                confidence='high' if feedback else classification.get('confidence', 'medium'),
                reasoning=classification.get('reasoning', '')
            ).with_inputs("message", "conversation_summary")

            classification_examples.append(example)
        except Exception as e:
            print(f"  Warning: Could not create example: {e}")

    print(f"  Converted {len(classification_examples)} classification examples")

    return {
        'classification': classification_examples,
        'entity_extraction': entity_examples
    }


def merge_training_data(
    existing: List,
    new_examples: List,
    max_total: int = 500,
    prioritize_corrected: bool = True
) -> List:
    """
    Merge existing training data with new examples.

    Args:
        existing: Existing training examples
        new_examples: New examples from logs
        max_total: Maximum total examples to keep
        prioritize_corrected: Keep corrected examples over uncorrected

    Returns:
        Merged training set
    """
    # Deduplicate by message
    seen_messages = set()
    merged = []

    # Add corrected examples first (highest priority)
    for ex in new_examples:
        msg = getattr(ex, 'message', '')
        if msg and msg not in seen_messages:
            seen_messages.add(msg)
            merged.append(ex)

    # Add existing examples
    for ex in existing:
        msg = getattr(ex, 'message', '')
        if msg and msg not in seen_messages:
            seen_messages.add(msg)
            merged.append(ex)

    # Trim to max
    if len(merged) > max_total:
        merged = merged[:max_total]

    print(f"  Merged dataset: {len(merged)} examples")
    return merged


def run_optimization(trainset: List, component: str) -> Any:
    """Run DSPy optimization for a component."""
    print(f"\nOptimizing {component}...")

    if component == 'classifier':
        return optimize_classifier(trainset)
    elif component == 'extractor':
        return optimize_entity_extractor(trainset)
    elif component == 'weather':
        return optimize_weather_resolver(trainset)
    else:
        raise ValueError(f"Unknown component: {component}")


def upload_models_to_s3(models_dir: str = ".") -> Dict[str, str]:
    """
    Upload optimized models to S3.

    Returns:
        Dict of model name -> S3 URI
    """
    print("\nUploading optimized models to S3...")

    s3 = boto3.client('s3')
    uploaded = {}

    model_files = [
        'optimized_classifier.json',
        'optimized_extractor.json',
        'optimized_weather.json'
    ]

    for filename in model_files:
        filepath = os.path.join(models_dir, filename)
        if os.path.exists(filepath):
            key = f"{DSPY_MODEL_PREFIX}{filename}"

            # Add metadata
            with open(filepath, 'r') as f:
                model_data = json.load(f)

            model_data['_metadata'] = {
                'uploaded_at': datetime.utcnow().isoformat(),
                'version': datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            }

            s3.put_object(
                Bucket=DSPY_MODEL_BUCKET,
                Key=key,
                Body=json.dumps(model_data),
                ContentType='application/json',
                Metadata={
                    'uploaded-at': datetime.utcnow().isoformat(),
                    'source': 'retrain-script'
                }
            )

            uri = f"s3://{DSPY_MODEL_BUCKET}/{key}"
            uploaded[filename] = uri
            print(f"  Uploaded {filename} -> {uri}")

    return uploaded


def create_training_report(
    original_count: int,
    new_count: int,
    merged_count: int,
    optimization_results: Dict,
    uploaded_models: Dict
) -> Dict:
    """Create a training report for logging/auditing."""
    report = {
        'timestamp': datetime.utcnow().isoformat(),
        'training_data': {
            'original_examples': original_count,
            'new_from_logs': new_count,
            'merged_total': merged_count
        },
        'optimization': optimization_results,
        'uploaded_models': uploaded_models,
        'status': 'success'
    }

    # Save report
    report_file = f"training_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\nTraining report saved: {report_file}")
    return report


def main():
    parser = argparse.ArgumentParser(description="Retrain DSPy models")

    parser.add_argument('--fetch-from-s3', action='store_true',
                       help='Fetch new examples from S3 training logs')
    parser.add_argument('--days', type=int, default=30,
                       help='Days of logs to fetch (default: 30)')
    parser.add_argument('--local-only', action='store_true',
                       help='Only use local training data')
    parser.add_argument('--upload', action='store_true',
                       help='Upload optimized models to S3')
    parser.add_argument('--upload-only', action='store_true',
                       help='Only upload existing models, skip retraining')
    parser.add_argument('--component', choices=['classifier', 'extractor', 'weather', 'all'],
                       default='all', help='Which component to optimize')
    parser.add_argument('--max-examples', type=int, default=500,
                       help='Maximum training examples')

    args = parser.parse_args()

    print("=" * 60)
    print("DSPy Retraining Script")
    print("=" * 60)

    # Upload only mode
    if args.upload_only:
        uploaded = upload_models_to_s3()
        print(f"\nUploaded {len(uploaded)} models")
        return

    # Configure DSPy
    print("\nConfiguring DSPy...")
    configure_dspy()

    # Gather training data
    original_count = len(CLASSIFICATION_EXAMPLES)
    new_count = 0
    merged_count = original_count

    if args.fetch_from_s3 and not args.local_only:
        # Fetch from S3
        logs = fetch_training_logs(days=args.days)
        new_examples = convert_logs_to_dspy_format(logs)
        new_count = len(new_examples.get('classification', []))

        # Merge with existing
        merged_classification = merge_training_data(
            CLASSIFICATION_EXAMPLES,
            new_examples.get('classification', []),
            max_total=args.max_examples
        )
        merged_count = len(merged_classification)
    else:
        merged_classification = CLASSIFICATION_EXAMPLES
        print(f"\nUsing local training data: {len(merged_classification)} examples")

    # Run optimization
    optimization_results = {}

    if args.component in ['classifier', 'all']:
        try:
            opt_classifier = run_optimization(merged_classification, 'classifier')
            opt_classifier.save('optimized_classifier.json')
            optimization_results['classifier'] = 'success'
        except Exception as e:
            optimization_results['classifier'] = f'error: {e}'
            print(f"  Classifier optimization failed: {e}")

    if args.component in ['extractor', 'all']:
        try:
            opt_extractor = run_optimization(ENTITY_EXAMPLES, 'extractor')
            opt_extractor.save('optimized_extractor.json')
            optimization_results['extractor'] = 'success'
        except Exception as e:
            optimization_results['extractor'] = f'error: {e}'
            print(f"  Extractor optimization failed: {e}")

    if args.component in ['weather', 'all']:
        try:
            opt_weather = run_optimization(WEATHER_CONTEXT_EXAMPLES, 'weather')
            opt_weather.save('optimized_weather.json')
            optimization_results['weather'] = 'success'
        except Exception as e:
            optimization_results['weather'] = f'error: {e}'
            print(f"  Weather optimization failed: {e}")

    # Upload to S3
    uploaded_models = {}
    if args.upload:
        uploaded_models = upload_models_to_s3()

    # Create report
    report = create_training_report(
        original_count=original_count,
        new_count=new_count,
        merged_count=merged_count,
        optimization_results=optimization_results,
        uploaded_models=uploaded_models
    )

    print("\n" + "=" * 60)
    print("RETRAINING COMPLETE")
    print("=" * 60)
    print(f"Original examples: {original_count}")
    print(f"New from logs: {new_count}")
    print(f"Merged total: {merged_count}")
    print(f"Components optimized: {list(optimization_results.keys())}")
    if uploaded_models:
        print(f"Models uploaded to: s3://{DSPY_MODEL_BUCKET}/{DSPY_MODEL_PREFIX}")


if __name__ == "__main__":
    main()
