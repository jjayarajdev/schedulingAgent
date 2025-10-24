# Individual Agent Test Plan

## Test Configuration

**Test Customer**:
- Customer ID: `1645975`
- Client ID: `09PF05VD`

**Test Environment**:
- Region: `us-east-1`
- Alias: `TSTALIASID` (test alias)
- Mode: Direct agent invocation (bypassing supervisor)

---

## 1. Scheduling Agent (TIGRBGSXCS)

**Purpose**: Handles appointment scheduling, availability checking, and appointment management

### Test Case 1.1: List Projects
**Input**: `"Show me my projects"`
**Session Attributes**:
```json
{
  "customer_id": "1645975",
  "client_id": "09PF05VD"
}
```
**Expected**:
- ✅ Calls `list_projects` Lambda action
- ✅ Returns list of 3 projects with details (project_id, order_number, type, status, address)
- ✅ Projects formatted as numbered list

**Success Criteria**:
- Response contains actual project data from Lambda (not made up)
- All project fields present: project_id, order_number, project_type, category, status, store, address
- Mock mode indicator shown

---

### Test Case 1.2: Get Available Dates
**Input**: `"What dates are available for project 138836?"`
**Session Attributes**:
```json
{
  "customer_id": "1645975",
  "client_id": "09PF05VD",
  "project_id": "138836"
}
```
**Expected**:
- ✅ Calls `get_available_dates` Lambda action
- ✅ Returns list of available dates
- ✅ Includes request_id for next step

**Success Criteria**:
- Response contains date list from Lambda
- request_id is provided for time slot lookup
- Dates are in readable format

---

### Test Case 1.3: Get Time Slots
**Input**: `"Show me available time slots for 2024-11-15"`
**Session Attributes**:
```json
{
  "customer_id": "1645975",
  "client_id": "09PF05VD",
  "project_id": "138836",
  "date": "2024-11-15",
  "request_id": "REQ123"
}
```
**Expected**:
- ✅ Calls `get_time_slots` Lambda action
- ✅ Returns available time slots for the date
- ✅ Time slots formatted clearly

**Success Criteria**:
- Response contains time slot data from Lambda
- Time slots include start/end times
- Clear formatting for selection

---

### Test Case 1.4: Confirm Appointment (Mock Mode)
**Input**: `"Confirm appointment for 2024-11-15 at 09:00 AM"`
**Session Attributes**:
```json
{
  "customer_id": "1645975",
  "client_id": "09PF05VD",
  "project_id": "138836",
  "date": "2024-11-15",
  "time": "09:00",
  "request_id": "REQ123"
}
```
**Expected**:
- ✅ Calls `confirm_appointment` Lambda action (mock mode)
- ✅ Returns confirmation message
- ✅ Includes scheduled date and time

**Success Criteria**:
- Confirmation message received
- Mock mode indicator shown
- No actual appointment created in system

---

### Test Case 1.5: Cancel Appointment (Mock Mode)
**Input**: `"Cancel my appointment for project 138836"`
**Session Attributes**:
```json
{
  "customer_id": "1645975",
  "client_id": "09PF05VD",
  "project_id": "138836"
}
```
**Expected**:
- ✅ Calls `cancel_appointment` Lambda action (mock mode)
- ✅ Returns cancellation confirmation
- ✅ Provides cancellation details

**Success Criteria**:
- Cancellation confirmed
- Mock mode indicator shown
- No actual appointment cancelled in system

---

## 2. Information Agent (JEK4SDJOOU)

**Purpose**: Provides information about projects, business hours, and weather

### Test Case 2.1: Get Business Hours
**Input**: `"What are your business hours?"`
**Session Attributes**:
```json
{
  "customer_id": "1645975",
  "client_id": "09PF05VD"
}
```
**Expected**:
- ✅ Calls `get_business_hours` Lambda action
- ✅ Returns business hours (weekday/weekend)
- ✅ Formatted clearly with times

**Success Criteria**:
- Business hours returned from Lambda
- Shows weekday and weekend hours
- Clear, readable format

---

### Test Case 2.2: Get Weather Forecast
**Input**: `"What's the weather forecast for November 15, 2024?"`
**Session Attributes**:
```json
{
  "customer_id": "1645975",
  "client_id": "09PF05VD",
  "date": "2024-11-15"
}
```
**Expected**:
- ✅ Calls `get_weather` Lambda action
- ✅ Returns weather forecast for the date
- ✅ Includes temperature, conditions, precipitation

**Success Criteria**:
- Weather data returned from Lambda
- Temperature and conditions shown
- Helpful for appointment planning

---

### Test Case 2.3: Get Project Information
**Input**: `"Tell me about project 138836"`
**Session Attributes**:
```json
{
  "customer_id": "1645975",
  "client_id": "09PF05VD",
  "project_id": "138836"
}
```
**Expected**:
- ✅ Calls `get_project_info` Lambda action
- ✅ Returns detailed project information
- ✅ Includes type, status, address, scheduled date

**Success Criteria**:
- Project details returned from Lambda
- All relevant fields present
- Information matches project records

---

### Test Case 2.4: General Information Query
**Input**: `"How does the scheduling process work?"`
**Session Attributes**:
```json
{
  "customer_id": "1645975",
  "client_id": "09PF05VD"
}
```
**Expected**:
- ✅ Agent provides helpful explanation
- ✅ Explains scheduling workflow
- ✅ Offers to help with next steps

**Success Criteria**:
- Clear explanation provided
- Helpful and informative
- Offers guidance on how to proceed

---

## 3. Notes Agent (CF0IPHCFFY)

**Purpose**: Manages notes and communication related to projects

