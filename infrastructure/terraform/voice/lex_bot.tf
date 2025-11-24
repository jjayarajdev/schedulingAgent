# ============================================================================
# Amazon Lex V2 Bot for Voice Integration (Phase 3)
# ============================================================================

# ============================================================================
# Lex Bot
# ============================================================================

resource "aws_lexv2models_bot" "scheduling_assistant" {
  name                        = "${var.prefix}-scheduling-assistant-${var.environment}"
  description                 = "AI Voice Assistant for Project Scheduling"
  role_arn                    = aws_iam_role.lex_bot.arn
  data_privacy {
    child_directed = false
  }
  idle_session_ttl_in_seconds = 600  # 10 minutes

  tags = {
    Name        = "${var.prefix}-lex-bot-${var.environment}"
    Environment = var.environment
    Phase       = "3"
  }
}

# ============================================================================
# Bot Locale (English US)
# ============================================================================

resource "aws_lexv2models_bot_locale" "en_us" {
  bot_id      = aws_lexv2models_bot.scheduling_assistant.id
  bot_version = "DRAFT"
  locale_id   = "en_US"

  description           = "English US locale for scheduling assistant"
  n_lu_intent_confidence_threshold = 0.70

  voice_settings {
    voice_id = "Joanna"  # Professional female voice
    engine   = "neural"  # Better quality than standard
  }
}

# ============================================================================
# Intents
# ============================================================================

# 1. Welcome Intent
resource "aws_lexv2models_intent" "welcome" {
  bot_id      = aws_lexv2models_bot.scheduling_assistant.id
  bot_version = "DRAFT"
  locale_id   = aws_lexv2models_bot_locale.en_us.locale_id

  name        = "Welcome"
  description = "Greeting and help intent"

  sample_utterance {
    utterance = "hello"
  }
  sample_utterance {
    utterance = "hi"
  }
  sample_utterance {
    utterance = "help"
  }
  sample_utterance {
    utterance = "what can you do"
  }
  sample_utterance {
    utterance = "how does this work"
  }

  fulfillment_code_hook {
    enabled = true
  }
}

# 2. Project Inquiry Intent
resource "aws_lexv2models_intent" "project_inquiry" {
  bot_id      = aws_lexv2models_bot.scheduling_assistant.id
  bot_version = "DRAFT"
  locale_id   = aws_lexv2models_bot_locale.en_us.locale_id

  name        = "ProjectInquiry"
  description = "Query project status and details"

  # Sample utterances
  sample_utterance {
    utterance = "show me my projects"
  }
  sample_utterance {
    utterance = "list my projects"
  }
  sample_utterance {
    utterance = "what projects do I have"
  }
  sample_utterance {
    utterance = "do I have any projects"
  }
  sample_utterance {
    utterance = "what's the status of project {ProjectID}"
  }
  sample_utterance {
    utterance = "tell me about project {ProjectID}"
  }
  sample_utterance {
    utterance = "show me pending projects"
  }
  sample_utterance {
    utterance = "list scheduled projects"
  }

  fulfillment_code_hook {
    enabled = true
  }
}

# 3. Schedule Appointment Intent
resource "aws_lexv2models_intent" "schedule_appointment" {
  bot_id      = aws_lexv2models_bot.scheduling_assistant.id
  bot_version = "DRAFT"
  locale_id   = aws_lexv2models_bot_locale.en_us.locale_id

  name        = "ScheduleAppointment"
  description = "Schedule a project appointment"

  sample_utterance {
    utterance = "schedule an appointment"
  }
  sample_utterance {
    utterance = "I need to schedule project {ProjectID}"
  }
  sample_utterance {
    utterance = "book an appointment for {ProjectCategory}"
  }
  sample_utterance {
    utterance = "schedule my {ProjectCategory} project"
  }
  sample_utterance {
    utterance = "I want to book on {AppointmentDate}"
  }
  sample_utterance {
    utterance = "schedule for {AppointmentDate} at {AppointmentTime}"
  }

  fulfillment_code_hook {
    enabled = true
  }
}

