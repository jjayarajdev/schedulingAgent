# Action Groups Quick Start

**⏱️ Time Required:** ~30 minutes (manual AWS Console work)

---

## What You Need

✅ Lambda functions deployed (already done!)
✅ OpenAPI schema files created (already done!)
❌ Action groups in AWS Console (need to create manually)

---

## Quick Steps

### 1. Get Lambda ARNs (Copy These)

```bash
aws lambda list-functions \
  --region us-east-1 \
  --query "Functions[?starts_with(FunctionName, 'scheduling-agent-')].{Name:FunctionName,ARN:FunctionArn}" \
  --output table
```

### 2. For Each Agent, Create Action Group

**Scheduling Agent (IX24FSMTQH):**
1. Open: https://console.aws.amazon.com/bedrock/home?region=us-east-1#/agents/IX24FSMTQH
2. Click "Add" in Action Groups section
3. Name: `scheduling-actions`
4. Schema: Inline editor → paste contents of `bedrock/lambda/schemas/scheduling-actions-schema.json`
5. Lambda: Select `scheduling-agent-scheduling-actions`
6. Click "Add"
7. **Click "Prepare" button** (top of page)

**Information Agent (C9ANXRIO8Y):**
1. Open: https://console.aws.amazon.com/bedrock/home?region=us-east-1#/agents/C9ANXRIO8Y
2. Click "Add" in Action Groups section
3. Name: `information-actions`
4. Schema: Inline editor → paste contents of `bedrock/lambda/schemas/information-actions-schema.json`
5. Lambda: Select `scheduling-agent-information-actions`
6. Click "Add"
7. **Click "Prepare" button** (top of page)

**Notes Agent (G5BVBYEPUM):**
1. Open: https://console.aws.amazon.com/bedrock/home?region=us-east-1#/agents/G5BVBYEPUM
2. Click "Add" in Action Groups section
3. Name: `notes-actions`
4. Schema: Inline editor → paste contents of `bedrock/lambda/schemas/notes-actions-schema.json`
5. Lambda: Select `scheduling-agent-notes-actions`
6. Click "Add"
7. **Click "Prepare" button** (top of page)

### 3. Test in Bedrock Console

1. Open Supervisor Agent
2. Click "Test" button
3. Try: "I want to schedule an appointment"
4. Should see agent invoke Lambda and return project list

---

## Schema Contents

### Scheduling Actions Schema
```bash
cat bedrock/lambda/schemas/scheduling-actions-schema.json
```

**6 Actions:**
- `/list-projects` - Show customer projects
- `/get-available-dates` - Get available dates
- `/get-time-slots` - Get time slots for a date
- `/confirm-appointment` - Schedule appointment
- `/reschedule-appointment` - Change appointment
- `/cancel-appointment` - Cancel appointment

### Information Actions Schema
```bash
cat bedrock/lambda/schemas/information-actions-schema.json
```

**4 Actions:**
- `/get-project-details` - Project info
- `/get-appointment-status` - Appointment status
- `/get-working-hours` - Business hours
- `/get-weather` - Weather forecast

### Notes Actions Schema
```bash
cat bedrock/lambda/schemas/notes-actions-schema.json
```

**2 Actions:**
- `/add-note` - Add note to project
- `/list-notes` - List project notes

---

## Troubleshooting

**Issue:** "Unable to invoke Lambda function"
**Fix:** Run the deployment script's permission step:
```bash
./bedrock/scripts/deploy_lambda_functions.sh  # Re-run (it will skip existing resources)
```

**Issue:** Agent doesn't use action group
**Fix:** Click "Prepare" button after adding action group (must rebuild agent)

**Issue:** Schema validation error
**Fix:** Copy schema exactly as-is (including all braces, commas, quotes)

---

## Full Documentation

For detailed instructions, see: [ACTION_GROUPS_SETUP_GUIDE.md](./ACTION_GROUPS_SETUP_GUIDE.md)

---

**Status:** Ready to create action groups manually ✅
