# Intent Classification Testing UI

**Version**: 2.0
**Purpose**: Interactive web-based UI for testing all 27 classification test queries
**Date**: October 26, 2025

---

## Overview

This testing UI provides an interactive way to test the v2.0 frontend routing classification system. It allows you to:

- ✅ Test all 27 predefined queries with one click
- ✅ Test individual queries interactively
- ✅ Test custom queries in real-time
- ✅ See classification results immediately
- ✅ Track accuracy metrics
- ✅ View which agent would handle each query
- ✅ Monitor classification performance

---

## Quick Start

### 1. Start the Backend Server

```bash
# Navigate to backend directory
cd frontend/backend

# Start Flask server
python3 app.py
```

The server will start on **http://localhost:5001**

### 2. Open the Testing UI

Open `frontend/test_ui.html` in your web browser:

```bash
# Option 1: Open directly
open frontend/test_ui.html

# Option 2: Using a simple HTTP server (recommended)
cd frontend
python3 -m http.server 8000

# Then open: http://localhost:8000/test_ui.html
```

### 3. Test Queries

**Individual Testing:**
- Click any query button to test classification
- Results appear on the right panel
- Buttons turn green (✅ correct) or red (❌ incorrect)

**Batch Testing:**
- Click "🚀 Test All Queries (Batch)" button
- Watch the progress bar
- See final accuracy summary

**Custom Testing:**
- Enter your own query in the "Custom Query" field
- Click "Test" or press Enter
- See how the system classifies it

---

## Features

### 📊 Real-Time Statistics

The header displays live metrics:
- **Total Queries**: 27 predefined test queries
- **Tested**: Number of queries tested so far
- **Correct**: Number of correct classifications
- **Accuracy**: Overall accuracy percentage

### 🎯 Query Categories

**Organized by Intent Type:**

1. **💬 Chitchat** (5 queries)
   - Greetings, small talk, emotional expressions
   - Example: "I'm feeling a bit stressed, just need to talk"

2. **📅 Scheduling** (6 queries)
   - Appointments, calendar operations, meeting management
   - Example: "Schedule a meeting with Sarah for next Tuesday at 2pm"

3. **📊 Information** (6 queries)
   - Factual lookups, general knowledge, status queries
   - Example: "What's the current weather in Seattle?"

4. **📝 Notes** (6 queries)
   - Creating lists, saving notes, viewing notes
   - Example: "Add to my shopping list: coffee and bananas"

5. **❓ Ambiguous / Edge Cases** (4 queries)
   - Queries that could belong to multiple categories
   - Example: "Remind me about the meeting"

### 📈 Result Display

For each tested query, the UI shows:

- **Query Text**: The full user message
- **Expected Category**: What category it should be classified as
- **Expected Intent**: The target intent (scheduling/information/notes/chitchat)
- **Classified As**: What the system actually classified it as
- **Classification Time**: How long it took (in milliseconds)
- **Match**: Whether classification was correct (✅/❌)
- **Agent Info**: Which agent would handle this query (ID and name)

### 🎨 Visual Feedback

- **Green buttons**: Correctly classified queries ✅
- **Red buttons**: Misclassified queries ❌
- **Purple gradient**: Selected query
- **Intent badges**: Color-coded by agent type
  - 🔵 Scheduling (blue)
  - 🟡 Information (yellow)
  - 🟢 Notes (green)
  - 🟣 Chitchat (purple)

---

## Test Queries

### Chitchat Queries (5)

1. "Hey, how's it going?"
2. "What do you think about the weather today?"
3. "I'm feeling a bit stressed, just need to talk"
4. "Tell me a joke!"
5. "Good morning! Ready for the weekend?"

### Scheduling Queries (6)

1. "Can you schedule a meeting with Sarah for next Tuesday at 2pm?"
2. "What's on my calendar for tomorrow?"
3. "I need to reschedule my 3pm appointment to Thursday"
4. "Block out 2 hours next week for project planning"
5. "Find a time slot for a team sync this week"
6. "Cancel my meeting on Friday afternoon"

