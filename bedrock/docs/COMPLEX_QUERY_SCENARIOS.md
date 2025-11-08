# Complex Query Scenarios for Step Functions

## Overview
This document outlines complex multi-step query scenarios that require Step Functions orchestration beyond single-agent capabilities.

## Scenario Categories

### 1. Weather-Dependent Scheduling
**Complexity**: Multi-agent + External API + Conditional Logic

#### Query Examples:
- "If the weather is good next week, schedule my outdoor flooring project"
- "Schedule my deck installation when it's sunny and above 70 degrees"
- "Check the weather for next Monday and schedule my roofing project if it's not raining"

#### Workflow:
1. Get outdoor/weather-sensitive projects (Information Agent)
2. Get weather forecast for project location (Weather API)
3. Evaluate weather conditions against project requirements
4. If suitable → Get available time slots (Scheduling Agent)
5. If suitable → Schedule the project
6. If not suitable → Suggest alternative dates with better weather

#### State Machine: `pf-schedule-weather-dependent`

---

### 2. Batch/Multi-Project Scheduling
**Complexity**: Parallel Processing + Optimization + Multiple Agent Calls

#### Query Examples:
- "Schedule all my pending installation projects"
- "Book appointments for all urgent projects this week"
- "Schedule my flooring projects back-to-back to save time"
- "Find the earliest available slots for all my high-priority projects"

#### Workflow:
1. Get all projects matching criteria (Information Agent)
2. Filter by status/priority/type
3. **Parallel Processing**: For each project:
   - Get available time slots
   - Check technician availability
   - Validate project requirements
4. Optimize scheduling (minimize gaps, same-day if possible)
5. Create appointments for all projects
6. Return batch confirmation with schedule summary

#### State Machine: `pf-schedule-batch-projects`

---

### 3. Conditional Scheduling with Fallback
**Complexity**: Sequential Preference Checking + Dynamic Routing

#### Query Examples:
- "Schedule project PRJ-123 for Monday at 10 AM, or Tuesday if that's not available"
- "Book my appointment for next week, preferably morning but afternoon is fine"
- "Schedule my installation for the 15th, or show me the next 3 available dates"

#### Workflow:
1. Get project details (Information Agent)
2. Check first preference (Scheduling Agent)
3. **Choice State**:
   - If available → Schedule
   - If not → Check second preference
4. If no preferences available → Get next N available slots
5. Return confirmation or options

#### State Machine: `pf-schedule-with-preferences`

---

### 4. Cross-Agent Information Gathering
**Complexity**: Sequential Agent Calls + Data Aggregation

#### Query Examples:
- "What's the status of my flooring project and when can it be rescheduled?"
- "Show me all my projects, their status, and the weather forecast for scheduled dates"
- "Get details for project PRJ-123 and show me alternative time slots"

#### Workflow:
1. Get project details (Information Agent)
2. Get appointment status (Information Agent)
3. Get available time slots (Scheduling Agent)
4. Get weather forecast (if outdoor project)
5. Aggregate all information
6. Return comprehensive response

#### State Machine: `pf-gather-project-info`

---

### 5. Priority-Based Scheduling with Constraints
**Complexity**: Multi-Criteria Filtering + Constraint Validation

#### Query Examples:
- "Schedule my urgent projects that don't conflict with my existing appointments"
- "Find available slots for high-priority projects that are at least 2 hours long"
- "Schedule my installation projects only on weekdays between 9 AM and 3 PM"

#### Workflow:
1. Get all projects matching priority criteria
2. Get existing appointments (to check conflicts)
3. Get available time slots with constraints
4. Filter slots that meet all criteria (duration, time window, no conflicts)
5. Rank by priority and availability
6. Return top recommendations

#### State Machine: `pf-schedule-with-constraints`

---

### 6. Rescheduling with Impact Analysis
**Complexity**: Dependency Checking + Impact Assessment

#### Query Examples:
- "Reschedule my appointment on the 15th to the 20th, what's affected?"
- "I need to move my flooring installation - show me the impact on dependent projects"
- "Cancel my Tuesday appointment and reschedule everything that depends on it"

#### Workflow:
1. Get appointment details (Information Agent)
2. Find dependent/related projects
3. Check impact of rescheduling (technician, customer, dependencies)
4. Get alternative slots that minimize disruption
5. Show impact analysis to user
6. If confirmed → Reschedule with cascading updates

#### State Machine: `pf-reschedule-with-impact`

---

### 7. Multi-Criteria Project Search and Schedule
**Complexity**: Complex Filtering + Ranking + Scheduling

#### Query Examples:
- "Find all my outdoor projects in Tampa and schedule them when weather is good"
- "Schedule all flooring projects for the same technician to maintain consistency"
- "Book my high-priority installations at locations closest to each other"

#### Workflow:
1. Get all projects (Information Agent)
2. Apply multiple filters (type, location, priority, status)
3. Get additional context (weather, technician availability, travel time)
4. Rank projects by composite score
5. Optimize scheduling order
6. Schedule top N projects
7. Return schedule with reasoning

#### State Machine: `pf-smart-schedule-optimizer`

---

### 8. Conditional Multi-Step with User Confirmation
**Complexity**: Human-in-the-Loop + State Persistence

#### Query Examples:
- "Find my urgent projects, show me options, then schedule when I confirm"
- "Check if Monday works, if not show me alternatives, then book after I choose"

#### Workflow:
1. Execute first steps (get projects, check availability)
2. **Pause for user input** (return options to user)
3. Wait for user confirmation/selection
4. Resume execution with user's choice
5. Complete scheduling
6. Return final confirmation

