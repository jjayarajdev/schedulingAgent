# AWS Console Setup Guide - Voice Integration

**Date:** November 9, 2025
**Purpose:** Step-by-step guide to set up AWS Connect voice integration using AWS Console

---

## Overview

This guide walks you through setting up AWS Connect voice integration entirely through the AWS Console. No Terraform required for the initial setup.

**Total Time:** 30-40 minutes
**Prerequisites:** AWS account with admin access

---

## Part 1: Create AWS Connect Instance & Get Phone Number (10-15 minutes)

### Step 1.1: Open AWS Connect Console

1. Go to: https://console.aws.amazon.com/connect/
2. **Region:** Ensure you're in **US East (N. Virginia) us-east-1** (top-right corner)

### Step 1.2: Create Connect Instance

1. Click **"Create instance"** button

2. **Step 1 - Identity management:**
   - Select: ☑️ **"Store users within Amazon Connect"**
   - **Access URL:** Enter unique alias (e.g., `pf-voice-dev-2025` or `projectforce-voice`)
     - This becomes: `https://pf-voice-dev-2025.my.connect.aws`
     - Must be globally unique
   - Click **"Next"**

3. **Step 2 - Administrator:**
   - You can skip this for now
   - Click **"Skip this"**

4. **Step 3 - Telephony:**
   - ✅ Check: **"I want to handle incoming calls with Amazon Connect"**
   - ✅ Check: **"I want to make outbound calls with Amazon Connect"**
   - Click **"Next"**

5. **Step 4 - Data storage:**
   - Accept defaults (S3 buckets will be auto-created)
   - ✅ **Call recordings:** Enabled
   - ✅ **Chat transcripts:** Enabled (optional)
   - Click **"Next"**

6. **Step 5 - Review and create:**
   - Review your settings
   - Click **"Create instance"**
   - ⏱️ Wait 2-3 minutes for instance to provision
   - You'll see: **"Your Amazon Connect instance has been created successfully"**

7. **Important:** Copy your instance URL (e.g., `https://pf-voice-dev-2025.my.connect.aws`)

### Step 1.3: Claim Your Phone Number

1. After instance is created, you'll see a button: **"Get started"** or **"Claim phone number"**
   - Click it

2. **Choose phone number type:**

   **Option A: Toll-Free Number (Recommended)**
   - Select **"Toll free"**
   - Country: **United States +1**
   - You'll see a list of available 1-800 numbers
   - Select one you like
   - Cost: **$2.00/month + $0.022/min** for inbound calls

   **Option B: Direct Dial (Local Number)**
   - Select **"DID (Direct Inward Dialing)"**
   - Country: **United States +1**
   - Choose a number (may have limited availability)
   - Cost: **$0.90/month + $0.0022/min** for inbound calls

3. Click **"Claim number"**

4. **Success!** Your phone number is now claimed
   - Copy your phone number (e.g., `+1-800-555-1234`)
   - Write it down - you'll need it later

### Step 1.4: Initial Test (Optional)

1. From the Connect dashboard, click **"Test chat"** or **"Test call"**
2. Call your new number from your mobile phone
3. You should hear: *"Welcome to Amazon Connect..."*
4. This confirms telephony is working
5. Hang up

**✅ Part 1 Complete:** You now have an AWS Connect instance and a phone number!

---

## Part 2: Create Amazon Lex Bot (15-20 minutes)

### Step 2.1: Open Amazon Lex Console

1. Go to: https://console.aws.amazon.com/lexv2/
2. **Region:** Ensure you're in **US East (N. Virginia) us-east-1**
3. Click **"Create bot"**

### Step 2.2: Configure Bot Basics

1. **Creation method:**
   - Select: ☑️ **"Create a blank bot"**

2. **Bot name:** `pf-scheduling-assistant`

3. **Description:** `AI voice assistant for project scheduling`

