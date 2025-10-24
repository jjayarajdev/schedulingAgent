# Bedrock Multi-Agent System - Quick Reference

## 🚀 Common Commands

### Testing
```bash
# API access test
python3 tests/test_api_access.py

# Interactive testing
python3 tests/test_agents_interactive.py

# Basic test
python3 tests/test_agent.py
```

### Deployment
```bash
# Verify deployment
./scripts/verify_deployment.sh

# Prepare all agents
python3 utils/prepare_all_agents.py

# Gather diagnostics
./scripts/gather_diagnostics.sh
```

### Terraform
```bash
cd infrastructure/terraform

# Plan changes
terraform plan

# Apply changes
terraform apply

# Show current state
terraform show
```

---

## 🤖 Agent IDs

### Supervisor
- **ID**: `5VTIWONUMO`
- **Latest Alias**: `HH2U7EZXMW` (version 6)
- **Test Alias**: `TSTALIASID` (DRAFT)

### Collaborators
| Agent | ID | v4 Alias |
|-------|-----|----------|
| Chitchat | `BIUW1ARHGL` | `THIPMPJCPI` |
| Scheduling | `IX24FSMTQH` | `TYJRF3CJ7F` |
| Information | `C9ANXRIO8Y` | `YVNFXEKPWO` |
| Notes | `G5BVBYEPUM` | `F9QQNLZUW8` |

---

## 📂 File Locations

```
bedrock/
├── tests/          # Test scripts
├── utils/          # Utility scripts
├── scripts/        # Shell scripts
├── docs/           # Documentation
└── infrastructure/ # Terraform
```

### Key Files
- **Main README**: `bedrock/README.md`
- **Testing Guide**: `docs/TESTING_GUIDE.md`
- **API Access Guide**: `docs/ENABLE_API_ACCESS.md`
- **Support Ticket**: `docs/AWS_SUPPORT_TICKET.md`

---

## 🧪 Test Scenarios

```bash
# In interactive mode:
python3 tests/test_agents_interactive.py

# Try these:
Hello! How are you?                           # → Chitchat
I want to schedule an appointment             # → Scheduling
What are your working hours?                  # → Information
Add a note that I prefer morning appointments # → Notes
```

---

## 🌐 AWS Console Links

### Bedrock Agents
```
https://console.aws.amazon.com/bedrock/home?region=us-east-1#/agents
```

### Model Access
```
https://console.aws.amazon.com/bedrock/home?region=us-east-1#/modelaccess
```

### CloudWatch Logs
```
https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#logsV2:log-groups
```

---

## 🔍 Troubleshooting

### Check Agent Status
```bash
aws bedrock-agent get-agent --agent-id 5VTIWONUMO --region us-east-1
```

### Check Model
```bash
aws bedrock list-foundation-models --region us-east-1 --by-provider anthropic
```

### Test Model Access
```bash
aws bedrock-runtime invoke-model \
  --model-id us.anthropic.claude-sonnet-4-5-20250929-v1:0 \
  --region us-east-1 \
  --body '{"anthropic_version":"bedrock-2023-05-31","max_tokens":20,"messages":[{"role":"user","content":"Hi"}]}' \
  /tmp/response.json
```

### Check IAM Role
```bash
aws iam get-role-policy \
  --role-name scheduling-agent-supervisor-agent-role-dev \
  --policy-name scheduling-agent-supervisor-agent-policy
```

---

## 📊 Status Checks

### Quick Health Check
```bash
./scripts/verify_deployment.sh && \
python3 tests/test_api_access.py
```

### Full Diagnostic
```bash
./scripts/gather_diagnostics.sh
cat /tmp/bedrock_diagnostics_*/0_SUMMARY.txt
```

---

## 🆘 Common Errors

### Error 403: Access Denied
**Fix**: See `docs/ENABLE_API_ACCESS.md`

### Agent Not Prepared
**Fix**: `python3 utils/prepare_all_agents.py`

### Model Not Found
**Fix**: Check model ID in Terraform `terraform.tfvars`

### Collaborators Not Associated
**Fix**: Re-run `terraform apply`

---

## 📞 Getting Help

1. **Check Documentation**: `docs/DOCUMENTATION_INDEX.md`
2. **Run Diagnostics**: `./scripts/gather_diagnostics.sh`
3. **Submit Support Ticket**: Use `docs/AWS_SUPPORT_TICKET.md`

---

## 🔄 Workflow

### Daily Development
```bash
# 1. Make changes
# 2. Apply Terraform
terraform apply

# 3. Prepare agents
python3 utils/prepare_all_agents.py

# 4. Test
python3 tests/test_agents_interactive.py
```

### Before Deployment
```bash
./scripts/verify_deployment.sh
python3 tests/test_api_access.py
./scripts/gather_diagnostics.sh  # Save for records
```

---

## 💾 Backup Commands

### Export Agent Config
```bash
aws bedrock-agent get-agent \
  --agent-id 5VTIWONUMO \
  --region us-east-1 > agent_backup.json
```

### Export Terraform State
```bash
cd infrastructure/terraform
terraform state pull > terraform_state_backup.json
```

---

**Region**: us-east-1
**Model**: Claude Sonnet 4.5 (`us.anthropic.claude-sonnet-4-5-20250929-v1:0`)
**Last Updated**: October 13, 2025