### Test Case 3.1: Add Note to Project
**Input**: `"Add a note to project 138836: Customer prefers morning appointments"`
**Session Attributes**:
```json
{
  "customer_id": "1645975",
  "client_id": "09PF05VD",
  "project_id": "138836",
  "note_text": "Customer prefers morning appointments"
}
```
**Expected**:
- ✅ Calls `add_note` Lambda action
- ✅ Returns confirmation of note added
- ✅ Includes note ID or timestamp

**Success Criteria**:
- Note creation confirmed
- Note ID provided
- Confirmation message clear

---

### Test Case 3.2: View Notes for Project
**Input**: `"Show me all notes for project 138836"`
**Session Attributes**:
```json
{
  "customer_id": "1645975",
  "client_id": "09PF05VD",
  "project_id": "138836"
}
```
**Expected**:
- ✅ Calls `get_notes` Lambda action
- ✅ Returns list of notes for the project
- ✅ Includes timestamps and note text

**Success Criteria**:
- Notes list returned from Lambda
- Chronological order
- Clear formatting

---

### Test Case 3.3: Update Existing Note
**Input**: `"Update note NOTE123 to say: Customer prefers afternoon appointments after 2 PM"`
**Session Attributes**:
```json
{
  "customer_id": "1645975",
  "client_id": "09PF05VD",
  "project_id": "138836",
  "note_id": "NOTE123",
  "note_text": "Customer prefers afternoon appointments after 2 PM"
}
```
**Expected**:
- ✅ Calls `update_note` Lambda action
- ✅ Returns confirmation of update
- ✅ Shows updated content

**Success Criteria**:
- Update confirmed
- New content saved
- Timestamp updated

---

### Test Case 3.4: Delete Note
**Input**: `"Delete note NOTE123"`
**Session Attributes**:
```json
{
  "customer_id": "1645975",
  "client_id": "09PF05VD",
  "project_id": "138836",
  "note_id": "NOTE123"
}
```
**Expected**:
- ✅ Calls `delete_note` Lambda action
- ✅ Returns deletion confirmation
- ✅ Note removed from system

**Success Criteria**:
- Deletion confirmed
- Note no longer retrievable
- Clear confirmation message

---

## 4. Chitchat Agent (GXVZEOBQ64)

**Purpose**: Handles conversational interactions, greetings, and general inquiries

### Test Case 4.1: Greeting - Hello
**Input**: `"Hello! How are you?"`
**Session Attributes**:
```json
{
  "customer_id": "1645975"
}
```
**Expected**:
- ✅ Friendly greeting response
- ✅ Offers to help
- ✅ Warm, conversational tone

**Success Criteria**:
- Response is friendly and welcoming
- Offers assistance
- Natural conversation flow

---

### Test Case 4.2: Greeting - Good Morning
**Input**: `"Good morning!"`
**Session Attributes**:
```json
{
  "customer_id": "1645975"
}
```
**Expected**:
- ✅ Time-appropriate greeting
- ✅ Welcoming response
- ✅ Asks how to help

**Success Criteria**:
- Appropriate morning greeting
- Friendly tone
- Ready to assist

---

### Test Case 4.3: Thank You
**Input**: `"Thank you so much for your help!"`
**Session Attributes**:
```json
{
  "customer_id": "1645975"
}
```
**Expected**:
- ✅ Acknowledges thanks
- ✅ Offers continued assistance
- ✅ Positive, helpful tone

**Success Criteria**:
- Gracious response
- Offers further help
- Maintains friendly rapport

---

### Test Case 4.4: Goodbye
**Input**: `"Goodbye, have a great day!"`
**Session Attributes**:
```json
{
  "customer_id": "1645975"
}
```
**Expected**:
- ✅ Polite farewell
- ✅ Well wishes
- ✅ Leaves door open for future contact

**Success Criteria**:
- Warm goodbye
- Professional closing
- Positive final impression

---

### Test Case 4.5: Help Request
**Input**: `"Can you help me? I'm not sure how to get started."`
**Session Attributes**:
```json
{
  "customer_id": "1645975"
}
```
**Expected**:
- ✅ Reassuring response
- ✅ Explains available services
- ✅ Guides user on next steps

**Success Criteria**:
- Helpful, clear guidance
- Lists available options
- Encourages user to proceed

---

### Test Case 4.6: General Chitchat
**Input**: `"How's the weather today?"`
**Session Attributes**:
```json
{
  "customer_id": "1645975"
}
```
**Expected**:
- ✅ Engages with question
- ✅ Redirects to relevant service (weather info agent)
- ✅ OR acknowledges can't provide real-time weather

**Success Criteria**:
- Acknowledges question
- Provides helpful response or redirection
- Maintains conversation naturally

---

## Test Execution Plan

### Order of Testing:
1. **Chitchat Agent** (simplest - no Lambda calls)
2. **Scheduling Agent** (most complex - multiple Lambda actions)
3. **Information Agent** (moderate complexity)
4. **Notes Agent** (CRUD operations)

### For Each Agent:
1. Run all test cases sequentially
2. Document results in table format:
   - Test Case ID
   - Status (✅ Pass / ❌ Fail / ⚠️ Partial)
   - Response Summary
   - Lambda Called? (Y/N)
   - Issues/Notes

### Success Metrics:
- **Pass**: Agent correctly invokes Lambda AND returns expected data format
- **Partial**: Agent responds but doesn't invoke Lambda or data incomplete
- **Fail**: Agent errors or provides incorrect response

### Output Format:
- Create `AGENT_TEST_RESULTS.md` with detailed results
- Include response excerpts
- Note any issues or unexpected behaviors
- Provide recommendations

---

## Ready to Execute?

Once you approve this test plan, I'll:
1. Create automated test script for all 27 test cases
2. Run tests sequentially
3. Capture all outputs
4. Generate comprehensive results document

Would you like me to proceed with testing?
