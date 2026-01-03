# AI-DSPy: ProjectForce Intelligent Orchestration

DSPy-powered prompt optimization for the ProjectForce scheduling assistant. This module provides optimized few-shot examples that are injected into the orchestrator's prompts at runtime.

## Architecture

```
ai-dspy/
├── config.py              # DSPy LLM configuration (Anthropic/Bedrock)
├── signatures.py          # Input/output type definitions
├── modules.py             # DSPy modules with ChainOfThought reasoning
├── training_data.py       # 296 curated training examples
├── optimize.py            # Optimization scripts (BootstrapFewShot)
├── evaluate.py            # Evaluation metrics and testing
├── retrain.py             # S3-based retraining pipeline
├── optimized_*.json       # 7 optimized model files
└── requirements.txt       # Python dependencies
```

## Optimized Models

| Model | Purpose | Examples |
|-------|---------|----------|
| `optimized_classifier.json` | Intent classification (scheduling/information/chitchat) | 80+ |
| `optimized_extractor.json` | Entity extraction (project_id, date, time, etc.) | 40+ |
| `optimized_weather.json` | Weather context resolution (location, date) | 25+ |
| `optimized_date_interpreter.json` | Natural language date parsing | 21 |
| `optimized_context_resolver.json` | Pronoun/reference resolution | 15 |
| `optimized_response_styler.json` | Channel-specific formatting (voice/sms/chat) | 14 |
| `optimized_slot_ranker.json` | Time slot ranking (weather, preferences) | 10 |

## Setup

### Prerequisites

- Python 3.11+
- Anthropic API key (for optimization)
- AWS credentials (for S3 upload/download)

### Installation

```bash
cd ai-dspy

# Create virtual environment
python -m venv venv
source venv/bin/activate  # macOS/Linux
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Set API key
export ANTHROPIC_API_KEY="your-key-here"
```

## Usage

### Optimize All Models

Run full optimization on all 7 modules:

```bash
python optimize.py --component all --save .
```

This produces:
- `optimized_classifier.json`
- `optimized_extractor.json`
- `optimized_weather.json`
- `optimized_date_interpreter.json`
- `optimized_context_resolver.json`
- `optimized_response_styler.json`
- `optimized_slot_ranker.json`

### Optimize Individual Models

```bash
# Intent classifier
python optimize.py --component classifier --save optimized_classifier.json

# Entity extractor
python optimize.py --component extractor --save optimized_extractor.json

# Weather resolver
python optimize.py --component weather --save optimized_weather.json

# Date interpreter
python optimize.py --component date --save optimized_date_interpreter.json

# Context resolver
python optimize.py --component context --save optimized_context_resolver.json

# Response styler
python optimize.py --component styler --save optimized_response_styler.json

# Slot ranker
python optimize.py --component ranker --save optimized_slot_ranker.json
```

### Upload to S3

After optimization, upload models to S3 for Lambda access:

```bash
# Upload all models
python retrain.py --upload-only

# Or manually:
aws s3 cp optimized_classifier.json s3://pf-syn-dspy-models-dev/optimized/
aws s3 cp optimized_extractor.json s3://pf-syn-dspy-models-dev/optimized/
# ... etc
```

### Interactive Demo

Test the modules interactively:

```bash
python main.py --demo interactive
```

### Evaluate Models

Run evaluation metrics on test data:

```bash
python evaluate.py
```

## Training Data

Training examples are defined in `training_data.py`. Each example follows DSPy's format:

### Classification Example

```python
dspy.Example(
    message="list my projects",
    conversation_summary="",
    intent="scheduling",
    action="list_projects",
    confidence="high",
    reasoning="User explicitly asks to list their projects"
).with_inputs("message", "conversation_summary")
```

### Entity Extraction Example

```python
dspy.Example(
    message="schedule project 90000078 for tomorrow at 2pm",
    action="confirm_appointment",
    available_projects='[{"id": "90000078", "name": "Kitchen Remodel"}]',
    workflow_context='{}',
    project_id="90000078",
    category="",
    date="tomorrow",
    time="2pm",
    location="",
    status_filter=""
).with_inputs("message", "action", "available_projects", "workflow_context")
```

### Weather Context Example

```python
dspy.Example(
    message="what's the weather",
    workflow_context='{"selected_date": "2025-01-15", "project_location": "Miami, FL"}',
    location="Miami, FL",
    target_date="2025-01-15",
    reasoning="Extracted from workflow context"
).with_inputs("message", "workflow_context")
```

### Date Interpreter Example

```python
dspy.Example(
    phrase="next week",
    current_date="2025-01-03",
    start_date="2025-01-06",
    end_date="2025-01-10",
    interpretation="Monday to Friday of next week"
).with_inputs("phrase", "current_date")
```

### Context Resolver Example

```python
dspy.Example(
    message="schedule it for tomorrow",
    conversation_history="User asked about project 90000078 (Kitchen Remodel)",
    entity_type="project",
    resolved_value="90000078",
    reasoning="'it' refers to the project mentioned in conversation"
).with_inputs("message", "conversation_history")
```

### Response Styler Example

