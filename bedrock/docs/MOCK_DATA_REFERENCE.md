# Mock Data Reference

**Purpose:** Quick reference for testing agents with valid mock data
**Environment:** `USE_MOCK_API=true` (default for Lambda functions)
**Last Updated:** 2025-10-19

---

## 📦 Mock Project IDs

### Project 12345 - Flooring Installation
- **ID:** `12345`
- **Number:** ORD-2025-001
- **Type:** Installation
- **Category:** Flooring
- **Status:** Scheduled
- **Address:** 123 Main St, Tampa, FL 33601
- **Scheduled:** 2025-10-15, 08:00 AM - 12:00 PM
- **Duration:** 4 hours
- **Technician:** John Smith
- **Store:** ST-101

### Project 12347 - Windows Installation
- **ID:** `12347`
- **Number:** ORD-2025-002
- **Type:** Installation
- **Category:** Windows
- **Status:** Pending (Not Scheduled)
- **Address:** 456 Oak Ave, Tampa, FL 33602
- **Duration:** 3 hours
- **Technician:** Jane Doe
- **Store:** ST-102

### Project 12350 - Deck Repair
- **ID:** `12350`
- **Number:** ORD-2025-003
- **Type:** Repair
- **Category:** Deck Repair
- **Status:** Pending (Not Scheduled)
- **Address:** 789 Pine Dr, Clearwater, FL 33755
- **Duration:** 2 hours
- **Technician:** Mike Johnson
- **Store:** ST-103

---

## 👥 Mock Customer IDs

- **CUST001** - Generic test customer (used in all examples)
- **CUST_BIGCORP** - B2B multi-client customer (for B2B testing)

---

## 🏢 Mock Client IDs (B2B Testing)

- **09PF05VD** - Tampa Office (primary)
- **09PF05WE** - Miami Office
- **09PF05XF** - Orlando Office
- **09PF05YG** - Jacksonville Office

---

## 📅 Available Dates

Mock API returns next **10 weekdays** from current date (Mon-Fri only)

Example dates (relative to today):
- Tomorrow (if weekday)
- Day after tomorrow (if weekday)
- Next 8 weekdays

---

## ⏰ Available Time Slots

Standard time slots (all projects):
- 08:00 AM
- 09:00 AM
- 10:00 AM
- 11:00 AM
- 01:00 PM
- 02:00 PM
- 03:00 PM
- 04:00 PM
- 05:00 PM

---

## 🕐 Working Hours

**Default Hours:**
- Monday - Friday: 8:00 AM - 6:00 PM
- Saturday: 9:00 AM - 4:00 PM
- Sunday: Closed

**Time Zone:** Eastern Time (ET)

---

## 🌤️ Weather Data

Mock weather returns for any location:
- **Temperature:** 75°F
- **Conditions:** Partly Cloudy
- **High:** 82°F
- **Low:** 68°F
- **Humidity:** 65%
- **Precipitation:** 10% chance

---

## 🧪 Test Queries by Agent

### Supervisor Agent Tests

```
1. Show me all projects for customer CUST001
2. Tell me about project 12345 for customer CUST001
3. I want to schedule project 12347
4. Add a note to project 12345: Customer prefers mornings
5. What are your business hours?
6. Hello! How are you?
```

### Scheduling Agent Tests

```
1. Show me all projects for customer CUST001
2. What dates are available for project 12347?
3. Show me time slots for project 12347 on [pick a date]
4. Book project 12347 for [date] at 10:00 AM
5. Cancel appointment for project 12345
```

### Information Agent Tests

```
1. Tell me about project 12345 for customer CUST001
2. What's the appointment status for project 12345?
3. What are your business hours?
4. What's the weather like in Tampa?
```

### Notes Agent Tests

```
1. Add a note to project 12345: Customer prefers morning appointments
2. Show me all notes for project 12345
3. Add a note to project 12347: Gate code is 1234 (author: John Smith)
```

