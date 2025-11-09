# How to Claim a Phone Number for AWS Connect

**Date:** November 9, 2025
**Task:** Claim a phone number for incoming calls to AWS Connect

---

## Prerequisites

Before claiming a number, you need:

1. ✅ AWS Connect instance deployed (or create one first)
2. ✅ AWS account with appropriate permissions
3. ✅ Decision: Toll-Free (1-800) vs DID (local number)

---

## Method 1: AWS Console (Easiest - 5 minutes)

### Step 1: Check if Connect Instance Exists

First, let's see if you already have a Connect instance:

```bash
aws connect list-instances --region us-east-1
```

**If you see instances listed**, note the Instance ID and ARN.

**If no instances exist**, you need to create one first (see section below).

### Step 2: Open AWS Connect Console

1. Go to AWS Connect Console: https://console.aws.amazon.com/connect/
2. Select region: **US East (N. Virginia) us-east-1**
3. You should see your Connect instance (or need to create one)

### Step 3: Claim a Phone Number

**Option A: If Connect Instance Exists**

1. Click on your instance name (e.g., `pf-voice-dev`)
2. In the left navigation, click **Channels → Phone numbers**
3. Click the **Claim a number** button
4. Choose your preferences:
   - **Country:** United States
   - **Type:**
     - **Toll-Free** (recommended for business - customers don't pay)
     - **DID** (Direct Inbound Dial - local area code number)
5. Select a number from the list shown
6. Click **Claim number**
7. The number is now yours!

**Option B: If No Connect Instance Exists Yet**

1. In AWS Connect Console, click **Create instance**
2. Choose **Identity management:** Connect managed
3. Enter **Instance alias:** `pf-voice-dev` (must be globally unique)
4. Create admin user (optional for now)
5. Complete instance creation (takes 2-3 minutes)
6. Then follow Option A above to claim number

### Step 4: Note Your Phone Number

After claiming, you'll see the number in format: **+1-800-XXX-XXXX**

Save this number - you'll need it for:
- Testing
- Updating Terraform variables
- Giving to customers

---

## Method 2: AWS CLI (For Automation)

### Step 1: Get Your Connect Instance ID

```bash
# List all Connect instances
aws connect list-instances --region us-east-1

# Save the Instance ARN
INSTANCE_ARN="arn:aws:connect:us-east-1:618048437522:instance/XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"
```

### Step 2: Search for Available Numbers

**For Toll-Free Numbers:**

```bash
aws connect search-available-phone-numbers \
  --target-arn "$INSTANCE_ARN" \
  --phone-number-country-code "US" \
  --phone-number-type "TOLL_FREE" \
  --max-results 10 \
  --region us-east-1
```

**For DID (Local) Numbers:**

```bash
# Search by area code (e.g., 813 for Tampa)
aws connect search-available-phone-numbers \
  --target-arn "$INSTANCE_ARN" \
  --phone-number-country-code "US" \
  --phone-number-type "DID" \
  --phone-number-prefix "813" \
  --max-results 10 \
  --region us-east-1
```

**Example Output:**

```json
{
    "AvailableNumbersList": [
        {
            "PhoneNumber": "+18005551234",
            "PhoneNumberCountryCode": "US",
            "PhoneNumberType": "TOLL_FREE"
        },
        {
            "PhoneNumber": "+18005555678",
            "PhoneNumberCountryCode": "US",
            "PhoneNumberType": "TOLL_FREE"
        }
    ]
}
```

### Step 3: Claim the Number

```bash
# Choose a number from the list and claim it
aws connect claim-phone-number \
  --target-arn "$INSTANCE_ARN" \
  --phone-number "+18005551234" \
  --phone-number-description "Main inbound line for ProjectForce" \
  --region us-east-1
```

**Success Response:**

```json
{
    "PhoneNumberId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    "PhoneNumberArn": "arn:aws:connect:us-east-1:618048437522:phone-number/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
}
```

### Step 4: Verify the Number is Claimed

```bash
# List all phone numbers for your instance
aws connect list-phone-numbers-v2 \
  --target-arn "$INSTANCE_ARN" \
  --region us-east-1
```

---

## Quick Script: Claim Number Automatically

Save this as: `/Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/scripts/claim_phone_number.sh`

```bash
#!/bin/bash
set -e

echo "=== AWS Connect Phone Number Claim Tool ==="
echo ""

# Get Connect instance
echo "Fetching Connect instance..."
INSTANCE_ARN=$(aws connect list-instances \
  --region us-east-1 \
  --query 'InstanceSummaryList[0].Arn' \
  --output text)

if [ -z "$INSTANCE_ARN" ] || [ "$INSTANCE_ARN" == "None" ]; then
  echo "❌ No Connect instance found!"
  echo "Create instance first: https://console.aws.amazon.com/connect/"
  exit 1
fi

echo "✅ Found instance: $INSTANCE_ARN"
echo ""

# Ask user for number type
echo "What type of number do you want?"
echo "1) Toll-Free (1-800 number - recommended)"
echo "2) DID (Local area code number)"
read -p "Enter choice (1 or 2): " CHOICE

if [ "$CHOICE" == "1" ]; then
  NUMBER_TYPE="TOLL_FREE"
  echo ""
  echo "Searching for available toll-free numbers..."

  aws connect search-available-phone-numbers \
    --target-arn "$INSTANCE_ARN" \
    --phone-number-country-code "US" \
    --phone-number-type "TOLL_FREE" \
    --max-results 10 \
    --region us-east-1 \
    --query 'AvailableNumbersList[*].PhoneNumber' \
    --output table

elif [ "$CHOICE" == "2" ]; then
  NUMBER_TYPE="DID"
  read -p "Enter area code (e.g., 813 for Tampa): " AREA_CODE
  echo ""
  echo "Searching for available numbers in area code $AREA_CODE..."

  aws connect search-available-phone-numbers \
    --target-arn "$INSTANCE_ARN" \
    --phone-number-country-code "US" \
    --phone-number-type "DID" \
    --phone-number-prefix "$AREA_CODE" \
    --max-results 10 \
    --region us-east-1 \
    --query 'AvailableNumbersList[*].PhoneNumber' \
    --output table
else
  echo "Invalid choice!"
  exit 1
fi

echo ""
read -p "Enter the phone number you want to claim (format: +18005551234): " PHONE_NUMBER

echo ""
echo "Claiming $PHONE_NUMBER..."

aws connect claim-phone-number \
  --target-arn "$INSTANCE_ARN" \
  --phone-number "$PHONE_NUMBER" \
  --phone-number-description "ProjectForce main inbound line" \
  --region us-east-1

echo ""
echo "✅ Success! Phone number claimed: $PHONE_NUMBER"
echo ""
echo "Next steps:"
echo "1. Update terraform.tfvars with: connect_phone_number = \"$PHONE_NUMBER\""
echo "2. Associate number with contact flow in AWS Console"
echo "3. Test by calling: $PHONE_NUMBER"
```

**Make it executable:**

```bash
chmod +x /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/scripts/claim_phone_number.sh
```

**Run it:**

```bash
./scripts/claim_phone_number.sh
```

---

## Creating Connect Instance First (If Needed)

If you don't have a Connect instance yet, create one:

### Via Console

1. Go to: https://console.aws.amazon.com/connect/
2. Click: **Create instance**
3. **Step 1 - Identity management:**
   - Select: **Store users within Amazon Connect**
   - Access URL: `pf-voice-dev` (must be globally unique)
   - Click: **Next**
4. **Step 2 - Administrator:**
   - Skip (you can add later)
   - Click: **Skip this**
5. **Step 3 - Telephony:**
   - ✅ Enable: **I want to handle incoming calls with Amazon Connect**
   - ✅ Enable: **I want to make outbound calls with Amazon Connect**
   - Click: **Next**
6. **Step 4 - Data storage:**
   - Accept defaults (S3 buckets auto-created)
   - Click: **Next**
7. **Step 5 - Review and create:**
   - Click: **Create instance**
   - Wait 2-3 minutes for instance to provision

### Via Terraform (Automated)

You already have this in your codebase:

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/infrastructure/terraform/voice

# Initialize
terraform init

# Create instance + all resources
terraform apply
```

This will create:
- Connect instance
- S3 bucket for recordings
- KMS encryption keys
- Hours of operation (24/7)
- Queue for handling calls

**Then claim number** using console or CLI methods above.

---

## After Claiming Number

### Update Terraform Variables

Edit: `/Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/infrastructure/terraform/voice/terraform.tfvars`

```hcl
connect_phone_number = "+18005551234"  # Your actual claimed number
```

### Associate Number with Contact Flow

**Via Console:**

1. AWS Connect Console → **Channels → Phone numbers**
2. Click on your claimed number
3. **Contact flow / IVR:** Select `pf-main-inbound` (create this first)
4. Click: **Save**

**Via CLI:**

```bash
PHONE_NUMBER_ID="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
CONTACT_FLOW_ID="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
INSTANCE_ID="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

aws connect update-phone-number \
  --phone-number-id "$PHONE_NUMBER_ID" \
  --target-arn "arn:aws:connect:us-east-1:618048437522:instance/$INSTANCE_ID/contact-flow/$CONTACT_FLOW_ID" \
  --region us-east-1
```

---

## Testing Your Number

### Test 1: Call from Mobile Phone

```bash
# Just dial the number from any phone
# You should hear the default greeting or your custom contact flow
```

### Test 2: Verify in CLI

```bash
# Get number details
aws connect describe-phone-number \
  --phone-number-id "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" \
  --region us-east-1
```

---

## Pricing for Phone Numbers

| Type | Monthly Cost | Per-Minute Cost | Best For |
|------|--------------|-----------------|----------|
| **Toll-Free** | $2.00/month | $0.022/min inbound | Business, customer service |
| **DID (Local)** | $0.90/month | $0.0022/min inbound | Local presence, regional offices |

**Example Cost (Toll-Free):**
- Number lease: $2.00/month
- 300 minutes of calls: 300 × $0.022 = $6.60
- **Total:** $8.60/month for phone number costs

**Note:** This is JUST the phone number cost. Add AWS Connect usage, Lex, Bedrock, etc. on top.

---

## Common Issues

### Issue 1: "No numbers available"

**Solution:** Try different area codes or use toll-free instead of DID.

```bash
# Try multiple area codes
for area in 813 727 941 239; do
  echo "Trying area code $area..."
  aws connect search-available-phone-numbers \
    --target-arn "$INSTANCE_ARN" \
    --phone-number-country-code "US" \
    --phone-number-type "DID" \
    --phone-number-prefix "$area" \
    --max-results 5 \
    --region us-east-1
done
```

### Issue 2: "Instance alias already exists"

**Error:** Instance alias `pf-voice-dev` is taken globally.

**Solution:** Try a different alias:
- `pf-voice-dev-2025`
- `projectforce-voice`
- `pf-{your-company}-voice`

### Issue 3: "AccessDeniedException"

**Error:** Not authorized to claim phone numbers.

**Solution:** Add IAM permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "connect:ClaimPhoneNumber",
        "connect:SearchAvailablePhoneNumbers",
        "connect:ListPhoneNumbers",
        "connect:DescribePhoneNumber",
        "connect:UpdatePhoneNumber"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## Release Number (If Needed)

To release a claimed number:

```bash
PHONE_NUMBER_ID="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

aws connect release-phone-number \
  --phone-number-id "$PHONE_NUMBER_ID" \
  --region us-east-1
```

**Warning:** This is permanent! The number goes back to the pool.

---

## Next Steps After Claiming

1. ✅ Number claimed
2. → Update Terraform variables
3. → Create contact flow
4. → Associate number with flow
5. → Test by calling
6. → Deploy Lex bot integration
7. → Connect to Bedrock agents

See `docs/AWS_CONNECT_IMPLEMENTATION_PLAN.md` for full deployment steps.

---

**Quick Reference:**

```bash
# Check if Connect instance exists
aws connect list-instances --region us-east-1

# Search toll-free numbers
aws connect search-available-phone-numbers \
  --target-arn "<instance-arn>" \
  --phone-number-country-code "US" \
  --phone-number-type "TOLL_FREE" \
  --max-results 10 \
  --region us-east-1

# Claim number
aws connect claim-phone-number \
  --target-arn "<instance-arn>" \
  --phone-number "+18005551234" \
  --region us-east-1

# List claimed numbers
aws connect list-phone-numbers-v2 \
  --target-arn "<instance-arn>" \
  --region us-east-1
```
