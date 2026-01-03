"""
DSPy Modules for ProjectForce Orchestrator

Modules are composable units that use Signatures to define LLM behavior.
They can be chained together and optimized as a pipeline.
"""
import dspy
import json
from typing import Dict, Any, Optional

from signatures import (
    IntentClassifier,
    EntityExtractor,
    WeatherContextResolver,
    ActionGuard,
    VoiceResponseFormatter,
    ChatResponseFormatter,
    DateInterpreter,
    ContextResolver,
    ResponseStyler,
    SlotRanker
)


class ProjectForceClassifier(dspy.Module):
    """
    Intent classification with chain-of-thought reasoning.

    Uses CoT to improve classification accuracy by requiring
    the model to explain its reasoning before outputting.
    """

    def __init__(self):
        super().__init__()
        self.classifier = dspy.ChainOfThought(IntentClassifier)

    def forward(self, message: str, conversation_summary: str = "") -> dspy.Prediction:
        return self.classifier(
            message=message,
            conversation_summary=conversation_summary
        )


class ProjectForceEntityExtractor(dspy.Module):
    """
    Extract entities needed for API calls.

    Uses structured prediction to ensure all required
    parameters are extracted for each action type.
    """

    def __init__(self):
        super().__init__()
        self.extractor = dspy.ChainOfThought(EntityExtractor)

    def forward(
        self,
        message: str,
        action: str,
        available_projects: str = "[]",
        workflow_context: str = "{}"
    ) -> dspy.Prediction:
        return self.extractor(
            message=message,
            action=action,
            available_projects=available_projects,
            workflow_context=workflow_context
        )


class ProjectForceWeatherResolver(dspy.Module):
    """
    Resolve weather query context.

    When user asks "what's the weather" without specifics,
    use workflow context to determine location and date.
    """

    def __init__(self):
        super().__init__()
        self.resolver = dspy.ChainOfThought(WeatherContextResolver)

    def forward(
        self,
        message: str,
        workflow_context: str,
        conversation_summary: str = ""
    ) -> dspy.Prediction:
        return self.resolver(
            message=message,
            workflow_context=workflow_context,
            conversation_summary=conversation_summary
        )


class ProjectForceGuard(dspy.Module):
    """
    Guard against classification errors.

    Validates actions and corrects common mistakes like
    auto-escalating to scheduling without explicit request.
    """

    def __init__(self):
        super().__init__()
        self.guard = dspy.Predict(ActionGuard)

    def forward(
        self,
        message: str,
        classified_action: str,
        workflow_stage: str = "none",
        previous_action: str = ""
    ) -> dspy.Prediction:
        return self.guard(
            message=message,
            classified_action=classified_action,
            workflow_stage=workflow_stage,
            previous_action=previous_action
        )


class ProjectForceFormatter(dspy.Module):
    """
    Format responses for voice or chat channels.
    """

    def __init__(self):
        super().__init__()
        self.voice_formatter = dspy.Predict(VoiceResponseFormatter)
        self.chat_formatter = dspy.Predict(ChatResponseFormatter)

    def forward(
        self,
        action: str,
        api_response: str,
        user_message: str,
        channel: str = "chat"
    ) -> dspy.Prediction:
        if channel == "voice":
            return self.voice_formatter(
                action=action,
                api_response=api_response,
                user_message=user_message
            )
        else:
            return self.chat_formatter(
                action=action,
                api_response=api_response,
                user_message=user_message
            )


# =============================================================================
# NEW MODULES - DATE, CONTEXT, STYLE, SLOT RANKING
# =============================================================================

class ProjectForceDateInterpreter(dspy.Module):
    """
    Convert natural language date expressions to specific date ranges.

    Handles 'next week', 'end of January', 'day after tomorrow', etc.
    """

    def __init__(self):
        super().__init__()
        self.interpreter = dspy.ChainOfThought(DateInterpreter)

    def forward(self, phrase: str, current_date: str) -> dspy.Prediction:
        return self.interpreter(
            phrase=phrase,
            current_date=current_date
        )


class ProjectForceContextResolver(dspy.Module):
    """
    Resolve pronouns and references from conversation context.

    Handles 'it', 'that one', 'the first one', 'my kitchen project', etc.
    """

    def __init__(self):
        super().__init__()
        self.resolver = dspy.ChainOfThought(ContextResolver)

    def forward(
        self,
        message: str,
        conversation_history: str
    ) -> dspy.Prediction:
        return self.resolver(
            message=message,
            conversation_history=conversation_history
        )


class ProjectForceResponseStyler(dspy.Module):
    """
    Adapt response style based on channel (voice/sms/chat).
    """

    def __init__(self):
        super().__init__()
        self.styler = dspy.Predict(ResponseStyler)

    def forward(
        self,
        raw_response: str,
        channel: str,
        context: str = ""
    ) -> dspy.Prediction:
        return self.styler(
            raw_response=raw_response,
            channel=channel,
            context=context
        )


