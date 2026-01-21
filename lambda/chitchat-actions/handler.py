"""
Chitchat Actions Lambda Handler
Conversational AI for greetings, small talk, and general queries
Uses Claude Haiku for natural, engaging responses while staying in domain
"""

import json
import logging
import boto3
from typing import Dict, Any
from botocore.config import Config as BotoConfig

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Bedrock client (lazy init)
_bedrock_client = None

def get_bedrock_client():
    """Get or create Bedrock runtime client"""
    global _bedrock_client
    if _bedrock_client is None:
        boto_config = BotoConfig(
            region_name='us-east-1',
            retries={"max_attempts": 3, "mode": "adaptive"}
        )
        _bedrock_client = boto3.client("bedrock-runtime", config=boto_config)
    return _bedrock_client


# ═══════════════════════════════════════════════════════════════════════════════
# SYSTEM PROMPT - Defines personality and boundaries
# ═══════════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """You are a fun, friendly scheduling assistant for home improvement projects. Think of yourself as that enthusiastic friend who's really into home improvement and genuinely excited to help people get their projects done!

## Your Personality
- Upbeat and enthusiastic - you LOVE helping people with their home projects!
- Warm and personable - use casual, friendly language
- A bit playful - light humor is welcome, but don't force it
- Encouraging - make customers feel good about their home improvement journey

## What You Help With
You're the go-to person for home improvement project scheduling:
- Kitchen upgrades (dishwashers, cooktops, sinks)
- Flooring (hardwood, tile, carpet)
- Decking & outdoor spaces
- Windows & doors
- And more!

You help customers:
- Check on their projects ("show my projects")
- Find available appointment slots
- Book installation appointments
- Reschedule when life happens
- Cancel if needed
- Check weather for outdoor projects

## Response Style
- Be conversational, like texting a helpful friend
- Keep responses 2-3 sentences max
- Use expressions like "Awesome!", "Great!", "Let's do this!"
- NEVER repeat the same response twice in a conversation
- Each response should feel fresh and unique

## Boundaries
- You're all about scheduling and projects - that's your jam!
- If someone asks off-topic stuff, acknowledge with humor then pivot back
- Don't make up project details you don't have"""


# ═══════════════════════════════════════════════════════════════════════════════
# INTENT DETECTION - More granular than before
# ═══════════════════════════════════════════════════════════════════════════════

def detect_intent(message: str) -> str:
    """Detect the type of chitchat from message content"""
    msg_lower = message.lower().strip()

    # Greeting patterns
    greet_words = ['hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening', 'howdy', 'hiya', 'yo']
    if any(msg_lower.startswith(w) or msg_lower == w for w in greet_words):
        return 'greet'

    # Well-being queries (how are you, how's it going)
    well_being_patterns = ['how are you', "how's it going", 'how you doing', "what's up", 'whats up', 'sup']
    if any(p in msg_lower for p in well_being_patterns):
        return 'well_being'

    # Help/capabilities queries
    help_patterns = ['what can you do', 'how does this work', 'what do you do', 'how can you help', 'what are you', 'who are you']
    if any(p in msg_lower for p in help_patterns):
        return 'help'

    # Follow-up queries (anything else, what else, tell me more)
    followup_patterns = ['anything else', 'what else', 'tell me more', 'more options', 'other things', 'something else']
    if any(p in msg_lower for p in followup_patterns):
        return 'followup'

    # Thanks patterns
    thanks_patterns = ['thank', 'thanks', 'appreciate', 'thx', 'ty', 'cheers']
    if any(p in msg_lower for p in thanks_patterns):
        return 'thanks'

    # Goodbye patterns
    bye_patterns = ['bye', 'goodbye', 'see you', 'later', 'gotta go', 'talk to you later', 'ttyl', 'cya']
    if any(p in msg_lower for p in bye_patterns):
        return 'bye'

    # Affirmative responses
    affirmative_patterns = ['yes', 'yeah', 'yep', 'sure', 'ok', 'okay', 'sounds good', 'let\'s do it', 'go ahead']
    if msg_lower in affirmative_patterns or any(msg_lower.startswith(p) for p in affirmative_patterns):
        return 'affirmative'

    # Negative responses
    negative_patterns = ['no', 'nope', 'nah', 'not now', 'maybe later', 'not interested']
    if msg_lower in negative_patterns or any(msg_lower.startswith(p) for p in negative_patterns):
        return 'negative'

    # Questions (ends with ?)
    if msg_lower.endswith('?'):
        return 'question'

    # Default to general
    return 'general'


# ═══════════════════════════════════════════════════════════════════════════════
# CONTEXT HINTS - Specific instructions for each intent type
# ═══════════════════════════════════════════════════════════════════════════════

CONTEXT_HINTS = {
    'greet': """The user is greeting you! Respond with a warm, enthusiastic greeting.
