"""
Update Lex V2 intents for voice - add missing utterances and CancelAppointment intent
"""
import boto3
import json

# Config
BOT_ID = "MCMSOW2OXJ"
BOT_VERSION = "DRAFT"
LOCALE_ID = "en_US"
REGION = "us-east-1"

client = boto3.client('lexv2-models', region_name=REGION)

# Missing utterances for RescheduleAppointment (work/service terminology)
NEW_RESCHEDULE_UTTERANCES = [
    "reschedule my work",
    "change my work date",
    "move my work",
    "reschedule my service",
    "reschedule my service call",
    "change my service date",
    "move my service call",
    "reschedule the service",
    "change the service appointment",
    "move the service",
    "reschedule my work order",
    "change my work order",
    "move my work order",
    "push it to next month",
    "reschedule to a later date",
    "reschedule for the following week",
    "change to a different week",
]

# SelectionIntent utterances - for ordinal selections (VOICE-SPECIFIC)
# UNIQUE utterances that don't conflict with ProjectStatusInquiry
# Uses action verbs: "I want", "let's do", "go with", "I'll take"
SELECTION_UTTERANCES = [
    # "I want" patterns - unique to selection
    "I want the first one", "I want the second one", "I want the third one", "I want the fourth one",
    "I want the fifth one", "I want the sixth one", "I want the seventh one", "I want the eighth one",
    "I want first", "I want second", "I want third", "I want fourth",
    # "let's do" patterns
    "let's do the first one", "let's do the second one", "let's do the third one", "let's do the fourth one",
    "lets do first", "lets do second", "lets do third", "lets do fourth",
    # "go with" patterns
    "go with the first one", "go with the second one", "go with the third one", "go with the fourth one",
    "go with first", "go with second", "go with third", "go with fourth",
    # "I'll take" patterns
    "I'll take the first one", "I'll take the second one", "I'll take the third one", "I'll take the fourth one",
    "ill take first", "ill take second", "ill take third", "ill take fourth",
    # "that one" with context
    "yes that one", "yeah that one", "that one please", "yes this one",
    # Selection with "please"
    "first please", "second please", "third please", "fourth please",
    "the first one please", "the second one please", "the third one please", "the fourth one please",
    # Explicit selection verbs
    "select the first", "select the second", "select the third", "select the fourth",
    "pick the first", "pick the second", "pick the third", "pick the fourth",
    "choose the first", "choose the second", "choose the third", "choose the fourth",
    # Number with context
    "I pick one", "I pick two", "I pick three", "I pick four",
    "I choose one", "I choose two", "I choose three", "I choose four",
    # Reschedule-specific ordinals
    "reschedule the first one", "reschedule the second one", "reschedule the third one", "reschedule the fourth one",
    "cancel the first one", "cancel the second one", "cancel the third one", "cancel the fourth one",
    # "details of my X job/work" patterns - VOICE-SPECIFIC (uses "my" + "job/work" to avoid ProjectStatusInquiry conflicts)
    "details of my first job", "details of my second job", "details of my third job", "details of my fourth job",
    "details of my first work", "details of my second work", "details of my third work", "details of my fourth work",
    "details on my first job", "details on my second job", "details on my third job", "details on my fourth job",
    "details on my first work", "details on my second work", "details on my third work", "details on my fourth work",
    # "tell me about my X job/work" patterns (avoid "the X one" - conflicts with ProjectStatusInquiry)
    "tell me about my first job", "tell me about my second job", "tell me about my third job", "tell me about my fourth job",
    "tell me about my first work", "tell me about my second work", "tell me about my third work", "tell me about my fourth work",
    # "more about my X job/work" patterns (avoid "the X one" - conflicts with ProjectStatusInquiry)
    "more about my first job", "more about my second job", "more about my third job", "more about my fourth job",
    "more about my first work", "more about my second work", "more about my third work", "more about my fourth work",
    # "what about my X job/work" patterns (avoid "the X project" - conflicts with ProjectStatusInquiry)
    "what about my first job", "what about my second job", "what about my third job", "what about my fourth job",
    "what about my first work", "what about my second work", "what about my third work", "what about my fourth work",
    # "info on my X" patterns
    "info on my first job", "info on my second job", "info on my third job", "info on my fourth job",
    "information on my first job", "information on my second job", "information on my third job", "information on my fourth job",
]

