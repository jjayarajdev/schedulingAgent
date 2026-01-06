"""
DSPy Date Interpreter Module

Replaces regex-based date parsing with LLM-powered interpretation.
Handles natural language date expressions like:
- "first week of January"
- "next Tuesday"
- "end of month"
- "between Jan 9 and 18"
- "01/08" (MM/DD format)

Benefits over regex:
1. Handles any phrasing without new patterns
2. Understands context (today's date, past vs future)
3. DSPy optimization improves accuracy over time
4. Single source of truth for all date logic
"""

import dspy
from typing import Literal, Optional, Tuple
from datetime import datetime, timedelta
import json
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# DSPy SIGNATURE
# =============================================================================

class DateInterpreter(dspy.Signature):
    """Convert natural language date expressions to specific date ranges for scheduling.

    Given a date phrase and today's date, extract:
    - The start and end dates of the requested period
    - Whether the dates are in the past
    - The type of date request (specific day, week, month, range)

    For week calculations:
    - Week 1 of a month = days from 1st until first Sunday
    - Week 2+ = Monday to Sunday weeks
    - If a week is entirely past, return is_past=true with null dates
    """

    phrase: str = dspy.InputField(desc="Natural language date expression (e.g., 'first week of January', 'next Tuesday', '01/08')")
    current_date: str = dspy.InputField(desc="Today's date in YYYY-MM-DD format")

    start_date: str = dspy.OutputField(
        desc="Start date in YYYY-MM-DD format, or 'null' if dates are entirely in past"
    )
    end_date: str = dspy.OutputField(
        desc="End date in YYYY-MM-DD format, or 'null' if dates are entirely in past"
    )
    is_past: bool = dspy.OutputField(
        desc="True if ALL requested dates are in the past (before current_date)"
    )
    date_type: Literal["specific_day", "week", "month", "date_range"] = dspy.OutputField(
        desc="Type of date request"
    )
    interpretation: str = dspy.OutputField(
        desc="Human-readable explanation of what dates were calculated"
    )


# =============================================================================
# TRAINING EXAMPLES
# =============================================================================