4. **IAM permissions:**
   - Select: ☑️ **"Create a role with basic Amazon Lex permissions"**
   - Role name: `AmazonLexBotRole-pf-scheduling`

5. **Children's Online Privacy Protection Act (COPPA):**
   - Select: **No**

6. **Idle session timeout:** `10 minutes`

7. Click **"Next"**

### Step 2.3: Add Language

1. **Language:** `English (US)`

2. **Voice interaction:**
   - **Voice:** Select **"Joanna"** (clear, professional female voice)
     - Or choose: Matthew, Salli, Kendra, Kimberly, Ivy, Joey, Justin, Kevin, Ruth, Stephen
   - **Intent classification confidence score:** `0.40` (default)

3. Click **"Done"**

### Step 2.4: Create Intents

Now you'll create several intents (what users can ask for).

#### Intent 1: Welcome Intent

1. In the left sidebar, under **Intents**, click **"Add intent"** → **"Add empty intent"**

2. **Intent name:** `Welcome`

3. Click **"Add"**

4. **Sample utterances** (what users might say):
   - Click **"Add utterance"**
   - Add these one by one:
     ```
     hello
     hi
     help
     what can you do
     how does this work
     start
     ```

5. **Closing response** (what the bot says back):
   - Scroll to **"Closing responses"**
   - Click **"Add message group"**
   - **Message:**
     ```
     Hello! Welcome to ProjectForce. I'm your AI scheduling assistant.
     I can help you check your projects, schedule appointments, or answer questions.
     What would you like to do today?
     ```
   - Click **"Save intent"**

#### Intent 2: Check Projects Intent

1. Click **"Add intent"** → **"Add empty intent"**

2. **Intent name:** `CheckProjects`

3. **Sample utterances:**
   ```
   show me my projects
   list my projects
   what projects do I have
   check my projects
   do I have any projects
   tell me about my projects
   ```

4. **Closing response:**
   - **Message:**
     ```
     Let me check your projects for you. I'll look those up right now.
     ```
   - Click **"Save intent"**

#### Intent 3: Schedule Appointment Intent

1. Click **"Add intent"** → **"Add empty intent"**

2. **Intent name:** `ScheduleAppointment`

3. **Sample utterances:**
   ```
   schedule an appointment
   book an appointment
   I need to schedule
   set up an appointment
   schedule my project
   book a time
   I want to schedule
   ```

4. **Closing response:**
   - **Message:**
     ```
     I can help you schedule an appointment. Let me connect you with our scheduling system.
     ```
   - Click **"Save intent"**

#### Intent 4: Weather Inquiry Intent

1. Click **"Add intent"** → **"Add empty intent"**

2. **Intent name:** `WeatherInquiry`

3. **Sample utterances:**
   ```
   what's the weather
   check the weather
   is it going to rain
   weather forecast
   how's the weather
   what's the temperature
   ```

4. **Closing response:**
   - **Message:**
     ```
     Let me check the weather for you.
     ```
   - Click **"Save intent"**

#### Intent 5: Fallback Intent (Already Created)

Lex automatically creates a **FallbackIntent** for unrecognized requests.

1. In the left sidebar, click **"FallbackIntent"**

2. **Closing response:**
   - Edit the default message to:
     ```
     I didn't quite understand that. Let me transfer you to our advanced AI assistant who can help.
     ```
   - Click **"Save intent"**

### Step 2.5: Build the Bot

1. In the top-right corner, click **"Build"** button

2. You'll see a popup: *"Building bot language..."*

3. ⏱️ Wait 1-2 minutes for build to complete

4. You'll see: ✅ **"Build successful"**

### Step 2.6: Test the Bot (Optional but Recommended)

1. In the right panel, you should see **"Test"** section

2. If not visible, click **"Test"** button in top-right

3. Try typing or speaking:
   - "hello" → Should trigger Welcome intent
   - "show my projects" → Should trigger CheckProjects intent
   - "schedule appointment" → Should trigger ScheduleAppointment intent

