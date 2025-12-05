# Voice Configuration Reference - AWS Lex V2

**Generated:** 2025-11-30
**Status:** Stable Production Configuration
**Purpose:** Reference for deployment script validation

---

## Table of Contents
1. [Bot Configuration](#bot-configuration)
2. [Bot Locale Settings](#bot-locale-settings)
3. [Generative AI Settings](#generative-ai-settings)
4. [Voice Settings](#voice-settings)
5. [Bot Alias Configuration](#bot-alias-configuration)
6. [Sentiment Analysis](#sentiment-analysis)
7. [Conversation Logging](#conversation-logging)
8. [Lambda Integration](#lambda-integration)
9. [Fulfillment Configuration (SSML)](#fulfillment-configuration-ssml)
10. [All Intents with Utterances](#all-intents-with-utterances)
11. [AWS CLI Commands Reference](#aws-cli-commands-reference)

---

## Bot Configuration

| Parameter | Value |
|-----------|-------|
| Bot ID | `MCMSOW2OXJ` |
| Bot Name | `pf-scheduling-assistant-dev` |
| Description | ProjectForce Scheduling Assistant (dev) |
| Bot Type | `Bot` |
| Bot Status | `Available` |
| Role ARN | `arn:aws:iam::772634497954:role/pf-lex-bot-role-dev` |
| Idle Session TTL | `300` seconds (5 minutes) |
| Child Directed | `false` |

### AWS CLI Command
```bash
aws lexv2-models describe-bot --bot-id MCMSOW2OXJ --region us-east-1
```

---

## Bot Locale Settings

| Parameter | Value |
|-----------|-------|
| Locale ID | `en_US` |
| Locale Name | English (US) |
| NLU Confidence Threshold | `0.3` |
| Intents Count | `17` |
| Slot Types Count | `0` |
| Bot Locale Status | `Built` |
| Speech Detection Sensitivity | `MaximumNoiseTolerance` |

**Note:** `MaximumNoiseTolerance` provides the best speech recognition in noisy environments. Options are: `Default`, `HighNoiseTolerance`, `MaximumNoiseTolerance`.

### AWS CLI Command
```bash
aws lexv2-models describe-bot-locale \
  --bot-id MCMSOW2OXJ \
  --bot-version DRAFT \
  --locale-id en_US \
  --region us-east-1
```

---

## Generative AI Settings

### Runtime Settings (Assisted NLU)

| Parameter | Value |
|-----------|-------|
| NLU Improvement Enabled | `true` |
| Assisted NLU Mode | `Primary` |

**Note:** Assisted NLU uses LLM through Amazon Bedrock to improve intent classification. In "Primary" mode, LLM is the default classifier.

### Buildtime Settings

| Parameter | Value |
|-----------|-------|
| Descriptive Bot Builder | `false` |
| Sample Utterance Generation | `false` |

### AWS CLI to Update
```bash
aws lexv2-models update-bot-locale \
  --bot-id MCMSOW2OXJ \
  --bot-version DRAFT \
  --locale-id en_US \
  --nlu-intent-confidence-threshold 0.3 \
  --speech-detection-sensitivity MaximumNoiseTolerance \
  --voice-settings '{"voiceId":"Joanna","engine":"neural"}' \
  --generative-ai-settings '{
    "runtimeSettings": {
      "nluImprovement": {
        "enabled": true,
        "assistedNluMode": "Primary"
      }
    },
    "buildtimeSettings": {
      "descriptiveBotBuilder": {"enabled": false},
      "sampleUtteranceGeneration": {"enabled": false}
    }
  }' \
  --region us-east-1
```

---

## Voice Settings

| Parameter | Value |
|-----------|-------|
| Voice ID | `Joanna` |
| Engine | `neural` |

**Note:** Joanna is a US English female voice. Neural engine provides natural-sounding speech.

### Available Voice Options (US English)
- `Joanna` (Female, Neural)
- `Matthew` (Male, Neural)
- `Ivy` (Female child, Neural)
- `Kendra` (Female, Neural)
- `Kimberly` (Female, Neural)
- `Salli` (Female, Neural)
- `Joey` (Male, Neural)
- `Justin` (Male child, Neural)

---

## Bot Alias Configuration

| Parameter | Value |
|-----------|-------|
| Alias ID | `TSTALIASID` |
| Alias Name | `TestBotAlias` |
| Bot Version | `DRAFT` |
| Alias Status | `Available` |

**Note:** `TSTALIASID` is a special test alias that can ONLY point to `DRAFT` version. For production, create a new alias pointing to a numbered version.

### AWS CLI Command
```bash
aws lexv2-models describe-bot-alias \
  --bot-id MCMSOW2OXJ \
  --bot-alias-id TSTALIASID \
  --region us-east-1
```

---

## Sentiment Analysis

| Parameter | Value |
|-----------|-------|
| Detect Sentiment | `true` |

**Note:** When enabled, Lex sends sentiment data to Lambda:
```python
sentiment = event.get('sentimentResponse', {})
# sentiment = {'sentiment': 'POSITIVE|NEGATIVE|NEUTRAL|MIXED', 'sentimentScore': {...}}
```

### Enable via AWS CLI
```bash
aws lexv2-models update-bot-alias \
  --bot-id MCMSOW2OXJ \
  --bot-alias-id TSTALIASID \
  --bot-alias-name TestBotAlias \
  --bot-version DRAFT \
  --sentiment-analysis-settings '{"detectSentiment": true}' \
  --region us-east-1
```

---

## Amazon Connect Settings (CRITICAL for Speech Quality)

| Parameter | Value | Purpose |
|-----------|-------|---------|
| CONTACT_LENS | `true` | Enables Amazon Transcribe for better ASR |
| ENABLE_BOT_ANALYTICS_AND_TRANSCRIPTS | `true` | Saves transcripts for analytics |

**Note:** Without these settings, Lex uses basic ASR which may misrecognize words like "weather" → "day".

### Enable via AWS CLI
```bash
# Enable Contact Lens (better transcription)
aws connect update-instance-attribute \
  --instance-id 3edd99db-14e2-4628-836e-478b574e4b90 \
  --attribute-type CONTACT_LENS \
  --value true \
  --region us-east-1

# Enable Bot Analytics and Transcripts
aws connect update-instance-attribute \
  --instance-id 3edd99db-14e2-4628-836e-478b574e4b90 \
  --attribute-type ENABLE_BOT_ANALYTICS_AND_TRANSCRIPTS \
  --value true \
  --region us-east-1
```

---

## Amazon Transcribe Custom Vocabulary

| Parameter | Value |
|-----------|-------|
| Vocabulary Name | `pf-home-improvement-vocab` |
| Language | `en-US` |
| Total Phrases | `113` |

**Purpose:** Improves recognition of domain-specific terms like "decking", "roofing", "weather", etc.

### Vocabulary Categories:
- **Project Types:** decking, roofing, siding, flooring, fencing, plumbing, gutters, painting, HVAC, electrical, carpentry, drywall, insulation, landscaping
- **Compound Terms:** kitchen-and-bath, doors-and-windows, generator-installation, roof-repair, deck-installation
- **Scheduling:** appointment, schedule, reschedule, cancel, time-slot, tomorrow, today
- **Weather:** weather, forecast, rain, sunny, cloudy, temperature, snow, storm
- **Stores:** Lowes, Home-Depot, Menards
- **Phrases:** how-is-the-weather, list-my-projects, schedule-my-project, who-is-my-technician

### AWS CLI Commands
```bash
# Check vocabulary status
aws transcribe get-vocabulary --vocabulary-name pf-home-improvement-vocab --region us-east-1

# List all vocabularies
aws transcribe list-vocabularies --region us-east-1
```

---

## Amazon Lex V2 Custom Vocabulary (CRITICAL for Real-Time ASR)

**IMPORTANT:** This is DIFFERENT from Amazon Transcribe vocabulary above!
- **Transcribe vocabulary** = Post-call analytics (Contact Lens)
- **Lex V2 vocabulary** = Real-time speech recognition during calls

| Parameter | Value |
|-----------|-------|
| Bot ID | `MCMSOW2OXJ` |
| Locale | `en_US` |
| Total Phrases | `87` |

### Weight System
| Weight | Meaning | Use For |
|--------|---------|---------|
| 0 | No boost (display only) | Display replacements |
| 1 | Default | Standard words |
| 2 | Medium boost | Domain terms |
| 3 | Maximum boost | Frequently misrecognized words |

### Current Vocabulary Phrases

**Weather (Weight 3 - CRITICAL):**
- `weather`, `hows the weather`, `weather tomorrow`, `weather forecast`, `whats the weather`

**Project References (Weight 3 - CRITICAL):**
- `project`, `projects`, `first project`, `second project`, `third project`, `fourth project`, `project details`

**Job Synonyms (Weight 3 - CRITICAL for "job" recognition):**
- `job`, `jobs`, `my job`, `my jobs`, `the job`
- `first job`, `second job`, `third job`, `fourth job`

**Work/Installation Synonyms (Weight 2-3):**
- `work`, `my work`, `the work` (weight 2)
- `installation`, `my installation` (weight 3)

**Scheduling (Weight 2):**
- `schedule`, `appointment`, `reschedule`

**Home Improvement (Weight 3):**
- `decking`, `deck installation`, `fencing`, `flooring`, `plumbing`, `roofing`

**Personnel/Technician References (Weight 3 - CRITICAL):**
- `technician`, `the technician`, `tech`, `who is the technician`, `who is the tech`
- `installer`, `the installer`, `who is the installer`
- `crew`, `the crew`, `crew member`, `who is the crew`
- `worker`, `the worker`, `contractor`, `the contractor`
- `person working`, `the person working`, `who is the person`
- `who is coming`, `who is assigned`, `assigned technician`

**Trade-Specific Workers (Weight 3 - CRITICAL):**
- `plumber`, `the plumber`, `where is the plumber`
- `carpenter`, `the carpenter`, `where is the carpenter`
- `electrician`, `the electrician`, `where is the electrician`
- `where is the technician`, `where is the person`, `where is the crew`, `where is the worker`

**Status/Happening Queries (Weight 3 - CRITICAL):**
- `whats happening`, `what is happening`
- `whats happening with my job`, `whats happening with my project`
- `whats happening with my second job`, `whats happening with my first job`
- `happening with my project`, `status of my job`, `status of my project`

**Position/Ordinal Job References (Weight 3 - CRITICAL):**
- `my first job`, `my second job`, `my third job`

**Other Terms (Weight 2):**
- `kitchen and bath`, `generator installation`, `windows and doors`

### Creating/Updating Vocabulary via AWS CLI

```bash
# Step 1: Create upload URL
aws lexv2-models create-upload-url --region us-east-1

# Step 2: Create CustomVocabulary.tsv file
cat > CustomVocabulary.tsv << 'EOF'
phrase	weight	displayAs
weather	3
hows the weather	3
weather tomorrow	3
project	2
third project	2
decking	3
plumbing	3
EOF

# Step 3: Zip the file
zip vocab.zip CustomVocabulary.tsv

# Step 4: Upload to the URL from step 1
curl -X PUT -H "Content-Type: application/zip" --data-binary @vocab.zip "UPLOAD_URL_FROM_STEP_1"

# Step 5: Start import
aws lexv2-models start-import \
  --import-id IMPORT_ID_FROM_STEP_1 \
  --resource-specification '{"customVocabularyImportSpecification": {"botId": "MCMSOW2OXJ", "botVersion": "DRAFT", "localeId": "en_US"}}' \
  --merge-strategy Overwrite \
  --region us-east-1

# Step 6: Wait for import to complete
aws lexv2-models describe-import --import-id IMPORT_ID --region us-east-1

# Step 7: Rebuild bot to apply vocabulary
aws lexv2-models build-bot-locale \
  --bot-id MCMSOW2OXJ \
  --bot-version DRAFT \
  --locale-id en_US \
  --region us-east-1

# Step 8: Verify vocabulary is active
aws lexv2-models list-custom-vocabulary-items \
  --bot-id MCMSOW2OXJ \
  --bot-version DRAFT \
  --locale-id en_US \
  --region us-east-1
```

### TSV File Format
```
phrase[TAB]weight[TAB]displayAs
weather[TAB]3[TAB]
hows the weather[TAB]3[TAB]
```

**Rules:**
- Max 500 phrases
- Tab-separated (not spaces)
- Weight: 0-3 (3 = maximum boost)
- displayAs: optional (for display replacements)
- File must be named `CustomVocabulary.tsv` in zip

---

## Conversation Logging

| Parameter | Value |
|-----------|-------|
| Text Logging Enabled | `true` |
| CloudWatch Log Group ARN | `arn:aws:logs:us-east-1:772634497954:log-group:/aws/lex/pf-scheduling-assistant-dev/conversation` |
| Log Prefix | `lex-conversation` |

### AWS CLI to Configure
```bash
aws lexv2-models update-bot-alias \
  --bot-id MCMSOW2OXJ \
  --bot-alias-id TSTALIASID \
  --bot-alias-name TestBotAlias \
  --bot-version DRAFT \
  --conversation-log-settings '{
    "textLogSettings": [{
      "enabled": true,
      "destination": {
        "cloudWatch": {
          "cloudWatchLogGroupArn": "arn:aws:logs:us-east-1:772634497954:log-group:/aws/lex/pf-scheduling-assistant-dev/conversation",
          "logPrefix": "lex-conversation"
        }
      }
    }]
  }' \
  --region us-east-1
```

---

## Lambda Integration

| Parameter | Value |
|-----------|-------|
| Lambda ARN | `arn:aws:lambda:us-east-1:772634497954:function:pf-lex-fulfillment-dev` |
| Code Hook Interface Version | `1.0` |
| Locale | `en_US` |

### AWS CLI to Configure
```bash
aws lexv2-models update-bot-alias \
  --bot-id MCMSOW2OXJ \
  --bot-alias-id TSTALIASID \
  --bot-alias-name TestBotAlias \
  --bot-version DRAFT \
  --bot-alias-locale-settings '{
    "en_US": {
      "enabled": true,
      "codeHookSpecification": {
        "lambdaCodeHook": {
          "lambdaARN": "arn:aws:lambda:us-east-1:772634497954:function:pf-lex-fulfillment-dev",
          "codeHookInterfaceVersion": "1.0"
        }
      }
    }
  }' \
  --region us-east-1
```

---

## Fulfillment Configuration (SSML)

All 16 intents use the same SSML-enhanced fulfillment configuration:

| Parameter | Value |
|-----------|-------|
| Active | `true` |
| Start Response Delay | `1` second |
| Update Response Frequency | `5` seconds |
| Timeout | `90` seconds |
| Allow Interrupt | `false` |

### Start Response Messages (SSML)
```xml
<speak><prosody rate="medium" pitch="medium">Let me look that up for you.</prosody><break time="300ms"/></speak>
<speak><prosody rate="medium">One moment please.</prosody><break time="200ms"/></speak>
<speak><prosody rate="medium" pitch="medium">Just a second while I check.</prosody></speak>
<speak><amazon:emotion name="excited" intensity="low">Sure, let me find that for you!</amazon:emotion></speak>
```

### Update Response Messages (SSML)
```xml
<speak><prosody rate="medium">Still working on that<break time="200ms"/>almost there.</prosody></speak>
<speak><prosody rate="medium" pitch="low">Thank you for your patience.</prosody></speak>
<speak>Just a few more seconds<break time="300ms"/>I appreciate you waiting.</speak>
```

### JSON Configuration for Intent Update
```json
{
  "fulfillmentUpdatesSpecification": {
    "active": true,
    "startResponse": {
      "delayInSeconds": 1,
      "messageGroups": [
        {"message": {"ssmlMessage": {"value": "<speak><prosody rate=\"medium\" pitch=\"medium\">Let me look that up for you.</prosody><break time=\"300ms\"/></speak>"}}},
        {"message": {"ssmlMessage": {"value": "<speak><prosody rate=\"medium\">One moment please.</prosody><break time=\"200ms\"/></speak>"}}},
        {"message": {"ssmlMessage": {"value": "<speak><prosody rate=\"medium\" pitch=\"medium\">Just a second while I check.</prosody></speak>"}}},
        {"message": {"ssmlMessage": {"value": "<speak><amazon:emotion name=\"excited\" intensity=\"low\">Sure, let me find that for you!</amazon:emotion></speak>"}}}
      ],
      "allowInterrupt": false
    },
    "updateResponse": {
      "frequencyInSeconds": 5,
      "messageGroups": [
        {"message": {"ssmlMessage": {"value": "<speak><prosody rate=\"medium\">Still working on that<break time=\"200ms\"/>almost there.</prosody></speak>"}}},
        {"message": {"ssmlMessage": {"value": "<speak><prosody rate=\"medium\" pitch=\"low\">Thank you for your patience.</prosody></speak>"}}},
        {"message": {"ssmlMessage": {"value": "<speak>Just a few more seconds<break time=\"300ms\"/>I appreciate you waiting.</speak>"}}}
      ],
      "allowInterrupt": false
    },
    "timeoutInSeconds": 90
  }
}
```

### Interrupt/Barge-In Handling (CRITICAL for Natural Conversations)

**Purpose:** Controls whether users can interrupt the bot while it's speaking. This is crucial for natural voice conversations.

#### How Interrupts Work

| Phase | `allowInterrupt` Setting | User Behavior |
|-------|--------------------------|---------------|
| Start response ("Let me look that up...") | `false` | User's speech is **ignored** |
| Update response ("Still working...") | `false` | User's speech is **ignored** |
| **Final Lambda response** | **Cannot disable** (AWS limitation) | User **CAN interrupt** |

#### Current Configuration

All intents are configured with:
```json
{
  "startResponse": {
    "allowInterrupt": false,
    "delayInSeconds": 1
  },
  "updateResponse": {
    "allowInterrupt": false,
    "frequencyInSeconds": 5
  }
}
```

#### Why This Matters

**Scenario: User asks Q1, then Q2 while processing**
1. User: "whats happening with my second job" (Q1)
2. Bot: "Let me look that up..." (1 second delay)
3. Bot processing... (user speech ignored during this phase)
4. Bot: "Still working on that..." (if >5 seconds)
5. User gets impatient, asks: "actually tell me about the weather" (Q2)
6. **IF still processing**: Q2 is ignored (allowInterrupt=false)
7. **IF Lambda returned and speaking response**: Q2 interrupts, Q1 response stops, Q2 starts processing

#### AWS Limitation

**Important:** Per AWS Lex V2 team confirmation, you **cannot disable barge-in for Lambda fulfillment responses**. Once the final response starts playing, users can always interrupt.

**Workaround (Limited):** Use session attribute `x-amz-lex:allow-interrupt` but this only works for slot prompts, not fulfillment responses.

#### Best Practices

1. **Keep responses short** (under 5-6 seconds) to minimize interrupts
2. **Set `frequencyInSeconds: 5`** so users hear "still working" before getting impatient
3. **Accept interrupts gracefully** - if user asks Q2 while Q1 is answering, they've moved on
4. **Don't repeat Q1 answer** after user asked Q2

#### References
- [AWS Lex Interrupt Bot Documentation](https://docs.aws.amazon.com/lexv2/latest/dg/interrupt-bot.html)
- [Fulfillment Progress Updates](https://docs.aws.amazon.com/lexv2/latest/dg/streaming-progress.html)
- [Stack Overflow - Disable barge-in for fulfillment](https://stackoverflow.com/questions/73031916/in-amazon-lexv2-how-do-i-disable-barge-in-interruption-event-for-fulfillment)

---

### Post-Fulfillment Status Specification (CRITICAL)

**Purpose:** Controls what happens after Lambda fulfillment completes. Without this, the bot ends the conversation after each response.

| Intent | successNextStep | Behavior |
|--------|-----------------|----------|
| All intents (except Goodbye) | `ElicitIntent` | **Continue conversation** - bot asks follow-up questions |
| Goodbye | `EndConversation` | **Hang up** - ends phone call |

**JSON Configuration for Intent Update:**
```json
{
  "postFulfillmentStatusSpecification": {
    "successNextStep": {
      "dialogAction": {
        "type": "ElicitIntent"
      }
    },
    "failureNextStep": {
      "dialogAction": {
        "type": "ElicitIntent"
      }
    },
    "timeoutNextStep": {
      "dialogAction": {
        "type": "ElicitIntent"
      }
    }
  }
}
```

**For Goodbye Intent Only:**
```json
{
  "postFulfillmentStatusSpecification": {
    "successNextStep": {
      "dialogAction": {
        "type": "EndConversation"
      }
    },
    "failureNextStep": {
      "dialogAction": {
        "type": "EndConversation"
      }
    },
    "timeoutNextStep": {
      "dialogAction": {
        "type": "EndConversation"
      }
    }
  }
}
```

**Bug Fixed (2025-11-30):** Without `postFulfillmentStatusSpecification`, Lex defaults to `EndConversation` which prevents follow-up questions like "Would you like to schedule one?" after listing projects.

---

## All Intents with Utterances

## Intents Summary (Updated 2025-12-05)

**Total Utterances: 752** (was 676, added SelectionIntent with 76 utterances)

| Intent | Count | Description |
|--------|-------|-------------|
| AppointmentInquiry | 44 | Check scheduled appointments and installations |
| BusinessHours | 31 | Ask about business and installation hours |
| CancelAppointment | 43 | Cancel an existing installation appointment |
| CheckAvailability | 46 | Check available dates for scheduling installations |
| FallbackIntent | 0 |  |
| Goodbye | 63 | End conversation and disconnect call |
| Help | 29 | Request for assistance or options |
| HowAreYou | 23 | Casual chitchat greeting |
| ProjectInquiry | 72 | List customer projects - includes "job", "work" synonyms |
| ProjectStatusInquiry | 111 | Get project details - includes "job" position refs, installer queries |
| RescheduleAppointment | 42 | Reschedule an existing installation appointment |
| ScheduleAppointment | 76 | Schedule a new appointment - single or multiple pr... |
| **SelectionIntent** | **76** | **NEW (2025-12-05)** Handle ordinal selections during workflows |
| ThankYou | 30 | Express gratitude |
| UrgentRequest | 32 | Handle urgent requests and emergencies |
| WeatherInquiry | 58 | Check weather |
| Welcome | 29 | Greeting and conversation start |

---

## Intent Details

### AppointmentInquiry (44 utterances)

**ID:** `VXOPOOHCBG`

**Description:** Check scheduled appointments and installations

**Utterances:**
- do I have any appointments
- show my appointments
- what appointments do I have
- check my appointments
- list appointments
- any upcoming appointments
- when is my next appointment
- appointment schedule
- my appointments please
- show me my schedule
- my appointments
- I would like to check my appointments
- may I see my appointments
- could you tell me about my appointments
- please show my appointments
- I need to check my schedule
- what is my appointment schedule
- when am I scheduled
- whats on my calendar
- any appointments coming up
- got any appointments
- am I scheduled for anything
- whens my appointment
- when is my installation
- when is my project scheduled
- when is my decking appointment
- when is my roofing scheduled
- when is my flooring installation
- show my installation date
- when are they coming
- when is the installer coming
- when is the technician coming
- when is the crew coming
- appointments
- the appointments
- show appointment
- check appointment
- appointment status
- is anything scheduled
- do I have anything scheduled
- what dates am I booked for
- show my booked dates
- when is my next install
- upcoming installations

---

### BusinessHours (31 utterances)

**ID:** `0UB7GOGZ8Y`

**Description:** Ask about business and installation hours

**Utterances:**
- what are your hours
- when are you open
- business hours
- operating hours
- what time do you open
- what time do you close
- are you open on weekends
- hours of operation
- when can I call
- office hours
- what are your working hours
- store hours
- are you open today
- are you open tomorrow
- are you open on saturday
- are you open on sunday
- what days are you open
- when do you start work
- when do installers work
- what time does installation start
- earliest appointment time
- latest appointment time
- do you work on holidays
- are you open on christmas
- are you closed on thanksgiving
- when can I schedule an appointment
- what hours do you install
- do you do evening appointments
- do you work mornings
- can you come early morning
- can you come late afternoon

---

### CancelAppointment (43 utterances)

**ID:** `SUVLXFCFSD`

**Description:** Cancel an existing installation appointment

**Utterances:**
- cancel my appointment
- I need to cancel
- cancel the appointment
- remove my appointment
- I want to cancel
- cancel please
- delete appointment
- I cannot make it
- cancel my booking
- I would like to cancel my appointment
- may I cancel please
- I need to cancel my scheduled appointment
- please cancel my appointment
- cancel it
- just cancel
- nevermind cancel it
- do not come
- do not need it anymore
- changed my mind
- not doing it anymore
- forget it
- cancel my installation
- cancel my project
- cancel the install
- cancel my decking installation
- cancel my roofing appointment
- cancel my flooring project
- do not install it
- cancel the scheduled work
- cancel the crew
- I changed my mind about the project
- I do not want to proceed
- I decided not to do it
- we are not doing the project
- can I cancel
- how do I cancel
- is it too late to cancel
- can I still cancel
- what if I cancel
- stop the project
- cancel everything
- cancel my deck project
- cancel my roof work

---

### CheckAvailability (46 utterances)

**ID:** `RGLVYXCNQV`

**Description:** Check available dates for scheduling installations

**Utterances:**
- what dates are available
- show available dates
- when can I schedule
- available times
- what times work
- check availability
- when are you available
- show me available slots
- open dates
- free dates
- what days are open
- available appointments
- I would like to know what dates are available
- may I see available times
- could you show me the available dates
- please check availability
- what would be a good time
- when would be convenient
- when can you come
- when can you guys come out
- whats open
- got any openings
- any slots available
- when can we do this
- earliest available
- soonest available
- next available date
- when can you install
- when can you do the work
- when can you start the project
- when can you start my deck
- when can you do my roof
- when can you install my flooring
- available dates for installation
- installation availability
- what about next week
- anything this week
- any openings this month
- do you have anything on monday
- availability for tuesday
- can you come this weekend
- saturday availability
- how soon can you come
- how quickly can you schedule
- what is your earliest availability
- when is the next opening

---

### FallbackIntent (0 utterances)

**ID:** `FALLBCKINT`

**Description:** 


---

### Goodbye (30 utterances)

**ID:** `PSJPHS0KWO`

**Description:** End conversation and disconnect call

**Utterances:**
- goodbye
- bye
- bye bye
- see you
- see you later
- thanks bye
- thank you goodbye
- ok bye
- alright bye
- that is all
- thats all
- that will be all
- I am done
- im done
- all done
- nothing else
- no more questions
- I am finished
- we are done
- thanks thats all
- thank you thats all
- hang up
- end call
- disconnect
- end the call
- take care
- have a good day
- talk to you later
- thanks for your help goodbye
- that helps thanks bye

---

### Help (29 utterances)

**ID:** `U624AG4X78`

**Description:** Request for assistance or options

**Utterances:**
- help
- help me
- I need help
- can you help
- what can you do
- what are my options
- how does this work
- I need assistance
- can you assist me
- I am confused
- I do not understand
- what should I do
- guide me
- walk me through this
- I am not sure what to do
- help please
- I need some help
- can someone help me
- what do I do
- how do I use this
- what can I ask you
- what are you able to do
- show me what you can do
- what services do you offer
- how can you help me
- I am lost
- start over
- I need to talk to someone
- can I speak to a person

---

### HowAreYou (23 utterances)

**ID:** `BN56AGSEGR`

**Description:** Casual chitchat greeting

**Utterances:**
- how are you
- how are you doing
- how is it going
- what is up
- how do you do
- are you doing well
- hows everything
- how have you been
- you doing okay
- how are things
- hows your day
- hows it going today
- you good
- all good
- everything alright
- are you okay
- are you well
- how is your day going
- having a good day
- busy today
- how is work
- nice to talk to you
- good to hear from you

---

### ProjectInquiry (72 utterances)

**ID:** `YJY8BUBCWL`

**Description:** List customer projects - includes "job", "work" synonyms

**Utterances:**
- list my projects
- show my projects
- what are my projects
- tell me about my projects
- get my projects
- my projects
- show projects
- what projects do I have
- projects please
- can you list my projects
- I want to see my projects
- I would like to see my projects
- may I see my projects please
- could you show me my projects
- please show my projects
- whats up with my projects
- show me what I got
- what do I have going on
- any projects
- got any projects
- my stuff
- show my stuff
- what am I working on
- whats going on with my work
- show my decking project
- list my roofing projects
- my siding project
- show my flooring project
- list my fencing project
- my painting project
- show my window project
- my kitchen project
- my bathroom project
- show my gutter project
- list my deck project
- my roof project
- list my products
- show my products
- what products do I have
- my products please
- tell me about my products
- show me my products
- what are my products
- products
- the products
- what work do I have
- show my home improvement projects
- list my installation projects
- what installations do I have
- show my jobs
- my jobs please
- what jobs are pending
- do I have any projects
- how many projects do I have
- what projects are there
- any pending projects
- my lowes projects
- show my lowes work
- list my store projects
- **NEW (2025-12-02) - "job" synonyms:**
- list my jobs
- what jobs do I have
- show me my jobs
- my job please
- tell me about my jobs
- any jobs
- how many jobs do I have
- whats my job status
- list my work
- what work do I have
- show my work
- my work please
- my installations
- list my installations
- what installations do I have

---

### ProjectStatusInquiry (91 utterances)

**ID:** `TEGINHT7UD`

**Description:** Get project details - includes "job" position refs, installer queries

**Utterances:**
- details of second project
- first project details
- info on third project
- more info on project one
- tell me about my project
- last project details
- can you give me details of third project
- tell me about the product
- how is my project doing
- give me a status update
- what is the status
- details of first project
- can i get details
- second project details
- show me details
- product details
- more about the second one
- get status
- give me details of the third project
- what is project number one
- details of the last one
- give me details of second project
- details on second
- i need details
- show me the third project
- show me status
- info on the last project
- second one please
- details of the third project
- details for project two
- product information
- details of project 2
- project status
- give me the details
- what about the third project
- what is the status of my project
- details of the first project
- status update please
- tell me about the third project
- show me third project
- details of the previous one
- tell me about project 3
- third project details
- details please
- tell me more about second project
- number two
- give me details of third project
- more about second project
- what about the second project
- tell me about the first one
- the product please
- fourth project details
- can i get details of second project
- details of the product
- fifth project details
- details of third project
- what about the product
- tell me about the second project
- give me details of first project
- check project status
- i want details
- the second one
- show me project 1
- **NEW (2025-12-02) - "job" position references:**
- first job details
- second job details
- third job details
- fourth job details
- tell me about the first job
- tell me about the second job
- info on the first job
- info on the second job
- whats the first job
- whats the second job
- details of first job
- details of second job
- the first job
- the second job
- job number one
- job number two
- **NEW (2025-12-02) - installer/technician queries:**
- who is the installer
- who is my installer
- who is the technician
- who is my technician
- who is coming
- who is doing the work
- who is the crew
- whos the installer for the first project
- technician for second project
- installer for the first job
- who is working on my project
- whos my contractor

---

### RescheduleAppointment (42 utterances)

**ID:** `PBBQ0R75L3`

**Description:** Reschedule an existing installation appointment

**Utterances:**
- reschedule my appointment
- change my appointment
- move my appointment
- I need to reschedule
- can I change the time
- change appointment time
- reschedule please
- move to a different day
- pick a different time
- change the date
- I would like to reschedule my appointment
- may I change my appointment
- could we reschedule please
- I need to move my appointment to another day
- would it be possible to reschedule
- can we move it
- push it back
- can you come a different day
- need to change it
- gotta reschedule
- something came up need to move it
- that day does not work
- need a new date
- reschedule my installation
- change my install date
- move my project date
- reschedule my decking installation
- change my roofing appointment
- move my flooring install
- need to change when you come
- can the crew come a different day
- something came up
- I have a conflict
- I will not be home
- that time does not work for me
- can I reschedule
- is it possible to reschedule
- how do I reschedule
- can we pick a new date
- change when they come
- move my deck installation
- reschedule my roof appointment

---

### ScheduleAppointment (76 utterances)

**ID:** `QM4EPLIJF2`

**Description:** Schedule a new appointment - single or multiple projects

**Utterances:**
- schedule all my projects
- schedule for tomorrow
- schedule not reschedule
- lets schedule it
- schedule project
- sure schedule it
- lets schedule
- can you schedule
- schedule my project
- book new appointment
- book for tuesday
- schedule the first project
- schedule something
- schedule my roofing project
- schedule for monday
- set up a new appointment
- schedule that
- schedule the last project
- book both
- schedule both projects
- yes book it
- book it
- okay book it
- create new booking
- schedule the first two projects
- schedule my flooring project
- book for next week
- i want to schedule
- i need a new appointment
- schedule this project
- book appointment for project
- book an appointment
- schedule this project please
- make an appointment
- schedule the second project
- schedule them all
- schedule appointment for project
- set up an appointment
- schedule my decking project
- book that
- set it up
- schedule first two projects
- new appointment
- lets book it
- book a new one
- set up appointment for this project
- book all projects
- schedule the appointment
- schedule a new one
- please book it
- book this project
- make a new appointment
- okay schedule it
- create an appointment
- I want to schedule my project
- schedule for this week
- book a time
- go ahead and schedule
- i want to book
- schedule an appointment
- please schedule
- I want to book
- schedule them
- schedule first three projects
- schedule my siding project
- I need to schedule
- new booking please
- yes schedule
- I need to book an appointment
- yeah schedule it
- schedule it
- can you schedule my project
- schedule the project
- go ahead and book
- schedule all projects
- schedule multiple projects

---

### SelectionIntent (76 utterances) - NEW 2025-12-05

**ID:** `I0RK8IU57Z`

**Description:** Handle ordinal selections during workflows (VOICE-SPECIFIC). Used when user needs to select a project during reschedule/cancel flows. Utterances are unique and don't conflict with ProjectStatusInquiry.

**Purpose:** Prevents FallbackIntent when user says things like "the fourth one", "I want the first one" during a workflow.

**Utterances:**
- I want the first one
- I want the second one
- I want the third one
- I want the fourth one
- I want the fifth one
- I want the sixth one
- I want the seventh one
- I want the eighth one
- I want first
- I want second
- I want third
- I want fourth
- let's do the first one
- let's do the second one
- let's do the third one
- let's do the fourth one
- lets do first
- lets do second
- lets do third
- lets do fourth
- go with the first one
- go with the second one
- go with the third one
- go with the fourth one
- go with first
- go with second
- go with third
- go with fourth
- I'll take the first one
- I'll take the second one
- I'll take the third one
- I'll take the fourth one
- ill take first
- ill take second
- ill take third
- ill take fourth
- yes that one
- yeah that one
- that one please
- yes this one
- first please
- second please
- third please
- fourth please
- the first one please
- the second one please
- the third one please
- the fourth one please
- select the first
- select the second
- select the third
- select the fourth
- pick the first
- pick the second
- pick the third
- pick the fourth
- choose the first
- choose the second
- choose the third
- choose the fourth
- I pick one
- I pick two
- I pick three
- I pick four
- I choose one
- I choose two
- I choose three
- I choose four
- reschedule the first one
- reschedule the second one
- reschedule the third one
- reschedule the fourth one
- cancel the first one
- cancel the second one
- cancel the third one
- cancel the fourth one

---

### ThankYou (30 utterances)

**ID:** `ZXU2R1QSAL`

**Description:** Express gratitude

**Utterances:**
- thank you
- thanks
- thanks a lot
- thank you so much
- appreciate it
- that is helpful
- thanks for your help
- thank you very much
- you have been helpful
- great thanks
- thank you kindly
- many thanks
- thanks so much
- I appreciate your help
- that was very helpful
- you are very helpful
- thanks for the information
- thank you for your time
- I really appreciate it
- that helps a lot
- perfect thank you
- wonderful thanks
- excellent thank you
- great help
- very helpful
- you are awesome
- thanks a bunch
- cheers
- much appreciated
- grateful for your help

---

### UrgentRequest (32 utterances)

**ID:** `JQG27LEZWL`

**Description:** Handle urgent requests and emergencies

**Utterances:**
- this is urgent
- emergency
- I need help urgently
- urgent matter
- this is an emergency
- urgent request
- I have an urgent issue
- need immediate help
- this is very urgent
- please help me urgently
- I have an emergency
- urgent problem
- critical issue
- my roof is leaking
- water is coming in
- something broke
- there is a problem with the installation
- the installer did not show up
- nobody came today
- I need someone right now
- can someone come today
- this cannot wait
- I need help immediately
- please hurry
- asap
- as soon as possible
- right away please
- I have a leak
- something is wrong
- there is damage
- the work is not done
- they left in the middle

---

### WeatherInquiry (58 utterances)

**ID:** `AKQZWPAKFN`

**Description:** Check weather

**Utterances:**
- hows the weather outside
- tomorrow forecast
- weather please
- whats the weather like
- tell me weather
- will it snow
- will it be cloudy
- is it hot outside
- weather today
- what is the weather today
- weather report
- what is the forecast
- current weather
- is it chilly
- weather tomorrow
- forecast for tomorrow
- will it be cold tomorrow
- weather in
- weather update
- tomorrow weather
- tell me the weather
- weekend weather
- check the weather
- how is the weather today
- is it warm
- what will the weather be tomorrow
- will it rain
- will it be hot tomorrow
- weather on sunday
- todays weather
- weather at the job site
- weather forecast
- will it be chilly
- will it be sunny
- is it cold outside
- weather for tomorrow please
- temperature tomorrow
- weather at the project location
- how hot will it be
- how cold will it be
- will it be cold
- will it be warm
- get weather
- will it rain tomorrow
- check weather
- what is the weather tomorrow
- weather for tomorrow
- how is the weather
- weather conditions
- weather at the address
- weather this weekend
- will it be hot
- is it going to rain
- is it freezing
- weather on saturday
- whats the temperature
- is it going to rain tomorrow
- what is the weather

---

### Welcome (29 utterances)

**ID:** `9XKZJOE7EX`

**Description:** Greeting and conversation start

**Utterances:**
- hello
- hi
- hey
- good morning
- good afternoon
- greetings
- hi there
- hello there
- hey there
- good evening
- howdy
- hiya
- yo
- whats up
- sup
- good day
- top of the morning
- hi its me
- hello its me calling
- this is calling about my project
- hi I am calling about my installation
- hello I need help
- hi I have a question
- hello can you help me
- hey I need some information
- hi this is about my appointment
- good morning I am calling about my project
- hello I would like some help please
- hi may I speak to someone

---


---

## AWS CLI Commands Reference

### List All Bots
```bash
aws lexv2-models list-bots --region us-east-1
```

### Describe Bot
```bash
aws lexv2-models describe-bot --bot-id MCMSOW2OXJ --region us-east-1
```

### Describe Bot Locale
```bash
aws lexv2-models describe-bot-locale \
  --bot-id MCMSOW2OXJ \
  --bot-version DRAFT \
  --locale-id en_US \
  --region us-east-1
```

### List Intents
```bash
aws lexv2-models list-intents \
  --bot-id MCMSOW2OXJ \
  --bot-version DRAFT \
  --locale-id en_US \
  --region us-east-1
```

### Describe Intent
```bash
aws lexv2-models describe-intent \
  --bot-id MCMSOW2OXJ \
  --bot-version DRAFT \
  --locale-id en_US \
  --intent-id <INTENT_ID> \
  --region us-east-1
```

### Build Bot Locale
```bash
aws lexv2-models build-bot-locale \
  --bot-id MCMSOW2OXJ \
  --bot-version DRAFT \
  --locale-id en_US \
  --region us-east-1
```

### Create Bot Version
```bash
aws lexv2-models create-bot-version \
  --bot-id MCMSOW2OXJ \
  --bot-version-locale-specification '{"en_US": {"sourceBotVersion": "DRAFT"}}' \
  --region us-east-1
```

### Update Bot Alias
```bash
aws lexv2-models update-bot-alias \
  --bot-id MCMSOW2OXJ \
  --bot-alias-id TSTALIASID \
  --bot-alias-name TestBotAlias \
  --bot-version DRAFT \
  --region us-east-1
```

### Describe Bot Alias
```bash
aws lexv2-models describe-bot-alias \
  --bot-id MCMSOW2OXJ \
  --bot-alias-id TSTALIASID \
  --region us-east-1
```

### List Bot Versions
```bash
aws lexv2-models list-bot-versions \
  --bot-id MCMSOW2OXJ \
  --region us-east-1
```

---

## Bot Version History

| Version | Status | Created |
|---------|--------|---------|
| DRAFT | Available | Initial |
| 1 | Available | 1764484244.395 |
| 2 | Available | 1764485302.463 |
| 3 | Available | 1764487746.903 |
| 4 | Available | 1764488786.315 |

---

## Python Script to Verify Configuration

```python
import boto3
import json

def verify_lex_config():
    client = boto3.client('lexv2-models', region_name='us-east-1')
    bot_id = 'MCMSOW2OXJ'

    # Get bot locale
    locale = client.describe_bot_locale(
        botId=bot_id,
        botVersion='DRAFT',
        localeId='en_US'
    )

    # Check Generative AI
    gen_ai = locale.get('generativeAISettings', {})
    nlu_enabled = gen_ai.get('runtimeSettings', {}).get('nluImprovement', {}).get('enabled', False)
    nlu_mode = gen_ai.get('runtimeSettings', {}).get('nluImprovement', {}).get('assistedNluMode', '')

    # Check Voice
    voice = locale.get('voiceSettings', {})
    voice_id = voice.get('voiceId', '')
    engine = voice.get('engine', '')

    # Get alias for sentiment
    alias = client.describe_bot_alias(
        botId=bot_id,
        botAliasId='TSTALIASID'
    )
    sentiment = alias.get('sentimentAnalysisSettings', {}).get('detectSentiment', False)

    print(f"Assisted NLU Enabled: {nlu_enabled}")
    print(f"Assisted NLU Mode: {nlu_mode}")
    print(f"Voice ID: {voice_id}")
    print(f"Voice Engine: {engine}")
    print(f"Sentiment Analysis: {sentiment}")

    # Count intents
    intents = []
    next_token = None
    while True:
        if next_token:
            resp = client.list_intents(botId=bot_id, botVersion='DRAFT', localeId='en_US', nextToken=next_token)
        else:
            resp = client.list_intents(botId=bot_id, botVersion='DRAFT', localeId='en_US')
        intents.extend(resp['intentSummaries'])
        next_token = resp.get('nextToken')
        if not next_token:
            break

    print(f"Total Intents: {len(intents)}")

    # Check SSML on each intent
    ssml_count = 0
    for intent in intents:
        details = client.describe_intent(
            botId=bot_id,
            botVersion='DRAFT',
            localeId='en_US',
            intentId=intent['intentId']
        )
        fulfillment = details.get('fulfillmentCodeHook', {})
        updates = fulfillment.get('fulfillmentUpdatesSpecification', {})
        if updates.get('active'):
            start = updates.get('startResponse', {})
            msgs = start.get('messageGroups', [])
            if msgs and 'ssmlMessage' in msgs[0].get('message', {}):
                ssml_count += 1

    print(f"Intents with SSML: {ssml_count}/{len(intents)}")

if __name__ == '__main__':
    verify_lex_config()
```

---

## IAM Role Configuration

The Lex bot requires an IAM role with specific permissions.

| Parameter | Value |
|-----------|-------|
| Role Name | `pf-lex-bot-role-dev` |
| Role ARN | `arn:aws:iam::772634497954:role/pf-lex-bot-role-dev` |

### Trust Policy
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lexv2.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

### Attached Policies
- `ComprehendFullAccess` - For sentiment analysis
- `AmazonLexFullAccess` - For Lex operations

### AWS CLI to Create Role
```bash
# Create role with trust policy
aws iam create-role \
  --role-name pf-lex-bot-role-dev \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "lexv2.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Attach policies
aws iam attach-role-policy \
  --role-name pf-lex-bot-role-dev \
  --policy-arn arn:aws:iam::aws:policy/ComprehendFullAccess

aws iam attach-role-policy \
  --role-name pf-lex-bot-role-dev \
  --policy-arn arn:aws:iam::aws:policy/AmazonLexFullAccess
```

---

## Lambda Function Configuration

The Lex fulfillment Lambda must have specific settings.

| Parameter | Value |
|-----------|-------|
| Function Name | `pf-lex-fulfillment-dev` |
| Runtime | `python3.11` |
| Memory | `512` MB |
| Timeout | `60` seconds |
| Handler | `handler.lambda_handler` |

### Resource Policy (Lex Permission)
The Lambda must allow Lex to invoke it:

```bash
aws lambda add-permission \
  --function-name pf-lex-fulfillment-dev \
  --statement-id AllowLexInvoke \
  --action lambda:InvokeFunction \
  --principal lexv2.amazonaws.com \
  --source-arn "arn:aws:lex:us-east-1:ACCOUNT_ID:bot-alias/BOT_ID/*"
```

### Resource Policy (Connect Permission)
For Amazon Connect integration:

```bash
aws lambda add-permission \
  --function-name pf-lex-fulfillment-dev \
  --statement-id AllowConnectInvoke \
  --action lambda:InvokeFunction \
  --principal connect.amazonaws.com \
  --source-arn "arn:aws:connect:us-east-1:ACCOUNT_ID:instance/INSTANCE_ID"
```

---

## Amazon Connect Contact Flows

| Flow Name | Flow ID | Type |
|-----------|---------|------|
| pf-main-inbound-voice | `6b9d1980-82df-4ca8-a448-398050cc2b57` | CONTACT_FLOW |
| pf-scheduling-voice-dev | `b830c12f-988b-4c62-8a06-3abc6b6c28c9` | CONTACT_FLOW |

**Note:** Contact flows are created via AWS Connect console or the DEPLOY script. The flow JSON is generated dynamically based on the Lex bot ID and alias.

### List Contact Flows
```bash
aws connect list-contact-flows \
  --instance-id 3edd99db-14e2-4628-836e-478b574e4b90 \
  --contact-flow-types CONTACT_FLOW \
  --region us-east-1
```

---

## Amazon Connect Phone Numbers

| Phone Number | Type | Country |
|--------------|------|---------|
| +14702832382 | DID | US |

**Note:** Phone numbers are associated with Contact Flows. The DEPLOY script handles phone number association automatically.

### Associate Phone Number with Contact Flow
```bash
aws connect associate-phone-number-contact-flow \
  --phone-number-id PHONE_NUMBER_ID \
  --instance-id INSTANCE_ID \
  --contact-flow-id CONTACT_FLOW_ID \
  --region us-east-1
```

---

## Important Notes

1. **TSTALIASID Limitation**: The TestBotAlias can ONLY point to DRAFT version. For production, create a custom alias.

2. **Assisted NLU**: Must rebuild bot after enabling for changes to take effect.

3. **SSML Tags Supported**:
   - `<speak>` - Root element
   - `<prosody rate="..." pitch="...">` - Control speech rate and pitch
   - `<break time="..."/>` - Add pauses
   - `<amazon:emotion name="..." intensity="...">` - Add emotional tone

4. **Fulfillment Timeout**: Set to 90 seconds to allow for backend processing.

5. **Sentiment Analysis**: Enabled on alias, not bot. Must update alias to change.

6. **Data Privacy**: `childDirected: false` - Required setting for COPPA compliance.

7. **Lex V2 Custom Vocabulary vs Transcribe Vocabulary**:
   - **Lex V2 vocabulary** = Real-time speech recognition during calls
   - **Transcribe vocabulary** = Post-call analytics (Contact Lens)
   - Both are needed for comprehensive speech recognition improvement.

---

## Voice Response Formatting (Updated 2025-12-05)

### Project Details - Voice-Specific Formatting

**Location:** `lambda/orchestrator/voice_formatter.py` - `_format_project_details_for_voice()`

**Key Changes:**
1. **No project ID/number narration** - User already knows which project (they asked "tell me about the first one")
2. **Comprehensive details included:** Status, technician, address, store, weather
3. **Natural language** - No technical IDs or numbers

**Before (BAD for voice):**
```
"Project number 7-7-5-1-7-4-2. The status is scheduled..."
```

**After (GOOD for voice):**
```
"Here are the details for your flooring project. The status is scheduled.
It's scheduled for Tuesday, December 10th. Your technician is John Smith.
The work address is 123 Main Street, Dallas, Texas.
Weather forecast for your appointment day: Partly cloudy. Expected high of 72 degrees."
```

### Ordinal Reference Path - Direct Voice Formatting

**Location:** `lambda/orchestrator/intelligent_orchestrator.py` - Lines 1577-1589

**Problem Solved:** Router strips JSON before `format_for_voice()`, causing:
- `_format_project_details_for_voice()` was NEVER called
- Text truncated to 3 sentences + 300 chars

**Solution:** For voice channel, call `_format_project_details_for_voice()` directly:
```python
if channel == 'voice':
    # Direct voice formatting - includes all details
    voice_text = _format_project_details_for_voice(response_body)
    voice_text = _add_voice_opener(voice_text, 'information')
    voice_text = _add_voice_followup(voice_text, 'information')
    response_text = voice_text
else:
    # Chat/SMS: Use standard formatting with JSON
    response_text = format_lambda_response('get_project_details', response_body, message)
```

### Voice Engagement Elements

| Element | Purpose | Example |
|---------|---------|---------|
| Voice Opener | Engaging start | "Great! Here are the details..." |
| Voice Follow-up | Continue conversation | "Is there anything else I can help you with?" |

**Applied to:**
- Project details response
- Project list response
- All JSON-based responses

---

### Ordinal Action Detection (All Channels)

**Location:** `lambda/orchestrator/intelligent_orchestrator.py` - Lines 1475-1512

**Note:** Originally voice-only, now works for ALL channels (chat, voice, SMS).

**Actions Detected:**
| Action | Keywords |
|--------|----------|
| SCHEDULE | schedule, book, set up, make an appointment, available dates |
| RESCHEDULE | reschedule, move, change the date, different date, another date |
| CANCEL | cancel, remove, delete, dont want |

**How it works:**
1. Ordinal detected (first, second, last project)
2. Action word detected → saves `resolved_project_id` to workflow state
3. Falls through to classification with project context
4. Classification routes to appropriate action (schedule/reschedule/cancel)

---

*Last verified: 2025-12-05*