# 4. Urgent Request Intent
resource "aws_lexv2models_intent" "urgent_request" {
  bot_id      = aws_lexv2models_bot.scheduling_assistant.id
  bot_version = "DRAFT"
  locale_id   = aws_lexv2models_bot_locale.en_us.locale_id

  name        = "UrgentRequest"
  description = "Handle urgent scheduling requests"

  sample_utterance {
    utterance = "I need urgent scheduling"
  }
  sample_utterance {
    utterance = "schedule my most urgent project"
  }
  sample_utterance {
    utterance = "what's my highest priority project"
  }
  sample_utterance {
    utterance = "I need immediate service"
  }
  sample_utterance {
    utterance = "this is urgent"
  }
  sample_utterance {
    utterance = "schedule my urgent project"
  }

  fulfillment_code_hook {
    enabled = true
  }
}

# 5. Fallback Intent - Use built-in AMAZON.FallbackIntent
# Note: FallbackIntent is automatically created by Lex and cannot be managed via Terraform
# The built-in AMAZON.FallbackIntent will automatically invoke the Lambda fulfillment function

# ============================================================================
# Slot Types
# ============================================================================

resource "aws_lexv2models_slot_type" "project_id" {
  bot_id      = aws_lexv2models_bot.scheduling_assistant.id
  bot_version = "DRAFT"
  locale_id   = aws_lexv2models_bot_locale.en_us.locale_id

  name        = "ProjectID"
  description = "Project identifier"

  value_selection_setting {
    resolution_strategy = "OriginalValue"
  }

  slot_type_values {
    sample_value {
      value = "PROJ-001"
    }
  }
  slot_type_values {
    sample_value {
      value = "PROJ-002"
    }
  }
  slot_type_values {
    sample_value {
      value = "12345"
    }
  }
}

resource "aws_lexv2models_slot_type" "project_category" {
  bot_id      = aws_lexv2models_bot.scheduling_assistant.id
  bot_version = "DRAFT"
  locale_id   = aws_lexv2models_bot_locale.en_us.locale_id

  name        = "ProjectCategory"
  description = "Type of project"

  value_selection_setting {
    resolution_strategy = "TopResolution"
  }

  slot_type_values {
    sample_value {
      value = "roofing"
    }
    synonyms {
      value = "roof"
    }
    synonyms {
      value = "roof installation"
    }
  }

  slot_type_values {
    sample_value {
      value = "painting"
    }
    synonyms {
      value = "paint"
    }
  }

  slot_type_values {
    sample_value {
      value = "flooring"
    }
    synonyms {
      value = "floor"
    }
    synonyms {
      value = "floor installation"
    }
  }

  slot_type_values {
    sample_value {
      value = "deck"
    }
    synonyms {
      value = "deck installation"
    }
    synonyms {
      value = "decking"
    }
  }

  slot_type_values {
    sample_value {
      value = "electrical"
    }
  }

  slot_type_values {
    sample_value {
      value = "plumbing"
    }
  }
}

# ============================================================================
# Bot Alias
# ============================================================================

# Note: Bot alias creation via Terraform is not supported in current AWS provider
# Use TSTALIASID (test alias) which is automatically available for all bots
# Or create alias manually via AWS Console after deployment

# ============================================================================
# IAM Role for Lex Bot
# ============================================================================

resource "aws_iam_role" "lex_bot" {
  name = "${var.prefix}-lex-bot-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lexv2.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.prefix}-lex-bot-role-${var.environment}"
  }
}

resource "aws_iam_role_policy" "lex_bot_policy" {
  name = "${var.prefix}-lex-bot-policy-${var.environment}"
  role = aws_iam_role.lex_bot.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "polly:SynthesizeSpeech"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lex/*"
      }
    ]
  })
}

# ============================================================================
# Lambda Permission for Lex
# ============================================================================

resource "aws_lambda_permission" "lex_fulfillment" {
  statement_id  = "AllowExecutionFromLex"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.lex_fulfillment.function_name
  principal     = "lexv2.amazonaws.com"
  source_arn    = "${aws_lexv2models_bot.scheduling_assistant.arn}/*"
}

# ============================================================================
# Outputs
# ============================================================================

output "lex_bot_id" {
  description = "Lex Bot ID"
  value       = aws_lexv2models_bot.scheduling_assistant.id
}

output "lex_bot_arn" {
  description = "Lex Bot ARN"
  value       = aws_lexv2models_bot.scheduling_assistant.arn
}

output "lex_bot_alias_id" {
  description = "Lex Bot Alias ID (using TSTALIASID - test alias)"
  value       = "TSTALIASID"
}

output "lex_bot_alias_arn" {
  description = "Lex Bot Alias ARN"
  value       = "${aws_lexv2models_bot.scheduling_assistant.arn}/alias/TSTALIASID"
}