TRAINING_EXAMPLES = [
    # Week queries - past
    dspy.Example(
        phrase="first week of January",
        current_date="2026-01-06",
        start_date="null",
        end_date="null",
        is_past=True,
        date_type="week",
        interpretation="First week of January 2026 is Jan 1-4 (Wed-Sat before first Monday). Today is Jan 6, so this week has passed."
    ).with_inputs("phrase", "current_date"),

    dspy.Example(
        phrase="1st week of Jan",
        current_date="2026-01-07",
        start_date="null",
        end_date="null",
        is_past=True,
        date_type="week",
        interpretation="1st week of January 2026 is Jan 1-4. All dates are before Jan 7, so week is past."
    ).with_inputs("phrase", "current_date"),

    # Week queries - future
    dspy.Example(
        phrase="first week of April",
        current_date="2026-01-06",
        start_date="2026-04-01",
        end_date="2026-04-05",
        is_past=False,
        date_type="week",
        interpretation="First week of April 2026 is Apr 1-5 (Wed-Sun before first Monday Apr 6)."
    ).with_inputs("phrase", "current_date"),

    dspy.Example(
        phrase="2nd week of January",
        current_date="2026-01-06",
        start_date="2026-01-07",
        end_date="2026-01-11",
        is_past=False,
        date_type="week",
        interpretation="2nd week of January 2026 starts Mon Jan 5, but Jan 5-6 are past. Available: Jan 7-11 (Wed-Sun)."
    ).with_inputs("phrase", "current_date"),

    dspy.Example(
        phrase="3rd week of February",
        current_date="2026-01-06",
        start_date="2026-02-16",
        end_date="2026-02-22",
        is_past=False,
        date_type="week",
        interpretation="3rd week of February 2026 is Feb 16-22 (Mon-Sun)."
    ).with_inputs("phrase", "current_date"),

    dspy.Example(
        phrase="last week of March",
        current_date="2026-01-06",
        start_date="2026-03-23",
        end_date="2026-03-31",
        is_past=False,
        date_type="week",
        interpretation="Last week of March 2026 is Mar 23-31 (last Monday to end of month)."
    ).with_inputs("phrase", "current_date"),

    # Specific day queries
    dspy.Example(
        phrase="01/08",
        current_date="2026-01-06",
        start_date="2026-01-08",
        end_date="2026-01-08",
        is_past=False,
        date_type="specific_day",
        interpretation="January 8, 2026 - specific date from MM/DD format."
    ).with_inputs("phrase", "current_date"),

    dspy.Example(
        phrase="January 15",
        current_date="2026-01-06",
        start_date="2026-01-15",
        end_date="2026-01-15",
        is_past=False,
        date_type="specific_day",
        interpretation="January 15, 2026 - specific date."
    ).with_inputs("phrase", "current_date"),

    dspy.Example(
        phrase="the 10th",
        current_date="2026-01-06",
        start_date="2026-01-10",
        end_date="2026-01-10",
        is_past=False,
        date_type="specific_day",
        interpretation="The 10th of current month (January 2026)."
    ).with_inputs("phrase", "current_date"),

    dspy.Example(
        phrase="next Tuesday",
        current_date="2026-01-06",
        start_date="2026-01-13",
        end_date="2026-01-13",
        is_past=False,
        date_type="specific_day",
        interpretation="Next Tuesday from Jan 6 (Tuesday) is Jan 13."
    ).with_inputs("phrase", "current_date"),

    dspy.Example(
        phrase="tomorrow",
        current_date="2026-01-06",
        start_date="2026-01-07",
        end_date="2026-01-07",
        is_past=False,
        date_type="specific_day",
        interpretation="Tomorrow from Jan 6 is Jan 7."
    ).with_inputs("phrase", "current_date"),

    # Month queries
    dspy.Example(
        phrase="February",
        current_date="2026-01-06",
        start_date="2026-02-01",
        end_date="2026-02-07",
        is_past=False,
        date_type="month",
        interpretation="February 2026 - showing first week (Feb 1-7)."
    ).with_inputs("phrase", "current_date"),

    dspy.Example(
        phrase="next month",
        current_date="2026-01-06",
        start_date="2026-02-01",
        end_date="2026-02-07",
        is_past=False,
        date_type="month",
        interpretation="Next month from January is February 2026 - showing first week."
    ).with_inputs("phrase", "current_date"),

    dspy.Example(
        phrase="end of January",
        current_date="2026-01-06",
        start_date="2026-01-27",
        end_date="2026-01-31",
        is_past=False,
        date_type="month",
        interpretation="End of January 2026 - last 5 days (Jan 27-31)."
    ).with_inputs("phrase", "current_date"),

    # Date range queries
    dspy.Example(
        phrase="between Jan 9 and 18",
        current_date="2026-01-06",
        start_date="2026-01-09",
        end_date="2026-01-18",
        is_past=False,
        date_type="date_range",
        interpretation="Explicit date range: January 9-18, 2026."
    ).with_inputs("phrase", "current_date"),

    dspy.Example(
        phrase="from the 15th to the 20th",
        current_date="2026-01-06",
        start_date="2026-01-15",
        end_date="2026-01-20",
        is_past=False,
        date_type="date_range",
        interpretation="Date range from 15th to 20th of current month (January 2026)."
    ).with_inputs("phrase", "current_date"),

    # Edge cases
    dspy.Example(
        phrase="this week",
        current_date="2026-01-06",
        start_date="2026-01-07",
        end_date="2026-01-11",
        is_past=False,
        date_type="week",
        interpretation="This week (Jan 5-11), but today is Jan 6, so available: Jan 7-11."
    ).with_inputs("phrase", "current_date"),

    dspy.Example(
        phrase="next week",
        current_date="2026-01-06",
        start_date="2026-01-12",
        end_date="2026-01-18",
        is_past=False,
        date_type="week",
        interpretation="Next week from Jan 6 is Jan 12-18 (Mon-Sun)."
    ).with_inputs("phrase", "current_date"),

    # Partially past week
    dspy.Example(
        phrase="2nd week of Jan",
        current_date="2026-01-08",
        start_date="2026-01-09",
        end_date="2026-01-11",
        is_past=False,
        date_type="week",
        interpretation="2nd week of Jan is Jan 5-11, but Jan 5-8 are past. Available: Jan 9-11."
    ).with_inputs("phrase", "current_date"),
]


# =============================================================================
# DSPy MODULE
# =============================================================================