- Say hi back in a fun way
- Show you're excited to help
- Ask what they'd like to do with their projects
Example: "Hey there! Great to see you! Ready to tackle some home improvement stuff today?"
DO NOT just repeat "What can we tackle together" - be creative!""",

    'well_being': """The user is asking how you're doing! This is small talk - engage with it!
- Share that you're doing great/fantastic
- Show some personality - maybe mention you've been helping people with cool projects
- Then offer to help them
Example: "Doing awesome, thanks for asking! Just helped someone schedule a deck install - so satisfying! How can I help you today?"
IMPORTANT: Actually answer how you're doing, don't just pivot to projects immediately.""",

    'help': """The user wants to know what you can do. Give them a helpful overview:
- List your main capabilities in a conversational way
- Mention: viewing projects, scheduling, rescheduling, canceling, weather checks
- Make it sound helpful, not like a feature list
Example: "I can help you see all your projects, find open install dates, book appointments, reschedule if plans change, or even check the weather for outdoor work!"
Be specific about capabilities but keep it friendly.""",

    'followup': """The user said "anything else" or similar - they want MORE info beyond what you already mentioned.
- DON'T repeat what you already said
- Mention additional features or tips they might not know
- Could mention: checking specific project details, weather for outdoor projects, rescheduling flexibility
Example: "Oh yeah! I can also tell you about specific project details like who your installer is, or check if the weather looks good for outdoor work. And if you ever need to reschedule, I'm super flexible with that!"
IMPORTANT: This is a follow-up - give NEW information, not the same thing again.""",

    'thanks': """The user is thanking you! Be genuinely appreciative.
- Express that you're happy to help
- Maybe add a light, friendly comment
- Remind them you're here whenever they need you
Example: "Aw, you're the best! Happy I could help. Holler anytime you need project help - I'm always here!"
Make it feel warm and genuine.""",

    'bye': """The user is leaving. Send them off with good vibes!
- Say goodbye warmly
- Wish them well with their projects
- Keep the door open for future chats
Example: "Take care! Good luck with those home projects - can't wait to hear how they turn out! Come back anytime!"
Be warm and encouraging.""",

    'affirmative': """The user said yes/sure/ok - they're agreeing to something.
- Acknowledge their confirmation enthusiastically
- Ask what they'd like to do or guide them to next step
Example: "Awesome! So what would you like to tackle first - want to see your projects or schedule something?"
Keep the momentum going.""",

    'negative': """The user said no or not now - respect that!
- Acknowledge without being pushy
- Leave the door open
- Be understanding
Example: "No worries at all! Whenever you're ready, I'll be here. Just say hi when you want to check on those projects!"
Don't be pushy.""",

    'question': """The user asked a question. Try to be helpful!
- If it's about projects/scheduling, offer to help with that
- If it's off-topic, acknowledge with humor and redirect
- Be helpful and engaging
Example (off-topic): "Ha! That's a great question, but I'm more of a project scheduling expert than a general knowledge guru. Speaking of which, got any home improvement projects I can help with?"
Stay in your lane but be friendly about it.""",

    'general': """Respond naturally to whatever the user said.
- Be friendly and conversational
- If you're not sure what they need, ask a clarifying question
- Offer concrete options: view projects, schedule appointment, get office number
- NEVER say generic phrases like "I'm all about home improvement"
Example: "I'm not quite sure what you need. Would you like to see your projects, schedule an appointment, or get the office number?"
Be helpful and guide them with specific options."""
}


