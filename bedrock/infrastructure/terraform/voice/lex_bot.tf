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

  # Slot for optional project ID
  slot_priority {
    priority  = 1
    slot_name = "ProjectID"
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

  slot_priority {
    priority  = 1
    slot_name = "ProjectID"
  }
  slot_priority {
    priority  = 2
    slot_name = "AppointmentDate"
  }
  slot_priority {
    priority  = 3
    slot_name = "AppointmentTime"
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

# 5. Fallback Intent (hand off to Bedrock)
resource "aws_lexv2models_intent" "fallback" {
  bot_id      = aws_lexv2models_bot.scheduling_assistant.id
  bot_version = "DRAFT"
  locale_id   = aws_lexv2models_bot_locale.en_us.locale_id

  name        = "FallbackIntent"
  description = "Fallback to Bedrock for complex queries"

  parent_intent_signature = "AMAZON.FallbackIntent"

  fulfillment_code_hook {
    enabled = true
  }
}

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
    resolution_strategy = "ORIGINAL_VALUE"
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
    resolution_strategy = "TOP_RESOLUTION"
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

resource "aws_lexv2models_bot_version" "v1" {
  bot_id = aws_lexv2models_bot.scheduling_assistant.id

  locale_specification = {
    (aws_lexv2models_bot_locale.en_us.locale_id) = {
      source_bot_version = "DRAFT"
    }
  }

  depends_on = [
    aws_lexv2models_intent.welcome,
    aws_lexv2models_intent.project_inquiry,
    aws_lexv2models_intent.schedule_appointment,
    aws_lexv2models_intent.urgent_request,
    aws_lexv2models_intent.fallback
  ]
}

resource "aws_lexv2models_bot_alias" "prod" {
  bot_id  = aws_lexv2models_bot.scheduling_assistant.id
  name    = "prod"
  bot_version = aws_lexv2models_bot_version.v1.bot_version

  bot_alias_locale_settings {
    locale_id = aws_lexv2models_bot_locale.en_us.locale_id

    bot_alias_locale_setting {
      enabled = true
      code_hook_specification {
        lambda_code_hook {
          lambda_arn                = aws_lambda_function.lex_fulfillment.arn
          code_hook_interface_version = "1.0"
        }
      }
    }
  }

  tags = {
    Name        = "${var.prefix}-lex-alias-prod-${var.environment}"
    Environment = var.environment
  }
}

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
  description = "Lex Bot Alias ID"
  value       = aws_lexv2models_bot_alias.prod.id
}

output "lex_bot_alias_arn" {
  description = "Lex Bot Alias ARN"
  value       = aws_lexv2models_bot_alias.prod.bot_alias_arn
}