```python
dspy.Example(
    raw_response="Available slots: 9:00 AM, 10:30 AM, 2:00 PM",
    channel="voice",
    action_context="scheduling",
    styled_response="I found three available times: 9 AM, 10:30 AM, and 2 PM. Which works best for you?",
    style_notes="Conversational, natural speech"
).with_inputs("raw_response", "channel", "action_context")
```

### Slot Ranker Example

```python
dspy.Example(
    available_slots='["8:00 AM", "10:00 AM", "1:00 PM", "3:00 PM"]',
    user_preference="morning",
    weather_info="Rain expected in afternoon",
    project_type="Outdoor - Decking",
    ranked_slots='["8:00 AM", "10:00 AM", "1:00 PM", "3:00 PM"]',
    recommendation="8:00 AM",
    ranking_reason="Morning preferred + outdoor work should avoid afternoon rain"
).with_inputs("available_slots", "user_preference", "weather_info", "project_type")
```

## Adding New Training Examples

1. **Edit `training_data.py`** - Add examples to the appropriate list:
   - `CLASSIFICATION_EXAMPLES` - Intent classification
   - `ENTITY_EXAMPLES` - Entity extraction
   - `WEATHER_CONTEXT_EXAMPLES` - Weather resolution
   - `DATE_INTERPRETER_EXAMPLES` - Date parsing
   - `CONTEXT_RESOLVER_EXAMPLES` - Reference resolution
   - `RESPONSE_STYLE_EXAMPLES` - Channel formatting
   - `SLOT_RANKER_EXAMPLES` - Time slot ranking

2. **Re-optimize** the affected module:
   ```bash
   python optimize.py --component classifier --save optimized_classifier.json
   ```

3. **Upload** to S3:
   ```bash
   aws s3 cp optimized_classifier.json s3://pf-syn-dspy-models-dev/optimized/
   ```

4. **Test** in Lambda (models are cached, may need cold start or redeploy)

## Retraining from Production Logs

The `retrain.py` script can fetch training data from S3 logs:

```bash
# Full retraining with S3 data
python retrain.py --fetch-from-s3 --upload

# Retrain with local data only
python retrain.py --local-only

# Just upload existing models
python retrain.py --upload-only
```

### Environment Variables for Retraining

```bash
export AWS_PROFILE=pf-aws
export TRAINING_LOG_BUCKET=pf-syn-training-logs-dev
export DSPY_MODEL_BUCKET=pf-syn-dspy-models-dev
export DSPY_MODEL_PREFIX=optimized/
export ANTHROPIC_API_KEY=your-key-here
```

## Integration with Orchestrator

The optimized models are loaded by `lambda/orchestrator/dspy_integration.py`:

```python
from dspy_integration import (
    get_classifier_few_shots,
    get_extractor_few_shots,
    get_weather_few_shots,
    get_date_interpreter_few_shots,
    get_context_resolver_few_shots,
    get_response_style_few_shots,
    get_slot_ranker_few_shots
)

# Get few-shot examples for prompt enhancement
few_shots = get_classifier_few_shots()
enhanced_prompt = f"{few_shots}\n\nClassify this message: {user_message}"
```

### Lambda Environment Variables

```
DSPY_MODEL_BUCKET=pf-syn-dspy-models-dev
DSPY_MODEL_PREFIX=optimized/
```

## How DSPy Optimization Works

1. **Signatures** define the input/output schema:
   ```python
   class IntentClassifier(dspy.Signature):
       message: str = dspy.InputField()
       intent: str = dspy.OutputField()
       action: str = dspy.OutputField()
   ```

2. **Modules** wrap signatures with reasoning:
   ```python
   class ProjectForceClassifier(dspy.Module):
       def __init__(self):
           self.classifier = dspy.ChainOfThought(IntentClassifier)
   ```

3. **BootstrapFewShot** optimizes by:
   - Running the module on training examples
   - Collecting successful traces (reasoning chains)
   - Selecting the best few-shot examples
   - Saving as JSON with demos embedded

4. **At runtime**, the orchestrator:
   - Loads the optimized JSON
   - Extracts the few-shot demos
   - Injects them into prompts as examples

## Metrics

| Module | Metric | Typical Score |
|--------|--------|---------------|
| Classifier | Intent + Action accuracy | 68-75% |
| Extractor | Entity field accuracy | 80-90% |
| Weather | Location + Date match | 85-95% |
| Date Interpreter | Start + End date match | 90-95% |
| Context Resolver | Reference resolution | 75-85% |
| Response Styler | Style appropriateness | 85-90% |
| Slot Ranker | Ranking quality | 80-90% |

## Troubleshooting

### "No module named 'dspy'"
```bash
pip install dspy-ai>=2.4.0
```

### API Key errors
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

### S3 access errors
```bash
export AWS_PROFILE=pf-aws
aws s3 ls s3://pf-syn-dspy-models-dev/optimized/
```

### Models not updating in Lambda
- Lambda caches models in `/tmp`
- Redeploy Lambda or wait for cold start
- Check CloudWatch logs for model loading

## Resources

- [DSPy Documentation](https://dspy-docs.vercel.app/)
- [DSPy GitHub](https://github.com/stanfordnlp/dspy)
- [DSPy Paper](https://arxiv.org/abs/2310.03714)
- [BootstrapFewShot Guide](https://dspy-docs.vercel.app/docs/building-blocks/optimizers)