### Information Queries (6)

1. "What's the current weather in Seattle?"
2. "Who won the NBA championship last year?"
3. "Look up the population of Tokyo"
4. "What are the symptoms of vitamin D deficiency?"
5. "Find me information about renewable energy trends"
6. "What's the exchange rate for USD to EUR?"

### Notes Queries (6)

1. "Save a note: Remember to buy groceries - milk, eggs, bread"
2. "Create a note about ideas for the quarterly presentation"
3. "Show me all my notes from last week"
4. "Find my note about the client meeting"
5. "Delete the note about vacation planning"
6. "Add to my shopping list: coffee and bananas"

### Ambiguous / Edge Case Queries (4)

1. "Remind me about the meeting" *(Could be scheduling or notes)*
2. "What time is it in London?" *(Information query)*
3. "I need help with something" *(Vague - likely chitchat)*
4. "Thanks for your help earlier!" *(Gratitude - chitchat)*

**Note**: Ambiguous queries have no fixed "correct" answer. The system routes them to the most appropriate agent based on context and keywords.

---

## Expected Results (v2.0)

Based on v2.0 improvements:

### Classification Accuracy Target
- **Non-Ambiguous Queries**: 100% (23/23 correct)
- **Overall (including edge cases)**: >95%

### Performance Targets
- **Classification Time**: <500ms per query
- **Batch Test Time**: <15 seconds for all 27 queries

### Agent Mapping

| Intent | Agent ID | Agent Name |
|--------|----------|------------|
| scheduling | TIGRBGSXCS | Scheduling Agent |
| information | JEK4SDJOOU | Information Agent |
| notes | CF0IPHCFFY | Notes Agent |
| chitchat | GXVZEOBQ64 | Chitchat Agent |

---

## Troubleshooting

### Issue: "Failed to classify query"

**Cause**: Backend server not running or not accessible

**Fix**:
```bash
# Check if backend is running
curl http://localhost:5001/api/health

# If not running, start it
cd frontend/backend
python3 app.py
```

### Issue: CORS Errors in Browser Console

**Cause**: Browser security restrictions

**Fix**: Use a local HTTP server instead of opening the file directly:
```bash
cd frontend
python3 -m http.server 8000
# Open: http://localhost:8000/test_ui.html
```

### Issue: Slow Classification

**Cause**: AWS Bedrock API latency or rate limiting

**Fix**:
- Wait a moment between tests
- Batch testing includes automatic 300ms delay between queries
- Check AWS CloudWatch for any throttling issues

### Issue: All Queries Classified as "chitchat"

**Cause**: Classification endpoint error (fallback behavior)

**Fix**:
1. Check backend logs for errors
2. Verify AWS credentials are configured
3. Ensure Bedrock model access is enabled
4. Check that Claude Haiku model is available in your region

---

## Technical Details

### Architecture

```
┌─────────────────┐
│  Test UI        │
│  (HTML/JS/CSS)  │
└────────┬────────┘
         │ HTTP POST
         │ /api/classify
         ▼
┌─────────────────┐
│  Flask Backend  │
│  (app.py)       │
└────────┬────────┘
         │ invoke_model
         │ (Claude Haiku)
         ▼
┌─────────────────┐
│  AWS Bedrock    │
│  Runtime API    │
└─────────────────┘
```

### API Endpoint

**POST** `/api/classify`

**Request:**
```json
{
  "message": "Schedule a meeting for tomorrow"
}
```

**Response:**
```json
{
  "intent": "scheduling",
  "agent_id": "TIGRBGSXCS",
  "agent_alias_id": "TSTALIASID",
  "classification_time_ms": 234.56,
  "timestamp": "2025-10-26T10:30:45.123456"
}
```

### Classification Logic

1. **User Query** → Test UI
2. **HTTP Request** → Flask `/api/classify` endpoint
3. **Classification** → Claude Haiku model via Bedrock
4. **Intent Determination** → scheduling/information/notes/chitchat
5. **Agent Mapping** → Select appropriate specialist agent
6. **Response** → Return intent + agent info + metrics

