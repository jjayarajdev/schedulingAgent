# 🚀 Quick Start - Voice Integration

**Phone:** +1-833-877-1422 | **Deploy Time:** 15-20 min | **Resources:** 32

---

## Deploy in 3 Steps

### 1. Prerequisites (2 min)

```bash
cd /path/to/schedulingAgent-bb/bedrock

# Verify AWS access
aws sts get-caller-identity

# Check agents exist
cat config/agent_ids.json
```

### 2. Deploy (15-20 min)

```bash
./scripts/DEPLOY_VOICE_FULL.sh
```

Type `yes` when prompted.

### 3. Test (1 min)

```bash
# Call from your phone
📞 +1-833-877-1422

# Monitor logs
aws logs tail /aws/lambda/pf-lex-fulfillment-dev --follow
```

---

## What Gets Deployed

- ✅ AWS Connect instance (`pf-voice-dev`)
- ✅ Lex bot with 4 intents
- ✅ 2 Lambda functions
- ✅ S3 bucket (call recordings)
- ✅ DynamoDB table (sessions)
- ✅ IAM roles + KMS key
- **Total: 32 resources**

---

## Success Indicators

✅ Phone number answers in <3 seconds
✅ Lex bot responds to voice
✅ Lambda logs show invocations
✅ Bedrock routes to agents
✅ No errors in CloudWatch

---

## Cleanup (When Needed)

```bash
./scripts/CLEANUP_VOICE_FULL.sh
```

---

## Cost

**~$345/month** for 500 calls (3 min avg)
**~$0.69 per call**

---

## Documentation

📖 **Full Guide:** `docs/FINAL_DEPLOYMENT_READY.md`
📋 **Summary:** `DELIVERABLE_SUMMARY.md`
🔧 **Troubleshooting:** `docs/PROVIDER_COMPATIBILITY_ISSUES.md`

---

## Support

**Logs:** CloudWatch → `/aws/lambda/pf-lex-fulfillment-dev`
**Console:** https://pf-voice-dev.my.connect.aws
**Rollback:** `./scripts/CLEANUP_VOICE_FULL.sh`

---

**Status:** ✅ PRODUCTION READY | Terraform: 0 errors, 0 warnings
