"""
Fix Lex V2 intent fulfillment settings for VOICE (AWS Best Practices)

Based on AWS Documentation:
- https://docs.aws.amazon.com/lexv2/latest/dg/streaming-progress.html
- https://docs.aws.amazon.com/lexv2/latest/APIReference/API_FulfillmentUpdatesSpecification.html

Parameter Ranges:
- delayInSeconds: 1-900 (when to start playing wait message)
- frequencyInSeconds: 1-900 (how often to play update message)
- timeoutInSeconds: 1-900 (Lambda timeout)
- messageGroups: 1-5 messages each
- allowInterrupt: Boolean (can user interrupt the message)

Best Practices for Voice:
- delayInSeconds=1: Play engaging message quickly (user expects feedback)
- frequencyInSeconds=5: Update every 5 sec (not too annoying)
- timeoutInSeconds=90: Allow 90 sec for complex Claude queries
- allowInterrupt=False for wait messages: Don't interrupt "please wait"
- allowInterrupt=True for final response: Allow user to interrupt long responses
- postFulfillmentStatusSpecification=ElicitIntent: Continue conversation
"""
import boto3
import json

# Config
BOT_ID = "MCMSOW2OXJ"
BOT_VERSION = "DRAFT"
LOCALE_ID = "en_US"
REGION = "us-east-1"

client = boto3.client('lexv2-models', region_name=REGION)

# Intents that need fulfillment updates (complex intents that call Lambda)
COMPLEX_INTENTS = [
    "ProjectInquiry",
    "ProjectStatusInquiry",
    "AppointmentInquiry",
    "CheckAvailability",
    "WeatherInquiry",
    "RescheduleAppointment",
    "CancelAppointment",
    "ScheduleAppointment",
    "UrgentRequest",
    "FallbackIntent",
    "SelectionIntent",
]

# ============================================================================
# AWS BEST PRACTICE: Fulfillment Updates Specification
# ============================================================================
FULFILLMENT_UPDATES_SPEC = {
    'active': True,

    # START RESPONSE: Played after delayInSeconds while Lambda runs
    'startResponse': {
        'delayInSeconds': 1,  # AWS: 1-900. Best: 1 sec (quick feedback)
        'messageGroups': [    # AWS: 1-5 message groups
            {
                'message': {
                    'plainTextMessage': {
                        'value': 'Let me look that up for you.'
                    }
                }
            },
            {
                'message': {
                    'plainTextMessage': {
                        'value': 'One moment please.'
                    }
                }
            },
            {
                'message': {
                    'plainTextMessage': {
                        'value': 'Just a second while I check.'
                    }
                }
            },
            {
                'message': {
                    'plainTextMessage': {
                        'value': 'Let me find that information for you.'
                    }
                }
            },
            {
                'message': {
                    'plainTextMessage': {
                        'value': 'Checking that now.'
                    }
                }
            }
        ],
        'allowInterrupt': False  # Don't let user interrupt "please wait"
    },

    # UPDATE RESPONSE: Played every frequencyInSeconds while Lambda still runs
    'updateResponse': {
        'frequencyInSeconds': 5,  # AWS: 1-900. Best: 5 sec (not annoying)
        'messageGroups': [        # AWS: 1-5 message groups
            {
                'message': {
                    'plainTextMessage': {
                        'value': 'Still working on that.'
                    }
                }
            },
            {
                'message': {
                    'plainTextMessage': {
                        'value': 'Almost there.'
                    }
                }
            },
            {
                'message': {
                    'plainTextMessage': {
                        'value': 'Thank you for your patience.'
                    }
                }
            },
            {
                'message': {
                    'plainTextMessage': {
                        'value': 'Just a moment longer.'
                    }
                }
            },
            {
                'message': {
                    'plainTextMessage': {
                        'value': 'Still checking.'
                    }
                }
            }
        ],
        'allowInterrupt': False  # Don't let user interrupt updates
    },

    # TIMEOUT: How long to wait for Lambda before timing out
    'timeoutInSeconds': 90  # AWS: 1-900. Best: 90 sec for complex Claude queries
}