---

## Use Cases

### 1. Development Testing
Test individual queries during development to validate classification logic.

### 2. Regression Testing
Run batch tests after making changes to ensure no accuracy degradation.

### 3. Stakeholder Demos
Show live classification with 100% accuracy to executives and sponsors.

### 4. Edge Case Discovery
Test custom queries to find new edge cases and improve classification.

### 5. Performance Monitoring
Track classification times to ensure system meets performance targets.

### 6. Documentation
Generate screenshots for documentation and presentations.

---

## Screenshots

### Main Interface
- Left panel: All 27 test queries organized by category
- Right panel: Real-time classification results
- Header: Live statistics and accuracy metrics

### Batch Testing
- Progress bar showing test completion
- Final summary with overall accuracy
- Visual indicators for correct/incorrect classifications

### Custom Query Testing
- Text input for custom queries
- Instant classification results
- Agent routing information

---

## Next Steps

### After Testing

1. **Review Results**
   - Check accuracy percentage
   - Review any misclassified queries
   - Note classification times

2. **Document Findings**
   - Take screenshots of 100% accuracy
   - Save batch test results
   - Document any edge cases

3. **Share with Stakeholders**
   - Use for demos and presentations
   - Include in status reports
   - Show to CEO/CTO/Sponsor

4. **Optimize if Needed**
   - Update classification prompt for edge cases
   - Fine-tune agent selection logic
   - Improve performance if needed

---

## Production Deployment

### Before Production

- [ ] Test all 27 queries → 100% accuracy
- [ ] Test custom queries → Validate edge cases
- [ ] Monitor classification times → <500ms average
- [ ] Review agent mappings → Correct agent IDs
- [ ] Test with real customer data → Validate context

### Monitoring in Production

Once deployed, monitor:
- Classification accuracy (target: >98%)
- Average classification time (target: <500ms)
- Error rate (target: <1%)
- Agent distribution (balanced across intents)

---

## Files

### Main Files

| File | Purpose | Location |
|------|---------|----------|
| `test_ui.html` | Testing UI (HTML/CSS/JS) | `frontend/test_ui.html` |
| `app.py` | Flask backend with `/api/classify` | `frontend/backend/app.py` |
| `TEST_UI_README.md` | This documentation | `frontend/TEST_UI_README.md` |

### Related Files

| File | Purpose | Location |
|------|---------|----------|
| `test_results_table.py` | Command-line batch test | `tests/v2/test_results_table.py` |
| `test_improved_classification.py` | Edge case validation | `tests/v2/test_improved_classification.py` |
| `agent_config.json` | Agent configuration | `frontend/agent_config.json` |

---

## Support

### For Technical Questions
- Review Flask backend logs for errors
- Check AWS CloudWatch for Bedrock API issues
- Verify network connectivity to AWS

### For Classification Issues
- Review classification prompt in `app.py:213-256`
- Test with verbose logging enabled
- Check ROUTING_COMPARISON.md for routing logic

### For UI Issues
- Check browser console for JavaScript errors
- Verify CORS settings
- Ensure backend URL is correct (default: http://localhost:5001)

---

## Version History

### v2.0 (October 26, 2025)
- ✅ Initial release of testing UI
- ✅ Support for all 27 test queries
- ✅ Batch testing functionality
- ✅ Custom query testing
- ✅ Real-time metrics and statistics
- ✅ Visual feedback for correct/incorrect classifications
- ✅ Agent routing information display

---

## Summary

The Intent Classification Testing UI is a powerful tool for:

- **Validating** the v2.0 frontend routing system
- **Demonstrating** 100% classification accuracy
- **Testing** new queries and edge cases
- **Monitoring** performance and metrics
- **Presenting** results to stakeholders

**Target Accuracy**: 100% (23/23 non-ambiguous queries)
**Expected Performance**: <500ms per classification
**Status**: ✅ Ready for use

---

**Last Updated**: October 26, 2025
**Version**: 2.0
**Status**: Production Ready
