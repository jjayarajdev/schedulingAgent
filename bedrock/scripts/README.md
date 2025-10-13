# Bedrock Agent Scripts

Shell scripts for deployment verification and diagnostics.

## Scripts

### 1. `gather_diagnostics.sh`
**Purpose**: Collect diagnostic information for AWS Support tickets

Gathers comprehensive information about:
- API access test results
- Agent configurations (supervisor + collaborators)
- IAM policies
- Inference profiles
- Account details

**Usage:**
```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock
./scripts/gather_diagnostics.sh
```

**Output:**
Creates a timestamped directory in `/tmp/` with diagnostic files:

```
/tmp/bedrock_diagnostics_20251013_120000/
├── 0_SUMMARY.txt                      # Overview of the issue
├── 1_api_test_results.txt            # Test output showing errors
├── 2_supervisor_agent_config.json    # Supervisor agent configuration
├── 3_supervisor_version6_config.json # Version 6 details
├── 4_supervisor_iam_policy.json      # IAM role policy
├── 5_collaborator_agents.txt         # Collaborator agent details
├── 6_direct_model_test.txt           # Direct model invocation test
├── 7_inference_profiles.json         # Available inference profiles
└── 8_account_info.json               # AWS account information
```

**When to use:**
- Before submitting AWS Support ticket
- Troubleshooting 403 Access Denied errors
- Documenting configuration for team review
- Capturing state before making changes

**Attaching to Support Ticket:**
```bash
# Zip the diagnostics
cd /tmp
zip -r bedrock_diagnostics.zip bedrock_diagnostics_20251013_120000/

# Attach to support ticket:
# - Most important: 0_SUMMARY.txt, 1_api_test_results.txt, 4_supervisor_iam_policy.json
# - Or attach entire zip file
```

---

### 2. `verify_deployment.sh`
**Purpose**: Verify Bedrock agent deployment status

Quick validation script that checks:
- Agent existence and status
- Agent preparation state
- Foundation model configuration
- Basic connectivity

**Usage:**
```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock
./scripts/verify_deployment.sh
```

**Expected Output:**
```
Verifying Bedrock Agent Deployment
==================================

Checking Supervisor Agent...
✓ Agent exists
✓ Agent status: PREPARED
✓ Foundation model: us.anthropic.claude-sonnet-4-5-20250929-v1:0

Checking Collaborator Agents...
✓ Chitchat agent exists
✓ Scheduling agent exists
✓ Information agent exists
✓ Notes agent exists

✅ All agents deployed successfully!
```

**When to use:**
- After running `terraform apply`
- After updating agent configurations
- Before running tests
- As part of CI/CD pipeline
- Quick health check

---

## Common Workflows

### After Initial Deployment
```bash
# 1. Verify deployment
./scripts/verify_deployment.sh

# 2. Prepare agents
python3 utils/prepare_all_agents.py

# 3. Run tests
python3 tests/test_agents_interactive.py
```

### Troubleshooting API Issues
```bash
# 1. Gather diagnostics
./scripts/gather_diagnostics.sh

# 2. Review summary
cat /tmp/bedrock_diagnostics_*/0_SUMMARY.txt

# 3. Check test results
cat /tmp/bedrock_diagnostics_*/1_api_test_results.txt

# 4. Submit to AWS Support (see docs/AWS_SUPPORT_TICKET.md)
```

### Pre-Production Validation
```bash
# Complete validation checklist
./scripts/verify_deployment.sh
python3 utils/prepare_all_agents.py
python3 tests/test_api_access.py

# If all pass, ready for production
```

---

## Script Details

### gather_diagnostics.sh

**Dependencies:**
- AWS CLI configured
- Python 3 with boto3
- Test scripts in tests/ directory

**Files Created:**
| File | Content | Purpose |
|------|---------|---------|
| 0_SUMMARY.txt | Issue overview | Quick reference for support |
| 1_api_test_results.txt | Test output | Shows exact errors |
| 2_supervisor_agent_config.json | Agent config | Current configuration |
| 3_supervisor_version6_config.json | Version details | Latest version info |
| 4_supervisor_iam_policy.json | IAM policy | Permission verification |
| 5_collaborator_agents.txt | Collaborators | All agent IDs and aliases |
| 6_direct_model_test.txt | Model test | Proves model access works |
| 7_inference_profiles.json | Profiles | Available profiles |
| 8_account_info.json | Account info | Account ID and user |

**Time to run:** ~30 seconds

---

### verify_deployment.sh

**Checks Performed:**
1. AWS CLI connectivity
2. Bedrock service availability
3. Agent existence (supervisor + 4 collaborators)
4. Agent status (PREPARED vs NOT_PREPARED)
5. Model configuration
6. Basic permissions

**Exit Codes:**
- `0` - All checks passed
- `1` - One or more checks failed

**Time to run:** ~10 seconds

---

## Customization

### Adding Custom Diagnostics

Edit `gather_diagnostics.sh` and add:

```bash
# 9. Your custom diagnostic
echo "[9/9] Running custom check..."
your-command > "$OUTPUT_DIR/9_custom_check.txt" 2>&1
```

### Adding Deployment Checks

Edit `verify_deployment.sh` and add:

```bash
echo "Checking custom component..."
aws your-service describe-resource --resource-id XXX
```

---

## Troubleshooting Scripts

### gather_diagnostics.sh issues

**Error: Command not found**
```bash
# Install AWS CLI
brew install awscli  # macOS
# or
pip install awscli  # Any OS
```

**Error: Permission denied**
```bash
chmod +x scripts/gather_diagnostics.sh
```

**Error: boto3 not found**
```bash
pip install boto3
```

### verify_deployment.sh issues

**Error: Agent not found**
- Check agent IDs in script match your deployment
- Verify you're in correct AWS region (us-east-1)
- Run `aws bedrock-agent list-agents --region us-east-1`

---

## Best Practices

1. **Run verify_deployment.sh after every deployment**
2. **Gather diagnostics before filing support tickets**
3. **Keep diagnostic outputs for historical reference**
4. **Review 0_SUMMARY.txt before sharing diagnostics**
5. **Update scripts when agent IDs or aliases change**

---

## Related Documentation

- **Deployment Guide**: `docs/DEPLOYMENT_GUIDE.md`
- **Testing Guide**: `docs/TESTING_GUIDE.md`
- **AWS Support Ticket Template**: `docs/AWS_SUPPORT_TICKET.md`
- **API Access Guide**: `docs/ENABLE_API_ACCESS.md`

---

**Last Updated**: October 13, 2025