class ProjectForceSlotRanker(dspy.Module):
    """
    Rank time slots based on user preferences, weather, and project type.
    """

    def __init__(self):
        super().__init__()
        self.ranker = dspy.ChainOfThought(SlotRanker)

    def forward(
        self,
        available_slots: str,
        user_preference: str = "",
        weather_info: str = "",
        project_type: str = ""
    ) -> dspy.Prediction:
        return self.ranker(
            available_slots=available_slots,
            user_preference=user_preference,
            weather_info=weather_info,
            project_type=project_type
        )


# =============================================================================
# FULL ORCHESTRATOR PIPELINE
# =============================================================================

class ProjectForceOrchestrator(dspy.Module):
    """
    Complete orchestration pipeline combining all modules.

    Pipeline:
    1. Classify intent and action
    2. Guard against misclassification
    3. Extract entities
    4. (Optional) Resolve weather context
    5. Format response
    """

    def __init__(self):
        super().__init__()
        self.classifier = ProjectForceClassifier()
        self.guard = ProjectForceGuard()
        self.extractor = ProjectForceEntityExtractor()
        self.weather_resolver = ProjectForceWeatherResolver()
        self.formatter = ProjectForceFormatter()

    def forward(
        self,
        message: str,
        conversation_summary: str = "",
        available_projects: str = "[]",
        workflow_context: str = "{}",
        workflow_stage: str = "none",
        previous_action: str = "",
        channel: str = "chat"
    ) -> Dict[str, Any]:
        """
        Process user message through the full pipeline.

        Returns dict with all intermediate and final results.
        """
        results = {}

        # Step 1: Classify
        classification = self.classifier(
            message=message,
            conversation_summary=conversation_summary
        )
        results['classification'] = {
            'intent': classification.intent,
            'action': classification.action,
            'confidence': classification.confidence,
            'reasoning': classification.reasoning
        }

        # Step 2: Guard
        guarded = self.guard(
            message=message,
            classified_action=classification.action,
            workflow_stage=workflow_stage,
            previous_action=previous_action
        )
        results['guard'] = {
            'final_action': guarded.final_action,
            'was_corrected': guarded.was_corrected,
            'guard_reason': guarded.guard_reason
        }

        final_action = guarded.final_action

        # Step 3: Extract entities
        entities = self.extractor(
            message=message,
            action=final_action,
            available_projects=available_projects,
            workflow_context=workflow_context
        )
        results['entities'] = {
            'project_id': entities.project_id,
            'category': entities.category,
            'date': entities.date,
            'time': entities.time,
            'location': entities.location,
            'status_filter': entities.status_filter
        }

        # Step 4: Weather context resolution (if weather action)
        if final_action == 'get_weather' and not entities.location:
            weather_ctx = self.weather_resolver(
                message=message,
                workflow_context=workflow_context,
                conversation_summary=conversation_summary
            )
            results['weather_context'] = {
                'location': weather_ctx.location,
                'target_date': weather_ctx.target_date,
                'reasoning': weather_ctx.reasoning
            }
            # Update entities with resolved values
            results['entities']['location'] = weather_ctx.location
            results['entities']['date'] = weather_ctx.target_date

        results['final_action'] = final_action
        results['channel'] = channel

        return results


# =============================================================================
# ASSERTIONS FOR QUALITY CONTROL
# =============================================================================

class ProjectForceOrchestratorWithAssertions(ProjectForceOrchestrator):
    """
    Orchestrator with DSPy assertions for quality control.

    Assertions are soft constraints that DSPy uses during
    optimization to learn better prompts.
    """

    def forward(self, message: str, **kwargs) -> Dict[str, Any]:
        results = super().forward(message, **kwargs)

        # Assertion: Don't auto-schedule without explicit keywords
        schedule_keywords = ['schedule', 'book', 'appointment', 'set up']
        has_schedule_keyword = any(kw in message.lower() for kw in schedule_keywords)

        if results['final_action'] == 'get_available_dates':
            dspy.Assert(
                has_schedule_keyword,
                f"Action 'get_available_dates' requires explicit schedule keyword in message: '{message}'"
            )

        # Assertion: Weather needs location
        if results['final_action'] == 'get_weather':
            location = results['entities'].get('location') or \
                       results.get('weather_context', {}).get('location')
            dspy.Assert(
                bool(location),
                f"Weather action requires location. Message: '{message}'"
            )

        # Assertion: Confirmation needs project and time
        if results['final_action'] == 'confirm_appointment':
            dspy.Assert(
                bool(results['entities'].get('project_id')),
                "Confirmation requires project_id"
            )
            dspy.Assert(
                bool(results['entities'].get('time')),
                "Confirmation requires time slot"
            )

        return results
