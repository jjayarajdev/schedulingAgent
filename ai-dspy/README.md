# DSPy ProjectForce Orchestrator POC

A proof-of-concept implementation of the ProjectForce scheduling assistant using [DSPy](https://github.com/stanfordnlp/dspy) for programmatic prompt optimization.

## Overview

This POC demonstrates how DSPy can replace hand-crafted prompts with:
- **Signatures**: Declarative I/O specifications
- **Modules**: Composable LLM programs
- **Teleprompters**: Automatic prompt optimization
- **Assertions**: Learned guardrails

## Structure

```
dspy-poc/
├── config.py           # DSPy configuration (Claude/Bedrock)
├── signatures.py       # Input/output definitions
├── modules.py          # DSPy modules (classifier, extractor, etc.)
├── training_data.py    # Examples for optimization
├── optimize.py         # Prompt optimization scripts
├── main.py             # Demo and interactive mode
└── requirements.txt    # Dependencies
```

## Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Set API key
export ANTHROPIC_API_KEY="your-key-here"
```

## Quick Start

### Run All Demos
```bash
python main.py --demo all
```

### Interactive Mode
```bash
python main.py --demo interactive
```

### Optimize Classifier
```bash
python optimize.py --component classifier --save optimized_classifier.json
```

## Components

### 1. Intent Classifier
Classifies user messages into:
- **scheduling**: list_projects, get_available_dates, confirm_appointment, etc.
- **information**: get_weather, get_project_details
- **chitchat**: greet, help, general

### 2. Entity Extractor
Extracts structured parameters:
- project_id, category, date, time, location, status_filter

### 3. Weather Resolver
Resolves location and date from workflow context when not explicitly specified.

### 4. Action Guard
Validates and corrects classification errors:
- Prevents auto-scheduling without explicit request
- Handles context-dependent corrections

## DSPy vs Current Implementation

| Current | DSPy |
|---------|------|
| Hand-crafted prompts in `classifier.py` | `IntentClassifier` signature with auto-optimization |
| Manual few-shot examples | `BootstrapFewShot` selects best examples |
| Hard-coded guards in `action_guards.py` | `dspy.Assert` learns constraints |
| Separate enricher prompts | `EntityExtractor` with structured output |

## Optimization

DSPy can automatically optimize prompts using your examples:

```python
from dspy.teleprompt import BootstrapFewShot
from modules import ProjectForceClassifier
from training_data import get_trainset

optimizer = BootstrapFewShot(
    metric=classification_accuracy,
    max_bootstrapped_demos=4
)

optimized = optimizer.compile(
    ProjectForceClassifier(),
    trainset=get_trainset('classification')
)
```

## Adding Training Examples

Edit `training_data.py` to add more examples:

```python
dspy.Example(
    message="your user message",
    conversation_summary="context",
    intent="scheduling",
    action="list_projects",
    confidence="high",
    reasoning="explanation"
).with_inputs("message", "conversation_summary")
```

## Integration Path

To integrate with the existing orchestrator:

1. **Phase 1**: Use DSPy for classification only
   - Replace `classifier.py` with DSPy module
   - Keep existing guards and enricher

2. **Phase 2**: Add entity extraction
   - Replace `sonnet_enricher.py` with DSPy module
   - Use structured output

3. **Phase 3**: Full pipeline
   - Use `ProjectForceOrchestrator` module
   - Train with real conversation logs

## Resources

- [DSPy Documentation](https://dspy-docs.vercel.app/)
- [DSPy GitHub](https://github.com/stanfordnlp/dspy)
- [DSPy Paper](https://arxiv.org/abs/2310.03714)
