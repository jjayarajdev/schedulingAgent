# Postman Collection Updated - Weather-Only Information Agent

**Date:** November 9, 2025
**File:** `testing/ProjectForce_Agent_API.postman_collection.json`

---

## Summary of Changes

The Postman collection has been updated to reflect the new weather-only information agent with Open-Meteo integration.

### What Changed:

**Removed:**
- Generic "Invoke Agent - Information Query" test (which asked "What services do you offer?")

**Added - Non-Streaming Weather Tests (Section 3):**
1. ✅ **Weather - City Name (Tampa)** - Test with city name only
2. ✅ **Weather - City with State** - Test with "City, State" format (Minneapolis, MN)
3. ✅ **Weather - Zip Code** - Test with zip code (33601)
4. ✅ **Weather - Project Location Context** - Test context preservation from project details
5. ✅ **Weather - Rain Forecast** - Test specific weather conditions (rain)
6. ✅ **Weather - Out of Scope (Should Defer)** - Test that non-weather queries defer to scheduling agent

**Added - Streaming Weather Tests (Section 4):**
1. ✅ **Weather - City Name (Streaming)** - Test weather with streaming enabled (New York)

---

## Test Coverage

### Weather Queries Tested:

| Test Case | Query Type | Expected Behavior |
|-----------|------------|-------------------|
| City Name | "What's the weather in Tampa?" | Geocode city → Get weather via coordinates |
| City + State | "Check weather for Minneapolis, MN" | Geocode with state → More accurate results |
| Zip Code | "What's the weather in 33601?" | Geocode zip → Get weather |
| Project Context | "Show project details then weather" | Use project coordinates directly (BEST) |
| Specific Condition | "Is it going to rain in Miami tomorrow?" | Return precipitation forecast |
| Out of Scope | "What are your business hours?" | Defer to scheduling agent |

### API Integration Points:

**Open-Meteo Geocoding API:**
- Used when: City name or zip code provided
- Converts: Location string → Latitude/Longitude coordinates
- Example: "Tampa" → lat=27.9506, lon=-82.4572

**Open-Meteo Weather API:**
- Used for: All weather queries
- Returns: Current conditions + 3-day forecast
- Parameters: latitude, longitude, temperature_unit=fahrenheit
- Rate limit: 10,000 calls/day (free tier)

---

## How to Use

### 1. Import into Postman

```bash
# Open Postman → Import → File
testing/ProjectForce_Agent_API.postman_collection.json
```

### 2. Set Environment Variables

Either use the collection variables or create an environment:

| Variable | Value | Description |
|----------|-------|-------------|
| `proxy_url` | `http://localhost:5003` | Backend proxy URL |
| `access_token` | (auto-set by Login) | ProjectForce API token |
| `user_id` | `1646085` | Test user ID |
| `client_id` | `09PF05VD` | Test client ID |

### 3. Run Tests in Order

**Recommended test sequence:**

1. **Authentication:**
   - Run "Login" → saves access_token
   - Run "Validate Token" → confirms auth works

2. **Dashboard API:**
   - Run "Get Dashboard/Projects" → verify API access

3. **Agent Tests - Non-Streaming:**
   - Run "Show Projects" → test scheduling agent
   - Run "Greeting" → test chitchat agent
   - Run "Project Details" → test scheduling agent
   - Run all Weather tests → test information agent

4. **Agent Tests - Streaming:**
   - Run streaming tests to verify SSE works

---

## Weather Test Examples

### Test 1: City Name (Tampa)
```json
{
    "message": "What's the weather in Tampa?",
    "session_id": "test-weather-1234567890",
    "pf_token": "{{access_token}}",
    "pf_client_id": "{{client_id}}",
    "pf_user_id": "{{user_id}}",
    "stream": false
}
```

**Expected Response:**
- Agent routes to pf-information
- Information agent geocodes "Tampa" to coordinates
- Open-Meteo returns current weather + 3-day forecast
- Response includes: temp_f, condition, humidity, wind, precipitation

### Test 2: Project Context
```json
{
    "message": "Show me project 7751743 details and then tell me what's the weather there"
}
```

