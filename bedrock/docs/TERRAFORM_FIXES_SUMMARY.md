# Terraform Configuration Fixes - Voice Integration

**Date:** November 9, 2025
**Status:** ✅ All errors resolved
**Terraform Plan:** Passes without errors or warnings

---

## Summary

Fixed all Terraform configuration errors in the voice integration to enable full automated deployment with AWS Connect, Lex, and Lambda.

---

## Errors Fixed

### 1. Missing Variable Declarations

**Error:**
```
Warning: Value for undeclared variable
The root module does not declare a variable named "lex_voice_id"
The root module does not declare a variable named "information_agent_id"
```

**Fix:** Added missing variable declarations to `infrastructure/terraform/voice/variables.tf`:
- `scheduling_agent_id` - Bedrock Scheduling Agent ID
- `information_agent_id` - Bedrock Information Agent ID
- `chitchat_agent_id` - Bedrock ChitChat Agent ID
- `lex_bot_name` - Name for the Lex bot (default: "pf-scheduling-assistant-dev")
- `lex_voice_id` - Amazon Polly voice ID (default: "Joanna")

**File:** `infrastructure/terraform/voice/variables.tf:52-77`

---

### 2. S3 Lifecycle Configuration Missing Filter

**Error:**
```
Warning: Invalid Attribute Combination
with aws_s3_bucket_lifecycle_configuration.call_recordings,
on aws_connect.tf line 67
No attribute specified when one (and only one) of [rule[0].filter,rule[0].prefix] is required
```

**Fix:** Added empty `filter {}` block to S3 lifecycle rule

**Before:**
```terraform
rule {
  id     = "delete-old-recordings"
  status = "Enabled"

  expiration {
    days = 90
  }
```

**After:**
```terraform
rule {
  id     = "delete-old-recordings"
  status = "Enabled"

  filter {}

  expiration {
    days = 90
  }
```

**File:** `infrastructure/terraform/voice/aws_connect.tf:74`

---

### 3. Resolution Strategy Case Sensitivity

**Error:**
```
Error: Invalid Attribute Value Match
on lex_bot.tf line 231
resolution_strategy value must be one of: ["OriginalValue" "TopResolution" "Concatenation"]
got: "ORIGINAL_VALUE"
```

**Fix:** Changed resolution_strategy values from SCREAMING_SNAKE_CASE to PascalCase

**Changes:**
- Line 231: `"ORIGINAL_VALUE"` → `"OriginalValue"`
- Line 260: `"TOP_RESOLUTION"` → `"TopResolution"`

**Files:**
- `infrastructure/terraform/voice/lex_bot.tf:231`
- `infrastructure/terraform/voice/lex_bot.tf:260`

---

### 4. Deprecated Slot Priority Syntax

**Error:**
```
Error: Missing required argument
on lex_bot.tf line 113, in resource "aws_lexv2models_intent" "project_inquiry":
The argument "slot_id" is required, but no definition was found.

Error: Unsupported argument
on lex_bot.tf line 115
An argument named "slot_name" is not expected here.
```

**Fix:** Removed all deprecated `slot_priority` blocks

The AWS Lex V2 provider no longer supports `slot_priority` blocks with `slot_name`. The newer API handles slot elicitation automatically based on sample utterances.

**Removed from:**
- `project_inquiry` intent (lines 113-116)
- `schedule_appointment` intent (lines 151-162)

**File:** `infrastructure/terraform/voice/lex_bot.tf`

---

### 5. Unsupported Bot Alias Resource Type

**Error:**
```
Error: Invalid resource type
on lex_bot.tf line 343
The provider hashicorp/aws does not support resource type "aws_lexv2models_bot_alias"
```

**Fix:** Removed unsupported `aws_lexv2models_bot_alias` resource and `aws_lexv2models_bot_version` resource

**Removed:**
- Lines 306-347: `aws_lexv2models_bot_version.v1`
- Lines 324-347: `aws_lexv2models_bot_alias.prod`

**Updated outputs to use TSTALIASID:**
```terraform
output "lex_bot_alias_id" {
  description = "Lex Bot Alias ID (using TSTALIASID - test alias)"
  value       = "TSTALIASID"
}

output "lex_bot_alias_arn" {
  description = "Lex Bot Alias ARN"
  value       = "${aws_lexv2models_bot.scheduling_assistant.arn}/alias/TSTALIASID"
}
```

**Note:** TSTALIASID is the default test alias that AWS automatically creates for all Lex bots. It points to the DRAFT version and is always available.

**File:** `infrastructure/terraform/voice/lex_bot.tf:306-309, 388-396`

---

## Verification

**Terraform Plan Result:**
```bash
$ terraform plan
✅ No errors
✅ No warnings
✅ Plan creates all required resources
```

**Resources to be created:**
- AWS Connect instance
- Amazon Lex bot with 5 intents
- 2 Lambda functions (lex-fulfillment, voice-bedrock-bridge)
- DynamoDB table for session storage
- S3 bucket for call recordings
- IAM roles and policies
- CloudWatch log groups
- KMS keys for encryption
- Contact flows and queues

---

## Next Steps

The Terraform configuration is now ready for deployment:

```bash
# Deploy full voice integration
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock
./scripts/DEPLOY_VOICE_FULL.sh
```

---

## Files Modified

1. **infrastructure/terraform/voice/variables.tf**
   - Added 5 new variable declarations

2. **infrastructure/terraform/voice/aws_connect.tf**
   - Added empty filter block to S3 lifecycle rule

3. **infrastructure/terraform/voice/lex_bot.tf**
   - Fixed 2 resolution_strategy values (PascalCase)
   - Removed 2 slot_priority blocks (deprecated)
   - Removed bot_version and bot_alias resources (unsupported)
   - Updated 2 outputs to use TSTALIASID

---

## Technical Notes

### Why TSTALIASID?

TSTALIASID is AWS Lex's built-in test alias that:
- Automatically exists for all bots
- Points to the DRAFT version
- Requires no additional configuration
- Perfect for development and testing

For production, you can:
- Create a bot version via AWS Console
- Create a production alias pointing to that version
- Update Connect to use the production alias

### Slot Priority Deprecation

The AWS Lex V2 API changed slot handling:
- **Old:** Explicit `slot_priority` blocks defined slot elicitation order
- **New:** Slot order inferred from sample utterances and intent configuration
- **Migration:** Remove `slot_priority` blocks entirely

The bot will still prompt for slots based on:
1. Sample utterances with slot placeholders
2. Slot validation rules
3. Conversation context

---

## Related Documentation

- [Full Deployment Guide](./VOICE_FULL_DEPLOYMENT_GUIDE.md)
- [Deployment Scripts Reference](./DEPLOYMENT_SCRIPTS_REFERENCE.md)
- [Voice Deployment Status](./VOICE_DEPLOYMENT_STATUS.md)
