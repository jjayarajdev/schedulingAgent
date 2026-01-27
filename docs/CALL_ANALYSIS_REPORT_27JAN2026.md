# VAPI Call Analysis Report

**Date Range:** January 25-26, 2026
**Export ID:** 9bc7e827-d48a-4c28-ab51-e4c3284116cc
**Analysis Date:** January 27, 2026

---

## Executive Summary

| Metric | Value |
|--------|-------|
| **Total Calls** | 9 |
| **Total Duration** | 27.0 minutes |
| **Average Duration** | 3.0 minutes |
| **Total Cost** | $4.63 |
| **Average Cost/Call** | $0.51 |
| **Success Rate** | 22% (2/9) |

### Critical Finding

**78% of calls (7/9) ended without successful scheduling** - primarily due to "No dates available" responses from the scheduling system.

---

## Issue Breakdown

| Issue | Count | Percentage | Severity |
|-------|-------|------------|----------|
| **No Dates Available** | 4 | 44% | HIGH |
| **Customer Frustration** | 3 | 33% | HIGH |
| **Escalation to Human** | 3 | 33% | MEDIUM |
| **Scheduling Blocked** | 1 | 11% | MEDIUM |
| **Misunderstanding** | 1 | 11% | LOW |

---

## Detailed Call Analysis

### Call 1: Jennifer (019bfbbc-5fa)
| Attribute | Value |
|-----------|-------|
| **Duration** | 1.8 min |
| **Cost** | $0.28 |
| **Outcome** | UNSUCCESSFUL |
| **Issues** | No dates available |

**Summary:** Customer called to schedule blinds appointment. AI found no open dates. Customer asked to check again later.

**Key Dialogue:**
```
User: "Schedule an appointment"
AI: "No open dates for this project right now. Want me to check again in a few days?"
```

---

### Call 2: Susan (019bfbaa-bbd)
| Attribute | Value |
|-----------|-------|
| **Duration** | 3.1 min |
| **Cost** | $0.47 |
| **Outcome** | UNSUCCESSFUL |
| **Issues** | No dates, Frustration, Escalation, Misunderstanding |

**Summary:** Customer wanted to schedule shades measurement but AI kept referencing "blinds project." Multiple misunderstandings led to frustration and request for human operator.

**Key Dialogue:**
```
User: "I'd like to schedule a visit to our home to measure for shade"
AI: "I see your blinds project is ready. Would you like me to check available dates?"
User: "Schedule an appointment to measure for shades"
AI: "I see your blinds project is ready..."  (repeated)
```

**Root Cause:** AI didn't understand "shades" vs "blinds" terminology - likely the same project with different customer terminology.

---

### Call 3: Jennifer (019bfb88-98e)
| Attribute | Value |
|-----------|-------|
| **Duration** | 2.1 min |
| **Cost** | $0.30 |
| **Outcome** | UNSUCCESSFUL |
| **Issues** | No dates available |

**Summary:** Customer confirmed blinds project at Howell Lowe's. No dates available.

**Key Dialogue:**
```
AI: "Your blinds measurement project is ready at the Howell Lowe's store"
User: "Look at available dates"
AI: "No open dates are available for this project right now"
```

---

### Call 4: Bradley (019bfb6c-21c)
| Attribute | Value |
|-----------|-------|
| **Duration** | 1.9 min |
| **Cost** | $0.32 |
| **Outcome** | UNSUCCESSFUL |
| **Issues** | Scheduling blocked, Escalation |

**Summary:** Customer's project status was "Customer Scheduled Rejected" - meaning WTU sent a date that didn't work. Customer wanted to pick a new date but AI couldn't proceed due to status.

**Key Dialogue:**
```
User: "You guys sent me a date that didn't work for me. So let's find a date that works"
AI: "Unfortunately, the project status is 'customer scheduled rejected', which means it can't be scheduled through me"
AI: "You can reach our office at 860-269-9040"
```

**Root Cause:** Status "Customer Scheduled Rejected" should be schedulable - customer is trying to pick a date after rejecting the one sent to them.

---

### Call 5: Laurie (019bfb59-bc4)
| Attribute | Value |
|-----------|-------|
| **Duration** | 1.3 min |
| **Cost** | $0.26 |
| **Outcome** | SUCCESSFUL (info provided) |
| **Issues** | No dates available |

**Summary:** Quick call - customer asked for dates, none available, asked to check later. Marked successful because expectation was set appropriately.

---

### Call 6: George (019bfb0b-92e)
| Attribute | Value |
|-----------|-------|
| **Duration** | 1.3 min |
| **Cost** | $0.20 |
| **Outcome** | SUCCESSFUL |
| **Issues** | None |

**Summary:** Customer already had appointment scheduled. AI correctly identified this and provided appointment details.

**Key Dialogue:**
```
AI: "Your blinds project is already scheduled. Would you like to reschedule or check the details?"
AI: "Your blinds measurement is scheduled with Anthony on January 29th at 4:30 PM"
```

**This is the ideal flow for already-scheduled projects.**

---

### Call 7: Amy (019bfad9-b09)
| Attribute | Value |
|-----------|-------|
| **Duration** | 8.5 min |
| **Cost** | $1.58 |
| **Outcome** | UNSUCCESSFUL |
| **Issues** | Customer frustration |

**Summary:** LONGEST CALL. Customer tried to reschedule blinds measurement at 210 Free Street, Marblehead. Repeatedly told dates were "booked up." 8+ minute call with no resolution.