# CancelAppointment utterances
CANCEL_UTTERANCES = [
    "cancel my appointment",
    "cancel the appointment",
    "cancel it",
    "I need to cancel",
    "I want to cancel",
    "cancel please",
    "cancel my installation",
    "cancel my job",
    "cancel my work",
    "cancel my service",
    "cancel my service call",
    "cancel my project",
    "cancel this",
    "cancel this appointment",
    "cancel this one",
    "cancel the installation",
    "cancel the job",
    "cancel first job",
    "cancel second job",
    "cancel my first job",
    "cancel my second job",
    "cancel the first project",
    "cancel the second project",
    "do not come",
    "dont come",
    "I dont need it anymore",
    "I dont want it anymore",
    "never mind cancel it",
    "forget it just cancel",
    "just cancel it",
    "cancel my booking",
    "remove my appointment",
    "delete my appointment",
    "I changed my mind cancel it",
    "cancel the whole thing",
    "cancel everything",
    "cancel my decking installation",
    "cancel my flooring project",
    "cancel my roofing appointment",
]


def update_reschedule_intent():
    """Add missing utterances to RescheduleAppointment intent"""
    print("\n=== Updating RescheduleAppointment Intent ===")

    # Get current intent
    intent = client.describe_intent(
        botId=BOT_ID,
        botVersion=BOT_VERSION,
        localeId=LOCALE_ID,
        intentId="PBBQ0R75L3"
    )

    # Get current utterances
    current_utterances = [u['utterance'].lower() for u in intent.get('sampleUtterances', [])]
    print(f"Current utterances: {len(current_utterances)}")

    # Add new ones that don't exist
    new_sample_utterances = list(intent.get('sampleUtterances', []))
    added = 0
    for utt in NEW_RESCHEDULE_UTTERANCES:
        if utt.lower() not in current_utterances:
            new_sample_utterances.append({'utterance': utt})
            added += 1
            print(f"  + Adding: {utt}")

    if added == 0:
        print("  No new utterances to add")
        return

    print(f"\nAdding {added} new utterances...")

    # Update intent
    client.update_intent(
        botId=BOT_ID,
        botVersion=BOT_VERSION,
        localeId=LOCALE_ID,
        intentId=intent['intentId'],
        intentName=intent['intentName'],
        description=intent.get('description', ''),
        sampleUtterances=new_sample_utterances,
        dialogCodeHook=intent.get('dialogCodeHook', {'enabled': False}),
        fulfillmentCodeHook=intent.get('fulfillmentCodeHook', {'enabled': True})
    )
    print(f"[OK] Updated RescheduleAppointment with {len(new_sample_utterances)} total utterances")


def create_cancel_intent():
    """Create CancelAppointment intent if it doesn't exist"""
    print("\n=== Creating CancelAppointment Intent ===")

    # Check if intent already exists (with manual pagination)
    next_token = None
    while True:
        kwargs = {
            'botId': BOT_ID,
            'botVersion': BOT_VERSION,
            'localeId': LOCALE_ID,
            'maxResults': 100
        }
        if next_token:
            kwargs['nextToken'] = next_token

        response = client.list_intents(**kwargs)
        for intent in response['intentSummaries']:
            if intent['intentName'] == 'CancelAppointment':
                print("  CancelAppointment intent already exists")
                # Update it with utterances
                update_cancel_intent(intent['intentId'])
                return

        next_token = response.get('nextToken')
        if not next_token:
            break

    print("  Creating new CancelAppointment intent...")

    # Create new intent
    response = client.create_intent(
        botId=BOT_ID,
        botVersion=BOT_VERSION,
        localeId=LOCALE_ID,
        intentName='CancelAppointment',
        description='Cancel an existing installation appointment',
        sampleUtterances=[{'utterance': u} for u in CANCEL_UTTERANCES],
        fulfillmentCodeHook={
            'enabled': True,
            'postFulfillmentStatusSpecification': {
                'successResponse': {
                    'messageGroups': [{'message': {'plainTextMessage': {'value': ' '}}}],
                    'allowInterrupt': True
                },
                'failureResponse': {
                    'messageGroups': [{'message': {'plainTextMessage': {'value': 'Sorry, there was an issue.'}}}],
                    'allowInterrupt': True
                }
            }
        },
        dialogCodeHook={'enabled': True}
    )

    print(f"[OK] Created CancelAppointment intent (ID: {response['intentId']})")
    print(f"     with {len(CANCEL_UTTERANCES)} utterances")


def update_cancel_intent(intent_id):
    """Update existing CancelAppointment intent with utterances"""
    print(f"  Updating CancelAppointment intent {intent_id}...")

    # Get current intent
    intent = client.describe_intent(
        botId=BOT_ID,
        botVersion=BOT_VERSION,
        localeId=LOCALE_ID,
        intentId=intent_id
    )

    # Get current utterances
    current_utterances = [u['utterance'].lower() for u in intent.get('sampleUtterances', [])]

    # Add new ones
    new_sample_utterances = list(intent.get('sampleUtterances', []))
    added = 0
    for utt in CANCEL_UTTERANCES:
        if utt.lower() not in current_utterances:
            new_sample_utterances.append({'utterance': utt})
            added += 1

    if added > 0:
        client.update_intent(
            botId=BOT_ID,
            botVersion=BOT_VERSION,
            localeId=LOCALE_ID,
            intentId=intent_id,
            intentName=intent['intentName'],
            description=intent.get('description', 'Cancel an existing installation appointment'),
            sampleUtterances=new_sample_utterances,
            dialogCodeHook=intent.get('dialogCodeHook', {'enabled': True}),
            fulfillmentCodeHook=intent.get('fulfillmentCodeHook', {'enabled': True})
        )
        print(f"  [OK] Added {added} utterances to CancelAppointment")
    else:
        print("  No new utterances to add")