### Chitchat Agent Tests

```
1. Hello! How are you?
2. How's the weather today?
3. What services do you offer?
4. Thanks! Goodbye
5. Can you schedule an appointment?
```

---

## 🔍 Testing Workflow

### Complete Multi-Step Workflow

```
Step 1: Show me my projects for customer CUST001
→ Returns 3 projects

Step 2: Tell me about project 12347 for customer CUST001
→ Returns Windows Installation details

Step 3: What dates are available for project 12347?
→ Returns next 10 weekdays

Step 4: Book project 12347 for [select date] at 10:00 AM
→ Confirms appointment

Step 5: Add a note to project 12347: Customer requested morning slot
→ Confirms note added

Step 6: What's the appointment status for project 12347?
→ Returns newly scheduled appointment
```

---

## ⚙️ Switching Between Mock and Real API

### Check Current Mode

```bash
aws lambda get-function-configuration \
  --function-name scheduling-agent-scheduling-actions \
  --region us-east-1 \
  --query 'Environment.Variables.USE_MOCK_API' \
  --output text
```

### Enable Mock Mode

```bash
aws lambda update-function-configuration \
  --function-name scheduling-agent-scheduling-actions \
  --environment Variables={USE_MOCK_API=true} \
  --region us-east-1
```

### Enable Real API Mode

```bash
aws lambda update-function-configuration \
  --function-name scheduling-agent-scheduling-actions \
  --environment Variables={USE_MOCK_API=false} \
  --region us-east-1
```

**Note:** Update all 3 Lambda functions:
- `scheduling-agent-scheduling-actions`
- `scheduling-agent-information-actions`
- `scheduling-agent-notes-actions`

---

## 📝 Notes About Mock Data

1. **In-Memory Storage:** Notes added in mock mode are stored in memory and cleared on Lambda restart
2. **Consistent IDs:** Always use numeric IDs (12345, 12347, 12350), not PROJECT001 format
3. **Customer Context:** All mock projects return the same customer details regardless of customer_id provided
4. **Date Calculation:** Available dates are dynamically calculated from current date
5. **Request IDs:** Mock API generates unique request IDs for each availability check

---

## 🎯 Common Testing Mistakes

❌ **Wrong Project ID Format**
```
Tell me about project PROJECT001  # WRONG - doesn't exist
```

✅ **Correct Project ID Format**
```
Tell me about project 12345  # CORRECT - mock data exists
```

❌ **Invalid Customer ID in Real API**
```
Show projects for customer CUST001  # Works in mock, fails in real API
```

✅ **Valid Customer ID for Real API**
```
Show projects for customer 1234  # Real PF360 customer ID (numeric)
```

---

## 🚀 Quick Start Testing

1. **Verify Mock Mode is Enabled**
   ```bash
   aws lambda get-function-configuration \
     --function-name scheduling-agent-scheduling-actions \
     --region us-east-1 \
     --query 'Environment.Variables.USE_MOCK_API'
   ```

2. **Open Supervisor Agent Test Console**
   ```
   https://us-east-1.console.aws.amazon.com/bedrock/home?region=us-east-1#/agents/5VTIWONUMO
   ```

3. **Try First Test Query**
   ```
   Show me all projects for customer CUST001
   ```

4. **Expect to See 3 Projects Returned**
   - 12345 (Flooring, Scheduled)
   - 12347 (Windows, Pending)
   - 12350 (Deck, Pending)

---

**Related Docs:**
- `SUPERVISOR_AGENT_SETUP.md` - Testing section
- `SCHEDULING_AGENT_SETUP.md` - Testing section
- `INFORMATION_AGENT_SETUP.md` - Testing section
- `NOTES_AGENT_SETUP.md` - Testing section
- `B2B_MULTI_CLIENT_INTEGRATION_GUIDE.md` - B2B testing scenarios
