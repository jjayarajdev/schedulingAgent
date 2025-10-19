# Agent Configuration

Documentation extracted from source code.

## Agent Components

### LLM Configuration
From `core/llm.py`, lines 15-21:
```python
llm = ChatOpenAI(
    model="gpt-4.1",
    temperature=0,
    rate_limiter=rate_limiter,
    max_retries=3,
    timeout=60,
)
```

**Rate Limiter** (lines 9-13):
```python
rate_limiter = InMemoryRateLimiter(
    requests_per_second=0.8,
    check_every_n_seconds=0.1,
    max_bucket_size=5,
)
```

### Memory
From `core/memory.py`, line 2:
```python
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
```

### Agent Setup
From `core/langchain_agent.py`, lines 192-195:
```python
function_agent = create_openai_functions_agent(llm=llm, tools=tools, prompt=prompt)
agent = AgentExecutor(agent=function_agent, tools=tools, memory=memory, verbose=True)
```

## Registered Tools

From `core/langchain_agent.py`, lines 34-115, the following 14 tools are registered:

1. **ListProjects** - List all available projects
2. **SwitchProject** - Switch active project by text description
3. **ShowProjectDetails** - Return full project details
4. **GetWorkingDays** - Get working days for session
5. **GetAvailableDates** - Get available appointment dates
6. **GetSlotsForDate** - Get time slots for a date
7. **UpdateDate** - Update selected appointment date
8. **ConfirmAppointment** - Confirm appointment (HH:MM:SS format)
9. **ShowSessionState** - Debug session state
10. **CancelSchedule** - Cancel appointment
11. **LoadAvailableProjects** - Load project details
12. **GetCurrentWeather** - Get weather for a city
13. **AddProjectNote** - Add customer note to project

## Prompt Template

From `core/langchain_agent.py`, lines 118-179:
```python
prompt = ChatPromptTemplate.from_messages([
    ("system", "...system prompt..."),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad")
])
```

## System Prompt Key Instructions

The system prompt (lines 119-175) instructs the agent on:

**Core Behavior:**
- Act as customer service assistant for scheduling/rescheduling/cancellations
- Greet user first, then proceed with steps
- Format messages in well-separated lines
- Display times in AM/PM format (not military time)
- Never expose session_id or project_id to users

**Project Management:**
- Call ListProjects when project_id not set
- Show projects with order_number, type, category, status, and project URL
- Users can select by list number, order_number, type, category, or status
- Use SwitchProject with natural language descriptions
- Always include project URL as clickable markdown hyperlink
- Format details with markdown bullets

**Scheduling Flow:**
- Check working days before providing dates/slots
- Use GetAvailableDates or reuse from session_context
- Fetch actual slots using get_slots_for_date
- Show first 3 consecutive earliest date-slot pairs
- Ask if user wants more, then show next 3-5 pairs
- Never invent or infer dates/slots
- Display dates and times on separate lines

**Confirmation:**
- Always get user confirmation before schedule/reschedule/cancel
- Show project details and chosen date/time
- Confirm even if user changes dates/slots mid-conversation

**Post-Appointment:**
- Say appointment is "tentatively scheduled"
- Include: date, time, order_number, category, type, address
- Note technician will call/text when en route
- Note office will review and update status
- Load projects again via LoadAvailableProjects
- Offer to add customer notes via AddProjectNote

**Scheduled Projects:**
- Offer options: reschedule, cancel, add note, or view details

**Context Management:**
- Use session_context to avoid unnecessary tool calls
- Only call tools when data not in session_context
- After schedule/reschedule/cancel, reload projects

**Weather:**
- Answer weather questions using GetCurrentWeather tool

## Agent Execution

From `api/routes.py`, lines 29-36:
```python
prompt_with_session = (
    f"My session ID is {parsed['session_id']}. "
    f"Customer ID is {parsed['customer_id']}. "
    f"Message: {parsed['message']}"
)

result = agent.invoke({"input": prompt_with_session})
return ChatResponse(response=result["output"])
```

The agent receives the user message with session and customer IDs, processes it through the tools and LLM, and returns the response.