def create_selection_intent():
    """Create SelectionIntent for ordinal selections (VOICE-SPECIFIC)"""
    print("\n=== Creating SelectionIntent (VOICE-SPECIFIC) ===")

    # Check if intent already exists (with manual pagination)
    next_token = None
    while True:
        kwargs = {
            'botId': BOT_ID,
            'botVersion': BOT_VERSION,
            'localeId': LOCALE_ID,
            'maxResults': 100
        }
        if next_token:
            kwargs['nextToken'] = next_token

        response = client.list_intents(**kwargs)
        for intent in response['intentSummaries']:
            if intent['intentName'] == 'SelectionIntent':
                print("  SelectionIntent already exists")
                # Update it with utterances
                update_selection_intent(intent['intentId'])
                return

        next_token = response.get('nextToken')
        if not next_token:
            break

    print("  Creating new SelectionIntent...")

    # Create new intent
    response = client.create_intent(
        botId=BOT_ID,
        botVersion=BOT_VERSION,
        localeId=LOCALE_ID,
        intentName='SelectionIntent',
        description='Handle ordinal selections like first, second, the fourth one (VOICE-SPECIFIC)',
        sampleUtterances=[{'utterance': u} for u in SELECTION_UTTERANCES],
        fulfillmentCodeHook={
            'enabled': True,
            'postFulfillmentStatusSpecification': {
                'successResponse': {
                    'messageGroups': [{'message': {'plainTextMessage': {'value': ' '}}}],
                    'allowInterrupt': True
                },
                'failureResponse': {
                    'messageGroups': [{'message': {'plainTextMessage': {'value': 'Sorry, there was an issue.'}}}],
                    'allowInterrupt': True
                }
            }
        },
        dialogCodeHook={'enabled': True}
    )

    print(f"[OK] Created SelectionIntent (ID: {response['intentId']})")
    print(f"     with {len(SELECTION_UTTERANCES)} utterances")


def update_selection_intent(intent_id):
    """Update existing SelectionIntent with utterances"""
    print(f"  Updating SelectionIntent {intent_id}...")

    # Get current intent
    intent = client.describe_intent(
        botId=BOT_ID,
        botVersion=BOT_VERSION,
        localeId=LOCALE_ID,
        intentId=intent_id
    )

    # Get current utterances
    current_utterances = [u['utterance'].lower() for u in intent.get('sampleUtterances', [])]

    # Add new ones
    new_sample_utterances = list(intent.get('sampleUtterances', []))
    added = 0
    for utt in SELECTION_UTTERANCES:
        if utt.lower() not in current_utterances:
            new_sample_utterances.append({'utterance': utt})
            added += 1

    if added > 0:
        client.update_intent(
            botId=BOT_ID,
            botVersion=BOT_VERSION,
            localeId=LOCALE_ID,
            intentId=intent_id,
            intentName=intent['intentName'],
            description=intent.get('description', 'Handle ordinal selections (VOICE-SPECIFIC)'),
            sampleUtterances=new_sample_utterances,
            dialogCodeHook=intent.get('dialogCodeHook', {'enabled': True}),
            fulfillmentCodeHook=intent.get('fulfillmentCodeHook', {'enabled': True})
        )
        print(f"  [OK] Added {added} utterances to SelectionIntent")
    else:
        print("  No new utterances to add")


def build_and_deploy_bot():
    """Build the bot locale after updates"""
    print("\n=== Building Bot Locale ===")

    response = client.build_bot_locale(
        botId=BOT_ID,
        botVersion=BOT_VERSION,
        localeId=LOCALE_ID
    )

    print(f"[OK] Bot build started (status: {response['botLocaleStatus']})")
    print("     Wait ~1-2 minutes for build to complete")


if __name__ == '__main__':
    print("=" * 60)
    print("Lex V2 Voice Intent Updates (VOICE-SPECIFIC)")
    print("=" * 60)

    update_reschedule_intent()
    create_cancel_intent()
    create_selection_intent()  # NEW: Handle ordinal selections like "the fourth one"
    build_and_deploy_bot()

    print("\n" + "=" * 60)
    print("DONE! Bot is building. Check status in AWS console.")
    print("=" * 60)