def call_llm(user_message: str, action_type: str) -> str:
    """Call Claude Haiku for natural response generation"""

    context = CONTEXT_HINTS.get(action_type, CONTEXT_HINTS['general'])

    prompt = f"""IMPORTANT: Generate a UNIQUE response. Do not use generic phrases.

Context: {context}

User message: "{user_message}"

Generate a natural, friendly response (2-3 sentences). Be specific and engaging - avoid generic responses!"""

    try:
        bedrock = get_bedrock_client()
        response = bedrock.invoke_model(
            modelId="anthropic.claude-3-haiku-20240307-v1:0",
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 150,
                "temperature": 0.8,  # Slightly higher for more variety
                "system": SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": prompt}]
            })
        )

        response_body = json.loads(response["body"].read())
        return response_body["content"][0]["text"].strip()

    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        # Fallback responses - varied and specific to each intent
        fallbacks = {
            'greet': "Hey there! So good to see you! What home improvement adventure can we tackle today?",
            'well_being': "Doing fantastic, thanks for asking! Been helping folks get their projects scheduled all day. What can I do for you?",
            'help': "I'm your home improvement scheduling buddy! I can show you your projects, help you book install dates, reschedule appointments, or even check the weather for outdoor work. What sounds good?",
            'followup': "Oh there's more! I can also pull up details on specific projects, check installer info, or see if weather looks good for outdoor installs. What interests you?",
            'thanks': "You're so welcome! It's what I'm here for. Come back anytime you need help with those projects!",
            'bye': "See ya! Best of luck with all your home improvement plans. I'll be here whenever you need me!",
            'affirmative': "Perfect! So what would you like to do - check on some projects or get something scheduled?",
            'negative': "Totally get it! I'll be here whenever you're ready. Just say the word!",
            'question': "That's an interesting one! I'm best at helping with scheduling though. Would you like to check your projects or schedule an appointment?",
            'general': "How can I help you today? I can show your projects, check available dates, or help schedule an appointment."
        }
        return fallbacks.get(action_type, fallbacks['general'])


def extract_parameters(event: Dict) -> Dict[str, Any]:
    """Extract parameters from Bedrock Agent event"""
    try:
        if 'parameters' in event and event['parameters']:
            params = {p['name']: p['value'] for p in event['parameters']}
        elif 'requestBody' in event:
            content = event['requestBody'].get('content', {})
            app_json = content.get('application/json', {})
            if isinstance(app_json, dict) and 'properties' in app_json:
                params = {p['name']: p['value'] for p in app_json['properties']}
            elif isinstance(app_json, str):
                params = json.loads(app_json)
            else:
                params = app_json
        else:
            body = event.get('body', '{}')
            params = json.loads(body) if isinstance(body, str) else body

        # Resolve session attribute references
        session_attrs = event.get('sessionAttributes', {})
        for key, value in params.items():
            if isinstance(value, str) and value.startswith('$'):
                attr_name = value[1:]
                if attr_name in session_attrs:
                    params[key] = session_attrs[attr_name]

        return params
    except Exception as e:
        logger.error(f"Error extracting parameters: {e}")
        return {}


def create_response(body: Dict[str, Any]) -> Dict[str, Any]:
    """Create Lambda response in Bedrock Agent format"""
    return {
        'messageVersion': '1.0',
        'response': {
            'actionGroup': 'chitchat-actions',
            'function': body.get('action', 'general'),
            'functionResponse': {
                'responseBody': {
                    'TEXT': {
                        'body': json.dumps(body)
                    }
                }
            }
        }
    }


def lambda_handler(event, context):
    """Main Lambda handler"""
    try:
        logger.info(f"Received event: {json.dumps(event)}")

        # Extract function name and parameters
        function = event.get('function', event.get('apiPath', 'general'))
        params = extract_parameters(event)
        user_message = params.get('message', '')

        # Also try to get message from other locations in the event
        if not user_message:
            # Try inputText (Bedrock Agent format)
            user_message = event.get('inputText', '')
        if not user_message:
            # Try messageContent
            user_message = event.get('messageContent', '')
        if not user_message:
            # Try agent.inputText
            agent = event.get('agent', {})
            user_message = agent.get('inputText', '')

        logger.info(f"Function: {function}, Message: {user_message}")

        # ALWAYS detect intent from message if available - don't trust upstream classification
        if user_message:
            action_type = detect_intent(user_message)
        elif function in ['greet', 'greeting', 'hello']:
            action_type = 'greet'
        elif function in ['help', 'assistance']:
            action_type = 'help'
        else:
            action_type = 'general'

        logger.info(f"Detected intent: {action_type} (from message: '{user_message[:50]}...' if len(user_message) > 50 else user_message)")

        # Generate natural response using LLM
        response_text = call_llm(user_message or "hello", action_type)

        result = {
            "message": response_text,
            "action": action_type
        }

        logger.info(f"Response: {result}")
        return create_response(result)

    except Exception as e:
        logger.error(f"Error in lambda_handler: {e}", exc_info=True)
        error_response = {
            "message": "Hey! Something went a bit sideways there. What can I help you with?",
            "action": "error_recovery"
        }
        return create_response(error_response)