#### State Machine: `pf-schedule-with-confirmation`
**Note**: This requires callback mechanism or integration with frontend state management

---

## Implementation Priority

### Phase 1 (Immediate)
1. ✅ **Urgent Project Scheduling** - COMPLETED
2. 🔄 **Weather-Dependent Scheduling** - IN PROGRESS
3. 🔄 **Batch Scheduling** - IN PROGRESS
4. 🔄 **Conditional with Fallback** - IN PROGRESS

### Phase 2 (Next)
5. Cross-Agent Information Gathering
6. Priority-Based with Constraints

### Phase 3 (Future)
7. Rescheduling with Impact Analysis
8. Multi-Criteria Optimizer
9. Confirmation-Based Scheduling

---

## State Machine Architecture Patterns

### Pattern 1: Sequential with Choice
```
Step1 → Step2 → Choice → Path A → End
                       → Path B → End
```
Used in: Conditional with Fallback, Weather-Dependent

### Pattern 2: Parallel Processing (Map State)
```
GetProjects → Map (for each project):
                ├─ CheckAvailability
                ├─ ValidateRequirements
                └─ GetTechnicianInfo
            → Aggregate → Schedule
```
Used in: Batch Scheduling, Multi-Criteria Optimizer

### Pattern 3: Nested Workflows
```
MainWorkflow → SubWorkflow1 (Step Functions)
            → SubWorkflow2 (Step Functions)
            → Aggregate
```
Used in: Complex scenarios with reusable components

### Pattern 4: Error Handling with Retry
```
Try → Step (with Retry)
   → Catch → Fallback Logic → Alternative Path
```
Used in: All state machines

---

## Required Lambda Functions

### Existing ✅
- `pf-query-router` - Query classification
- `pf-filter-projects` - Project filtering
- `pf-information-actions` - Project data retrieval

### New (To Create) 🆕
1. **`pf-weather-evaluator`** - Evaluate weather conditions for project suitability
2. **`pf-batch-optimizer`** - Optimize batch scheduling order
3. **`pf-slot-validator`** - Validate time slots against constraints
4. **`pf-conflict-checker`** - Check for scheduling conflicts
5. **`pf-impact-analyzer`** - Analyze rescheduling impact

---

## Testing Strategy

### Unit Tests
- Each Lambda function tested independently
- Mock data for all scenarios

### Integration Tests
- State machine execution with test inputs
- Verify all paths (success, failure, edge cases)

### End-to-End Tests
- Full workflow through frontend
- Real API calls (with test data)
- User interaction simulation

### Test Data Requirements
- Multiple customers with various project types
- Different weather conditions
- Various scheduling constraints
- Edge cases (no projects, all slots taken, etc.)

---

## Success Metrics

### Performance
- Query classification: < 500ms
- State machine execution: < 5 seconds
- End-to-end response: < 10 seconds

### Accuracy
- Query routing: > 95% correct classification
- Weather evaluation: > 90% suitable recommendations
- Batch optimization: Schedule at least 80% of requested projects

### Cost
- Average cost per complex query: < $0.001
- Monthly cost for 10,000 queries: < $10

---

## Next Steps

1. ✅ Create this planning document
2. 🔄 Implement weather-dependent state machine
3. 🔄 Implement batch scheduling state machine
4. 🔄 Implement conditional with fallback state machine
5. Create weather-evaluator Lambda
6. Create batch-optimizer Lambda
7. Update query router with new patterns
8. Create comprehensive test suite
9. Deploy all state machines
10. Integrate with Flask backend
11. Test through frontend UI
12. Production deployment

---

## Example Test Cases

### Test Case 1: Weather-Dependent Scheduling
**Input**: "If the weather is good next week, schedule my outdoor flooring project"
**Expected Output**:
```json
{
  "success": true,
  "project": "PRJ-78945 (Flooring)",
  "weather_forecast": "Sunny, 75°F",
  "scheduled_date": "2025-11-03",
  "scheduled_time": "10:00 AM - 2:00 PM",
  "reasoning": "Weather conditions are ideal for outdoor flooring installation"
}
```

### Test Case 2: Batch Scheduling
**Input**: "Schedule all my pending installation projects"
**Expected Output**:
```json
{
  "success": true,
  "scheduled_count": 3,
  "projects_scheduled": [
    {"id": "PRJ-001", "date": "2025-11-03", "time": "9:00 AM"},
    {"id": "PRJ-002", "date": "2025-11-03", "time": "1:00 PM"},
    {"id": "PRJ-003", "date": "2025-11-04", "time": "10:00 AM"}
  ],
  "optimization": "Scheduled PRJ-001 and PRJ-002 on same day to save travel time"
}
```

### Test Case 3: Conditional with Fallback
**Input**: "Schedule PRJ-123 for Monday at 10 AM, or Tuesday if not available"
**Expected Output**:
```json
{
  "success": true,
  "project": "PRJ-123",
  "scheduled_date": "Tuesday, 2025-11-04",
  "scheduled_time": "10:00 AM",
  "reasoning": "Monday 10 AM was not available. Scheduled for Tuesday 10 AM as requested."
}
```

---

## References
- Existing state machine: `pf-schedule-urgent-project`
- Deployment script: `scripts/deploy_step_functions.sh`
- Test script: `tests/test_step_functions.py`
- Documentation: `docs/STEP_FUNCTIONS_IMPLEMENTATION.md`