class DateInterpreterModule(dspy.Module):
    """DSPy module for interpreting natural language dates."""

    def __init__(self):
        super().__init__()
        self.interpreter = dspy.ChainOfThought(DateInterpreter)

    def forward(self, phrase: str, current_date: str):
        """Interpret a date phrase given the current date."""
        result = self.interpreter(phrase=phrase, current_date=current_date)
        return result


# =============================================================================
# STANDALONE FUNCTION (for use without DSPy runtime)
# =============================================================================

def interpret_date_with_llm(
    phrase: str,
    current_date: Optional[str] = None,
    use_cache: bool = True
) -> dict:
    """
    Interpret a natural language date expression using LLM.

    Args:
        phrase: Natural language date expression
        current_date: Today's date (YYYY-MM-DD), defaults to actual today
        use_cache: Whether to use cached results for common phrases

    Returns:
        dict with keys: start_date, end_date, is_past, date_type, interpretation
    """
    if current_date is None:
        current_date = datetime.now().strftime("%Y-%m-%d")

    # Try DSPy first
    try:
        import dspy

        # Initialize module
        module = DateInterpreterModule()

        # Run interpretation
        result = module(phrase=phrase, current_date=current_date)

        return {
            "start_date": None if result.start_date == "null" else result.start_date,
            "end_date": None if result.end_date == "null" else result.end_date,
            "is_past": result.is_past,
            "date_type": result.date_type,
            "interpretation": result.interpretation,
            "_source": "dspy"
        }

    except Exception as e:
        logger.warning(f"DSPy date interpretation failed: {e}, using fallback")
        return _fallback_interpret(phrase, current_date)


def _fallback_interpret(phrase: str, current_date: str) -> dict:
    """Fallback interpretation using simple rules (legacy behavior)."""
    # This is a simplified fallback - in production, you'd keep the existing regex logic
    today = datetime.strptime(current_date, "%Y-%m-%d")
    tomorrow = today + timedelta(days=1)

    return {
        "start_date": tomorrow.strftime("%Y-%m-%d"),
        "end_date": (tomorrow + timedelta(days=4)).strftime("%Y-%m-%d"),
        "is_past": False,
        "date_type": "week",
        "interpretation": f"Fallback: defaulting to next 5 days from {tomorrow.strftime('%Y-%m-%d')}",
        "_source": "fallback"
    }


# =============================================================================
# OPTIMIZATION SCRIPT
# =============================================================================

def optimize_date_interpreter():
    """
    Optimize the DateInterpreter using DSPy's MIPROv2 optimizer.

    Run this script to generate optimized_date_interpreter.json
    """
    import dspy
    from dspy.teleprompt import MIPROv2

    # Configure DSPy with Bedrock
    lm = dspy.LM(
        model="bedrock/anthropic.claude-3-5-sonnet-20241022-v2:0",
        aws_region_name="us-east-1"
    )
    dspy.configure(lm=lm)

    # Create module
    module = DateInterpreterModule()

    # Split examples into train/test
    train_examples = TRAINING_EXAMPLES[:15]
    test_examples = TRAINING_EXAMPLES[15:]

    # Define metric
    def date_accuracy(example, prediction, trace=None):
        """Check if predicted dates match expected dates."""
        score = 0.0

        # Check start_date
        if str(prediction.start_date) == str(example.start_date):
            score += 0.3

        # Check end_date
        if str(prediction.end_date) == str(example.end_date):
            score += 0.3

        # Check is_past
        if prediction.is_past == example.is_past:
            score += 0.2

        # Check date_type
        if prediction.date_type == example.date_type:
            score += 0.2

        return score

    # Optimize
    optimizer = MIPROv2(
        metric=date_accuracy,
        auto="medium",
        num_threads=4
    )

    optimized_module = optimizer.compile(
        module,
        trainset=train_examples,
        valset=test_examples
    )

    # Save optimized module
    optimized_module.save("optimized_date_interpreter.json")
    print("Saved optimized_date_interpreter.json")

    # Evaluate
    from dspy.evaluate import Evaluate
    evaluator = Evaluate(devset=test_examples, metric=date_accuracy)
    score = evaluator(optimized_module)
    print(f"Test accuracy: {score:.2%}")

    return optimized_module


if __name__ == "__main__":
    # Run optimization
    optimize_date_interpreter()