**Key Dialogue:**
```
User: "I would like to schedule the measuring appointment"
AI: "Your blinds project is already scheduled. Would you like to reschedule?"
User: "I'd like to reschedule"
AI: "Let me find the available dates..."
AI: "I need a bit more info to help you reschedule. Which project are you calling about?"
```

**Root Cause:** AI lost context during reschedule flow - kept asking for project info after already identifying it.

---

### Call 8: Gail (019bfa9e-df1)
| Attribute | Value |
|-----------|-------|
| **Duration** | 2.7 min |
| **Cost** | $0.58 |
| **Outcome** | UNSUCCESSFUL |
| **Issues** | No dates, Escalation |

**Summary:** Customer confused by "no dates available" message. Asked about February/March - still no dates. AI provided office number.

**Key Dialogue:**
```
User: "What does that mean? There's no dates available?"
AI: "Currently there are no available appointment slots for scheduling your blinds project"
User: "I need the blinds. I need to schedule a blind date. There's nothing available?"
```

**Root Cause:** Customer doesn't understand WHY no dates - system should explain (technician availability, area coverage, etc.)

---

### Call 9: Steven (019bf6ad-c84)
| Attribute | Value |
|-----------|-------|
| **Duration** | 4.5 min |
| **Cost** | $0.64 |
| **Outcome** | UNSUCCESSFUL |
| **Issues** | Customer frustration |

**Summary:** AI offered Friday Jan 30th at 8:30 AM only. Customer didn't like it. Then AI said "no open dates." Customer asked to speak to person.

**Key Dialogue:**
```
AI: "I've got Friday, January 30th available. Would that work for you?"
AI: "There's just 1 time slot available, 8:30 AM"
[Customer declined]
AI: "No open dates for this project right now"
User: "Can I speak to a person?"
```

**Root Cause:** After declining the only slot, AI says "no dates" instead of offering to call back with more options.

---

## Root Cause Analysis

### 1. No Dates Available (44% of calls)
**Problem:** The scheduling system frequently returns zero available dates.

**Possible Causes:**
- Technician schedules not loaded
- Geographic area not covered
- System configuration issue
- Genuine capacity constraint

**Recommendation:** Investigate the PF360 API `get_available_dates` responses for WTU tenant.

---

### 2. Status Blocking (11%)
**Problem:** "Customer Scheduled Rejected" status prevents scheduling.

**Current Behavior:**
```
AI: "This project can't be scheduled right now. The status is 'customer scheduled rejected'"
```

**Expected Behavior:** This status SHOULD be schedulable - customer rejected the date WTU proposed and wants to pick their own.

**Recommendation:** Add "Customer Scheduled Rejected" to the schedulable statuses list in `intelligent_orchestrator.py`.

---

### 3. Reschedule Flow Issues (11%)
**Problem:** AI loses context during reschedule flow - asks for project info after already identifying it.

**Recommendation:** Review workflow state preservation during reschedule_appointment action.

---

### 4. No Explanation for Unavailability (33%)
**Problem:** When no dates are available, AI doesn't explain WHY.

**Current Response:**
```
"No open dates for this project right now"
```

**Better Response:**
```
"No dates are currently available for your area. This usually means our technicians
are fully booked or we're expanding coverage. Would you like me to check again
in a few days, or should I give you our office number?"
```

---

## Recommendations

### Immediate (P0)

1. **Investigate WTU Date Availability**
   - Check why `get_available_dates` returns empty for most calls
   - Verify technician schedules are loaded in PF360
   - Check geographic coverage configuration

2. **Add "Customer Scheduled Rejected" to Schedulable Statuses**
   ```python
   schedulable_statuses = ['New', 'Ready To Schedule', 'Customer Scheduled Rejected']
   ```

### Short-term (P1)

3. **Improve "No Dates" Response**
   - Explain why no dates (area, capacity, etc.)
   - Offer proactive callback when dates become available
   - Always provide office number as fallback

4. **Fix Reschedule Context Loss**
   - Ensure project_id persists through reschedule flow
   - Don't re-prompt for project info after identifying it

### Medium-term (P2)

5. **Add "Shades" Synonym**
   - Map "shades" terminology to "blinds" project category
   - Handle customer terminology variations

6. **Proactive Capacity Alerts**
   - If area has no availability for 2+ weeks, offer escalation sooner
   - Don't make customer go through full flow to find out no dates

---

## Call-by-Call Summary Table

| Call | Customer | Duration | Cost | Success | Key Issue |
|------|----------|----------|------|---------|-----------|
| 1 | Jennifer | 1.8m | $0.28 | NO | No dates |
| 2 | Susan | 3.1m | $0.47 | NO | Misunderstanding + No dates |
| 3 | Jennifer | 2.1m | $0.30 | NO | No dates |
| 4 | Bradley | 1.9m | $0.32 | NO | Status blocked |
| 5 | Laurie | 1.3m | $0.26 | YES | No dates (handled well) |
| 6 | George | 1.3m | $0.20 | YES | None - perfect flow |
| 7 | Amy | 8.5m | $1.58 | NO | Reschedule confusion |
| 8 | Gail | 2.7m | $0.58 | NO | No dates + confusion |
| 9 | Steven | 4.5m | $0.64 | NO | Limited slots rejected |

---

## Metrics Comparison

| Metric | This Report | Previous (Jan 21-22) | Trend |
|--------|-------------|---------------------|-------|
| Success Rate | 22% | ~30% | DOWN |
| Avg Duration | 3.0m | 2.5m | UP |
| Escalations | 33% | 25% | UP |
| No Dates Issue | 44% | 35% | UP |

**Trend Analysis:** Scheduling availability is worsening, leading to more failed calls and escalations.

---

*Report generated by Claude Code - ProjectForce AI Assistant*