4. Verify responses are correct

### Step 2.7: Create Bot Alias

1. In the left sidebar, click **"Aliases"**

2. Click **"Create alias"**

3. **Alias name:** `prod`

4. **Description:** `Production alias for voice integration`

5. **Bot version:** `Draft version`

6. **Lambda function** (we'll add this later after deploying Lambda)
   - Leave blank for now
   - Click **"Create"**

7. **Copy the Alias ID** - you'll need it later
   - It looks like: `TSTALIASID` or similar

**✅ Part 2 Complete:** Your Lex bot is created and ready!

---

## Part 3: Deploy Lambda Functions (10-15 minutes)

Now we need to deploy the Lambda functions that will connect Lex to your Bedrock agents.

### Step 3.1: Package Lambda Functions

Open terminal and run:

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock

# Package lex-fulfillment Lambda
cd lambda/lex-fulfillment
zip -r deployment.zip handler.py
cd ../..

# Package voice-bedrock-bridge Lambda
cd lambda/voice-bedrock-bridge
zip -r deployment.zip handler.py
cd ../..
```

### Step 3.2: Deploy lex-fulfillment Lambda

1. Go to: https://console.aws.amazon.com/lambda/

2. Click **"Create function"**

3. **Function details:**
   - Function name: `pf-lex-fulfillment-dev`
   - Runtime: **Python 3.11**
   - Architecture: **x86_64**

4. **Permissions:**
   - Click **"Create a new role with basic Lambda permissions"**

5. Click **"Create function"**

6. **Upload code:**
   - In the **Code** tab, click **"Upload from"** → **".zip file"**
   - Click **"Upload"**
   - Select: `lambda/lex-fulfillment/deployment.zip`
   - Click **"Save"**

7. **Add environment variables:**
   - Click **"Configuration"** tab → **"Environment variables"**
   - Click **"Edit"** → **"Add environment variable"**
   - Add these:
     ```
     DYNAMODB_TABLE = pf-session-data-dev
     INFORMATION_LAMBDA = pf-information-actions
     VOICE_BRIDGE_LAMBDA = pf-voice-bedrock-bridge-dev
     AWS_REGION = us-east-1
     ```
   - Click **"Save"**

8. **Add permissions for DynamoDB and Lambda invocation:**
   - Click **"Configuration"** tab → **"Permissions"**
   - Click on the **Role name** (opens in new tab)
   - Click **"Add permissions"** → **"Attach policies"**
   - Search and attach:
     - `AmazonDynamoDBFullAccess`
     - `AWSLambda_FullAccess` (or create custom policy)
   - Return to Lambda tab

9. **Copy Lambda ARN** - you'll need it
   - At the top right: `arn:aws:lambda:us-east-1:618048437522:function:pf-lex-fulfillment-dev`

### Step 3.3: Deploy voice-bedrock-bridge Lambda

1. In Lambda console, click **"Create function"** again

2. **Function details:**
   - Function name: `pf-voice-bedrock-bridge-dev`
   - Runtime: **Python 3.11**

3. Click **"Create function"**

4. **Upload code:**
   - Upload: `lambda/voice-bedrock-bridge/deployment.zip`

5. **Add environment variables:**
   ```
   SUPERVISOR_AGENT_ID = P9VCJXPIZS
   SUPERVISOR_AGENT_ALIAS_ID = TSTALIASID
   DYNAMODB_TABLE = pf-session-data-dev
   AWS_REGION = us-east-1
   ```

6. **Add permissions:**
   - Attach policies:
     - `AmazonDynamoDBFullAccess`
     - Custom policy for Bedrock:
       ```json
       {
         "Version": "2012-10-17",
         "Statement": [
           {
             "Effect": "Allow",
             "Action": [
               "bedrock:InvokeAgent"
             ],
             "Resource": "*"
           }
         ]
       }
       ```

7. **Increase timeout:**
   - Configuration → General configuration → Edit
   - Timeout: **60 seconds**
   - Memory: **512 MB**
   - Click **"Save"**

**✅ Part 3 Complete:** Lambda functions are deployed!

---

## Part 4: Connect Lex to Lambda (5 minutes)

### Step 4.1: Add Lambda Permission for Lex

1. Go back to Lambda: `pf-lex-fulfillment-dev`

2. Click **"Configuration"** → **"Permissions"**

3. Scroll to **"Resource-based policy statements"**

4. Click **"Add permissions"**

5. **Create new statement:**
   - **Statement ID:** `AllowLexInvoke`
   - **Principal:** `lexv2.amazonaws.com`
   - **Source ARN:** `arn:aws:lex:us-east-1:618048437522:bot-alias/*`
   - **Action:** `lambda:InvokeFunction`
   - Click **"Save"**

### Step 4.2: Link Lambda to Lex Bot

1. Go back to Lex console: https://console.aws.amazon.com/lexv2/

2. Select your bot: `pf-scheduling-assistant`

3. Click **"Aliases"** in left sidebar

4. Click on **"prod"** alias

5. **Languages:**
   - Click **"English (US)"**

6. **Lambda function:**
   - Click **"Add"**
   - Select: `pf-lex-fulfillment-dev`
   - **Lambda function version or alias:** `$LATEST`
   - Click **"Save"**

7. Click **"Save"** again at the bottom

**✅ Part 4 Complete:** Lex is connected to Lambda!

---

## Part 5: Integrate Lex with AWS Connect (10 minutes)

### Step 5.1: Add Lex Bot to Connect

1. Go to AWS Connect console: https://console.aws.amazon.com/connect/

2. Click on your instance (e.g., `pf-voice-dev-2025`)

3. In the left sidebar, expand **"Contact flows"**

4. Click **"Amazon Lex"**

5. Click **"+ Add Lex bot"**

6. **Select your bot:**
   - **Bot:** `pf-scheduling-assistant`
   - **Alias:** `prod`

7. Click **"Add Amazon Lex Bot"**

8. You'll see it in the list with status: **Associated**

### Step 5.2: Create Contact Flow

1. In the left sidebar, click **"Contact flows"** (under Routing)

2. Click **"Create contact flow"**

3. **Flow name:** `pf-main-inbound`

4. **Build the flow:**

   **Block 1: Entry Point**
   - Already on the canvas

   **Block 2: Play Prompt (Greeting)**
   - From the left panel, drag **"Play prompt"** block onto canvas
   - Click the block to configure
   - **Select:** Text-to-speech
   - **Message:** `Thank you for calling ProjectForce. I'm your AI scheduling assistant.`
   - Click **"Save"**
   - Connect **Entry point** → **Play prompt**

   **Block 3: Get Customer Input (Lex)**
   - Drag **"Get customer input"** block onto canvas
   - Click to configure
   - **Select:** Amazon Lex
   - **Bot name:** `pf-scheduling-assistant`
   - **Alias:** `prod`
   - **Intents:** Click "Add an intent"
     - Add: `Welcome`
     - Add: `CheckProjects`
     - Add: `ScheduleAppointment`
     - Add: `WeatherInquiry`
     - Add: `FallbackIntent`
   - Click **"Save"**
   - Connect **Play prompt** → **Get customer input**

   **Block 4: Disconnect**
   - Drag **"Disconnect"** block onto canvas
   - Connect all outputs from **Get customer input** → **Disconnect**
     - Default
     - Error
     - Timeout

5. Click **"Save"** (top-right)

6. Click **"Publish"**

**✅ Contact Flow Created!**

### Step 5.3: Associate Phone Number with Contact Flow

1. In Connect console, click **"Phone numbers"** (under Channels)

2. Click on your phone number

3. Click **"Edit"**

4. **Contact flow / IVR:**
   - Select: `pf-main-inbound`

5. Click **"Save"**

**✅ Part 5 Complete:** Everything is connected!

---

## Part 6: Test Your Voice System (5 minutes)

### Step 6.1: Make Test Call

1. **Call your phone number** from your mobile phone

2. **Expected flow:**
   ```
   1. You hear: "Thank you for calling ProjectForce..."
   2. Say: "Hello"
   3. Bot responds: "Hello! Welcome to ProjectForce..."
   4. Say: "Show me my projects"
   5. Bot responds: "Let me check your projects..."
   ```

3. **If it works:** ✅ Success! Voice integration is live!

4. **If it doesn't work:** See troubleshooting below

### Step 6.2: Monitor Logs

**Lex Bot Logs:**
1. Lex Console → Your bot → Monitoring
2. See conversation history

**Lambda Logs:**
1. Lambda Console → pf-lex-fulfillment-dev → Monitor → View CloudWatch logs
2. Check for errors

**Connect Logs:**
1. Connect Console → Metrics and quality → Contact flow logs
2. See call flow execution

---

## Troubleshooting

### Issue: No audio when calling

**Solution:**
- Check contact flow is published (not draft)
- Verify phone number is associated with correct contact flow
- Check Connect instance has telephony enabled

### Issue: Bot doesn't respond

**Solution:**
- Verify Lex bot is built (green checkmark)
- Check Lambda permissions (Lex can invoke Lambda)
- Check Lambda has correct environment variables
- View CloudWatch logs for errors

### Issue: "I don't understand" message

**Solution:**
- Check your sample utterances in Lex
- Try exact phrases from sample utterances
- Lower confidence threshold in Lex (to 0.30)

### Issue: Lambda timeout

**Solution:**
- Increase Lambda timeout to 60 seconds
- Check Bedrock agent is prepared and accessible
- Verify DynamoDB table exists

---

## Summary - What You Created

✅ **AWS Connect instance** - Cloud contact center
✅ **Phone number** - 1-800 or local number
✅ **Lex bot** - Voice AI with 5 intents
✅ **2 Lambda functions** - Lex fulfillment + Bedrock bridge
✅ **Contact flow** - IVR call routing
✅ **Full integration** - Phone → Connect → Lex → Lambda → Bedrock

---

## Cost Estimate

For **100 calls/month** at 3 min average:

| Service | Cost |
|---------|------|
| Phone number | $2.00/month |
| Connect usage | $11.40 |
| Telephony | $0.66 |
| Lex requests | $0.08 |
| Lambda invocations | ~$0.00 |
| DynamoDB | ~$1.00 |
| **Total** | **~$15.14/month** |

(Plus Bedrock costs if you call agents)

---

## Next Steps

1. **Test thoroughly** - Call multiple times, try different intents

2. **Connect to Bedrock** - Ensure Lambda can invoke your Supervisor agent

3. **Add more intents** - Expand Lex bot capabilities

4. **Create contact flow variations** - Business hours, after-hours, etc.

5. **Enable call recording** - For quality and training

6. **Set up monitoring** - CloudWatch dashboards and alarms

---

## Quick Reference Commands

```bash
# Check if DynamoDB table exists
aws dynamodb describe-table --table-name pf-session-data-dev --region us-east-1

# Test Lambda function
aws lambda invoke \
  --function-name pf-lex-fulfillment-dev \
  --payload '{"sessionState":{"intent":{"name":"Welcome"}},"sessionId":"test"}' \
  /tmp/test-output.json

# View Lambda logs
aws logs tail /aws/lambda/pf-lex-fulfillment-dev --follow --region us-east-1

# List Bedrock agents
aws bedrock-agent list-agents --region us-east-1
```

---

**Congratulations!** 🎉 You now have a working AI voice assistant!

Call your number and talk to your Bedrock agents via phone.