**Expected Flow:**
1. Supervisor routes to SchedulingAgent
2. SchedulingAgent calls get_project_details
3. Returns project with coordinates: `installation_address_latitude`, `installation_address_longitude`
4. User asks follow-up: "What's the weather there?"
5. Supervisor routes to pf-information
6. Information agent uses coordinates from project context (PREFERRED)
7. Returns weather for exact project location

### Test 3: Out of Scope
```json
{
    "message": "What are your business hours?"
}
```

**Expected Behavior:**
- Supervisor routes to pf-information (recognizes as information query)
- Information agent recognizes out-of-scope (business hours ≠ weather)
- Information agent responds: "I specialize in weather information only. For business hours, please ask the scheduling specialist."
- User can rephrase to scheduling agent

---

## Testing Tips

### ✅ Successful Weather Response Indicators:

1. **API Provider:** Response should show `"api_provider": "open-meteo"` (NOT wttr.in)
2. **Mock Mode:** Should show `"mock_mode": false` (using real API)
3. **Coordinates:** Should include `"latitude"` and `"longitude"` in response
4. **Forecast:** Should include 3-day forecast array with:
   - `date`, `max_temp_f`, `min_temp_f`, `condition`, `precipitation_probability`
5. **Current Weather:** Should include:
   - `temp_f`, `feels_like_f`, `condition`, `humidity`, `wind_mph`

### ❌ Error Scenarios to Test:

1. **Invalid Location:** "What's the weather in InvalidCityXYZ12345?"
   - Should return: "Unable to find location" error

2. **Missing Location:** "What's the weather?"
   - Should ask: "What location would you like to know about?"

3. **Ambiguous Location:** "What's the weather in Springfield?"
   - Should geocode to most prominent Springfield (likely MA or IL)

---

## Performance Expectations

| Metric | Target | Notes |
|--------|--------|-------|
| Response Time (with coordinates) | <150ms | Direct Open-Meteo call |
| Response Time (with city name) | <300ms | Includes geocoding step |
| Success Rate | >99% | Open-Meteo has 99.9% uptime |
| Rate Limit | 10,000/day | Free tier sufficient for testing |

---

## Streaming Tests

The streaming weather test uses Server-Sent Events (SSE) to stream the response in real-time.

**Note:** Postman has limited SSE support. For better streaming testing:

```bash
# Test streaming via curl
curl -X POST http://localhost:5003/api/invoke-agent \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is the weather in New York?",
    "session_id": "test-stream-123",
    "pf_token": "YOUR_TOKEN",
    "pf_client_id": "09PF05VD",
    "pf_user_id": "1646085",
    "stream": true
  }' \
  --no-buffer
```

Or use the test UI:
```bash
cd testing/ui
./launch_test_ui.sh
```

---

## Troubleshooting

### Issue: Weather data not returning

**Check:**
1. Lambda function updated? `aws lambda get-function --function-name pf-information-actions`
2. Agent instructions updated? Check agent version
3. Action group schema updated? Must include new parameters (latitude, longitude, location)
4. Open-Meteo API accessible? Test directly: https://api.open-meteo.com/v1/forecast?latitude=27.95&longitude=-82.45&current=temperature_2m

### Issue: Still using wttr.in

**Symptoms:**
- Response shows `"api_provider": "wttr.in"`
- Slow response times (>500ms)

**Fix:**
- Lambda code not updated
- Run deployment script again

### Issue: Geocoding fails

**Symptoms:**
- Error: "Unable to geocode location"

**Common causes:**
- City name too generic (use "City, State" format)
- Typo in city name
- Non-existent location

---

## Next Steps

After successful testing:

1. ✅ Verify all weather tests pass
2. ✅ Verify out-of-scope queries defer correctly
3. ✅ Monitor CloudWatch logs for errors
4. ✅ Check Open-Meteo usage (should be <100 calls/day for testing)
5. ✅ Test with real user projects and addresses

---

**Collection Version:** v2
**Last Updated:** November 9, 2025
**Status:** ✅ Ready for Testing