# ============================================================================
# AWS BEST PRACTICE: Post-Fulfillment - CONTINUE conversation for voice
# ============================================================================
POST_FULFILLMENT_SPEC = {
    # SUCCESS: After Lambda returns successfully
    'successResponse': {
        'messageGroups': [
            {
                'message': {
                    'plainTextMessage': {
                        'value': ' '  # Empty - Lambda provides the response
                    }
                }
            }
        ],
        'allowInterrupt': True  # Allow user to interrupt long responses
    },
    'successNextStep': {
        'dialogAction': {
            'type': 'ElicitIntent'  # Continue conversation (NOT EndConversation)
        }
    },

    # FAILURE: If Lambda fails
    'failureResponse': {
        'messageGroups': [
            {
                'message': {
                    'plainTextMessage': {
                        'value': "I'm sorry, I had trouble processing that. Could you try again?"
                    }
                }
            }
        ],
        'allowInterrupt': True
    },
    'failureNextStep': {
        'dialogAction': {
            'type': 'ElicitIntent'  # Continue conversation
        }
    },

    # TIMEOUT: If Lambda takes too long
    'timeoutResponse': {
        'messageGroups': [
            {
                'message': {
                    'plainTextMessage': {
                        'value': "I'm sorry, that's taking longer than expected. Let me try something else. How can I help you?"
                    }
                }
            }
        ],
        'allowInterrupt': True
    },
    'timeoutNextStep': {
        'dialogAction': {
            'type': 'ElicitIntent'  # Continue conversation
        }
    }
}


def get_intent_id(intent_name):
    """Get intent ID by name"""
    paginator_token = None
    while True:
        kwargs = {
            'botId': BOT_ID,
            'botVersion': BOT_VERSION,
            'localeId': LOCALE_ID,
            'maxResults': 50
        }
        if paginator_token:
            kwargs['nextToken'] = paginator_token

        response = client.list_intents(**kwargs)
        for intent in response['intentSummaries']:
            if intent['intentName'] == intent_name:
                return intent['intentId']

        paginator_token = response.get('nextToken')
        if not paginator_token:
            break
    return None


def update_intent_fulfillment(intent_name):
    """Update intent with proper voice fulfillment settings"""
    intent_id = get_intent_id(intent_name)
    if not intent_id:
        print(f"  [SKIP] {intent_name} - not found")
        return False

    print(f"  -> Updating {intent_name} (ID: {intent_id})...")

    # Get current intent
    intent = client.describe_intent(
        botId=BOT_ID,
        botVersion=BOT_VERSION,
        localeId=LOCALE_ID,
        intentId=intent_id
    )

    # Build update params - preserve existing settings
    update_params = {
        'botId': BOT_ID,
        'botVersion': BOT_VERSION,
        'localeId': LOCALE_ID,
        'intentId': intent_id,
        'intentName': intent['intentName'],
    }

    # Preserve optional fields if they exist
    if intent.get('description'):
        update_params['description'] = intent['description']
    if intent.get('sampleUtterances'):
        update_params['sampleUtterances'] = intent['sampleUtterances']
    if intent.get('slotPriorities'):
        update_params['slotPriorities'] = intent['slotPriorities']
    if intent.get('dialogCodeHook'):
        update_params['dialogCodeHook'] = intent['dialogCodeHook']
    if intent.get('intentConfirmationSetting'):
        update_params['intentConfirmationSetting'] = intent['intentConfirmationSetting']
    if intent.get('intentClosingSetting'):
        update_params['intentClosingSetting'] = intent['intentClosingSetting']
    if intent.get('inputContexts'):
        update_params['inputContexts'] = intent['inputContexts']
    if intent.get('outputContexts'):
        update_params['outputContexts'] = intent['outputContexts']
    if intent.get('kendraConfiguration'):
        update_params['kendraConfiguration'] = intent['kendraConfiguration']
    if intent.get('initialResponseSetting'):
        update_params['initialResponseSetting'] = intent['initialResponseSetting']

    # UPDATE: fulfillmentCodeHook with voice-optimized settings
    update_params['fulfillmentCodeHook'] = {
        'enabled': True,
        'fulfillmentUpdatesSpecification': FULFILLMENT_UPDATES_SPEC,
        'postFulfillmentStatusSpecification': POST_FULFILLMENT_SPEC,
        'active': True
    }

    try:
        client.update_intent(**update_params)
        print(f"  [OK] {intent_name} - fulfillment updates enabled")
        return True
    except Exception as e:
        print(f"  [ERROR] {intent_name} - {e}")
        return False


def build_bot():
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
    print("=" * 70)
    print("Fixing Lex V2 Intent Fulfillment for VOICE (AWS Best Practices)")
    print("=" * 70)
    print("\nConfiguration being applied:")
    print("  - delayInSeconds: 1 (play 'please wait' after 1 second)")
    print("  - frequencyInSeconds: 5 (update every 5 seconds)")
    print("  - timeoutInSeconds: 90 (90 sec timeout for Claude)")
    print("  - allowInterrupt: False for wait messages")
    print("  - allowInterrupt: True for final responses")
    print("  - postFulfillment: ElicitIntent (continue conversation)")
    print("")

    updated = 0
    for intent_name in COMPLEX_INTENTS:
        if update_intent_fulfillment(intent_name):
            updated += 1

    print(f"\n[DONE] Updated {updated}/{len(COMPLEX_INTENTS)} intents")

    if updated > 0:
        build_bot()

    print("\n" + "=" * 70)
    print("COMPLETE! Bot is building. Test in ~2 minutes.")
    print("=" * 70)
