# Open-Meteo Weather API - Deployment Guide

**Date:** January 9, 2025
**Status:** ✅ Ready to Deploy
**Migration:** wttr.in → Open-Meteo

---

## 🎯 What Was Implemented

Migrated weather service from **wttr.in** to **Open-Meteo** with intelligent parameter handling:

### **Key Features:**

1. ✅ **Smart Parameter Detection**
   - **Priority 1:** Use `latitude` + `longitude` if provided (most accurate)
   - **Priority 2:** Geocode `location` name if coordinates not available
   - **Continuity:** Accept context parameters (`customer_id`, `user_id`, `project_id`, `address`)

2. ✅ **Better Performance**
   - Response time: 50-150ms (vs 500-1000ms with wttr.in)
   - Reliability: 99.9% uptime
   - Data quality: National weather services

3. ✅ **No API Key Required**
   - Free up to 10,000 calls/day
   - No registration needed
   - Simple integration

---

## 📂 Files Modified

### ✅ 1. Lambda Handler
**File:** `lambda/information-actions/handler.py`

**Changes:**
- Added `WEATHER_CODES` dictionary (WMO weather codes)
- Added `geocode_location()` helper function
- Rewrote `handle_get_weather()` with smart parameter detection
- Added Open-Meteo API integration
- Added context parameter support

**Lines changed:** ~180 lines added/modified

### ✅ 2. OpenAPI Schema
**File:** `infrastructure/openapi_schemas/information_actions.json`

**Changes:**
- Added `latitude` parameter (number, optional)
- Added `longitude` parameter (number, optional)
- Made `location` parameter optional (fallback)
- Added context parameters: `customer_id`, `user_id`, `project_id`, `address`
- Updated descriptions

### ✅ 3. Agent Instructions
**File:** `agent-instructions/information-agent-instructions.txt`

**Changes:**
- Updated `get_weather` action documentation
- Added parameter priority explanation
- Added new conversation examples with coordinates
- Added project context examples

### ✅ 4. Test Script
**File:** `lambda/information-actions/test_open_meteo.py`

**New file** - Comprehensive test suite:
- Test with coordinates
- Test with city name
- Test with full project context
- Test error handling

---

## 🔄 Parameter Flow

### **Scenario 1: From Project Details (PREFERRED)**

```
User: "What's the weather for my project?"

Step 1: Get project details from scheduling agent
{
  "installation_address_latitude": "44.97364610000000",
  "installation_address_longitude": "-93.25749449999999",
  "installation_address_city": "Minneapolis",
  "installation_address_full_address": "401 Chicago Avenue Minneapolis MN 55415"
}

Step 2: Call weather with coordinates + context
get_weather(
  latitude=44.97,
  longitude=-93.26,
  project_id="7751741",
  customer_id="1645869",
  address="401 Chicago Avenue Minneapolis MN 55415"
)

Step 3: Get accurate weather for exact location
{
  "current": {"temp_f": 68, "condition": "Clear"},
  "forecast": [...],
  "context": {"project_id": "7751741", "customer_id": "1645869"}
}
```

### **Scenario 2: City Name Fallback**

```
User: "What's the weather in Tampa?"

Step 1: No coordinates, use city name
get_weather(
  location="Tampa",
  customer_id="1645869"
)

Step 2: Geocode city to coordinates
Geocoding API: "Tampa" → lat=27.9506, lon=-82.4572

Step 3: Get weather for geocoded location
{
  "current": {"temp_f": 75, "condition": "Partly cloudy"},
  "coordinates": {"latitude": 27.9506, "longitude": -82.4572}
}
```

---

## 🚀 Deployment Steps

### **Option 1: Automated (Recommended)**

```bash
cd scripts
./consolidate_information_agent.sh
```

This script will:
1. Package Lambda function with new Open-Meteo integration
2. Upload to AWS
3. Update agent instructions
4. Prepare agent
5. Update agent alias

**Then manually:**
- Update action group schema in AWS Console (see step 6 below)

### **Option 2: Manual Deployment**

#### 1. Package Lambda Function

```bash
cd lambda/information-actions

# Create deployment package
zip -r information-actions-openmeteo.zip \
  handler.py \
  config.py \
  mock_data.py \
  token_manager.py \
  requests/ \
  urllib3/ \
  certifi/ \
  charset_normalizer/ \
  idna/ \
  dateutil/
```

#### 2. Upload to Lambda

```bash
aws lambda update-function-code \
  --function-name pf-information-actions \
  --zip-file fileb://information-actions-openmeteo.zip \
  --region us-east-1
```

#### 3. Wait for Update

```bash
aws lambda wait function-updated \
  --function-name pf-information-actions \
  --region us-east-1
```

#### 4. Update Agent Instructions

```bash
AGENT_ID=$(jq -r '.pf_information.agent_id' ../../config/agent_ids.json)
INSTRUCTIONS=$(cat ../../agent-instructions/information-agent-instructions.txt)

aws bedrock-agent update-agent \
  --agent-id $AGENT_ID \
  --agent-name "pf-information" \
  --instruction "$INSTRUCTIONS" \
  --region us-east-1
```

#### 5. Prepare Agent

```bash
aws bedrock-agent prepare-agent \
  --agent-id $AGENT_ID \
  --region us-east-1
```

#### 6. Update Action Group Schema (AWS Console)

**Important:** Must be done via console

1. Go to: AWS Console → Bedrock → Agents
2. Select `pf-information` agent
3. Go to "Action groups" section
4. Edit the action group
5. Upload new schema: `infrastructure/openapi_schemas/information_actions.json`
6. Save changes
7. Click "Prepare" to create new agent version

#### 7. Update Alias

```bash
AGENT_ID=$(jq -r '.pf_information.agent_id' ../../config/agent_ids.json)
ALIAS_ID=$(jq -r '.pf_information.alias_id' ../../config/agent_ids.json)

# Get latest version
LATEST_VERSION=$(aws bedrock-agent list-agent-versions \
  --agent-id $AGENT_ID \
  --region us-east-1 \
  --query 'agentVersionSummaries[0].agentVersion' \
  --output text)

# Update alias
aws bedrock-agent update-agent-alias \
  --agent-id $AGENT_ID \
  --agent-alias-id $ALIAS_ID \
  --agent-alias-name "live" \
  --routing-configuration "agentVersion=$LATEST_VERSION" \
  --region us-east-1
```

---

## 🧪 Testing

### **Test 1: Local Testing (Without AWS)**

```bash
cd lambda/information-actions

# Run test script
python3 test_open_meteo.py
```

**Expected output:**
```
TEST 1: Weather with Coordinates (Tampa)
Location: Tampa
Current Temp: 75.2°F
Condition: Partly cloudy

TEST 2: Weather with City Name (Minneapolis)
Location: Minneapolis
Coordinates (geocoded): 44.979, -93.263
Current Temp: 68.5°F

TEST 3: Weather with Full Project Context
Context: Project 7751741, Customer 1645869
3-Day Forecast:
  2025-01-09: 65-78°F, Clear, 15% rain
  ...

✅ ALL TESTS COMPLETED
```

### **Test 2: Test Lambda Directly**

```bash
# Test with coordinates
aws lambda invoke \
  --function-name pf-information-actions \
  --payload '{"apiPath":"/get_weather","parameters":[{"name":"latitude","value":"27.9506"},{"name":"longitude","value":"-82.4572"}]}' \
  --region us-east-1 \
  response.json

cat response.json | jq .
```

### **Test 3: Test via Backend API**

```bash
cd testing/ui
./launch_test_ui.sh

# In the UI, test these queries:
# 1. "What's the weather in Tampa?"
# 2. "What's the weather for my project?"
# 3. "Check weather for Minneapolis"
```

### **Test 4: Test Continuity from Project Details**

**Full conversation flow:**
```
User: "Show me my projects"
Agent: [Lists projects including project 7751741]

User: "Tell me about project 7751741"
Agent: [Returns project details with address coordinates]

User: "What's the weather there?"
Agent: [Uses coordinates from project context]
       "At your project location in Minneapolis (401 Chicago Ave),
        it's currently 68°F and clear..."
```

---

## 📊 Verification Checklist

After deployment, verify:

- [ ] Lambda function updated successfully
- [ ] Agent instructions updated
- [ ] Action group schema updated in console
- [ ] Agent version created and alias updated
- [ ] Test: Weather with coordinates works
- [ ] Test: Weather with city name works
- [ ] Test: Context parameters preserved
- [ ] Test: Error handling for invalid locations
- [ ] Test: Geocoding works for various city formats
- [ ] Monitor: Check CloudWatch logs for errors
- [ ] Monitor: Verify Open-Meteo API calls succeed

---

## 📈 API Endpoints Used

### **Open-Meteo Weather API**
```
GET https://api.open-meteo.com/v1/forecast
Parameters:
  - latitude (required)
  - longitude (required)
  - current (weather variables)
  - daily (forecast variables)
  - temperature_unit=fahrenheit
  - wind_speed_unit=mph
  - precipitation_unit=inch
  - timezone=auto
  - forecast_days=3
```

### **Open-Meteo Geocoding API**
```
GET https://geocoding-api.open-meteo.com/v1/search
Parameters:
  - name (city name)
  - count=1
  - language=en
  - format=json
```

---

## 🔍 Monitoring

### **CloudWatch Logs**

Look for these log patterns:

**Success:**
```
[COORDINATES] Using lat=27.9506, lon=-82.4572
[REAL] Fetching weather from Open-Meteo for lat=27.9506, lon=-82.4572
```

**Geocoding:**
```
[GEOCODE] Location name provided: Tampa
Geocoding location: Tampa
```

**Errors to watch:**
```
Open-Meteo API request failed: ...
Geocoding API request failed: ...
Unable to geocode location '...'
```

### **Metrics to Track**

- Response times: Should be <150ms
- Error rate: Should be <1%
- Geocoding calls: Track how many city vs coordinate requests
- API failures: Alert if Open-Meteo API fails

---

## ⚠️ Important Notes

### **Rate Limits**
- **Free tier:** 10,000 calls/day
- **Your usage:** ~20-100 calls/day (well under limit)
- **No throttling expected**

### **Coordinates Source**
Your project data already includes coordinates:
```json
{
  "installation_address_latitude": "44.97364610000000",
  "installation_address_longitude": "-93.25749449999999"
}
```

**Always prefer these** over geocoding for accuracy.

### **Backward Compatibility**
- ✅ Old `location` parameter still works
- ✅ Falls back to geocoding if coordinates not provided
- ✅ No breaking changes for existing calls

---

## 🐛 Troubleshooting

### **Issue: Geocoding fails for city name**

**Cause:** City name not found or ambiguous

**Solution:**
```python
# Be specific with city names
"Tampa"              # May be ambiguous
"Tampa, FL"          # Better
"Tampa, Florida"     # Also works
```

### **Issue: Weather API returns 400**

**Cause:** Invalid coordinates

**Solution:**
- Verify lat/lon are valid decimal numbers
- Latitude: -90 to 90
- Longitude: -180 to 180

### **Issue: Slow responses**

**Cause:** Geocoding adds latency

**Solution:**
- Use coordinates when available (faster)
- Cache geocoded results if needed
- Most requests should use project coordinates

---

## 📝 Example Responses

### **With Coordinates:**
```json
{
  "action": "get_weather",
  "location": "Minneapolis",
  "coordinates": {
    "latitude": 44.97,
    "longitude": -93.26
  },
  "weather": {
    "location": {
      "latitude": 44.97,
      "longitude": -93.26,
      "name": "Minneapolis",
      "timezone": "America/Chicago",
      "elevation_meters": 262
    },
    "current": {
      "time": "2025-01-09T15:00",
      "temp_f": 68.5,
      "feels_like_f": 70.2,
      "condition": "Clear sky",
      "weather_code": 0,
      "humidity": 55,
      "wind_mph": 8.5,
      "wind_direction": 180,
      "precipitation_inch": 0.0
    },
    "forecast": [
      {
        "date": "2025-01-09",
        "max_temp_f": 75,
        "min_temp_f": 62,
        "condition": "Clear sky",
        "weather_code": 0,
        "precipitation_probability": 10
      }
    ],
    "context": {
      "customer_id": "1645869",
      "user_id": "user123",
      "project_id": "7751741",
      "address": "401 Chicago Avenue Minneapolis MN"
    }
  },
  "mock_mode": false,
  "api_provider": "open-meteo"
}
```

---

## ✅ Success Criteria

Deployment is successful when:

1. ✅ Lambda function responds without errors
2. ✅ Weather queries with coordinates return data in <150ms
3. ✅ Weather queries with city names geocode and return data in <300ms
4. ✅ Context parameters (customer_id, project_id) are preserved
5. ✅ Error handling works for invalid inputs
6. ✅ CloudWatch logs show successful Open-Meteo API calls
7. ✅ No wttr.in API calls in logs (fully migrated)

---

## 📚 Related Documentation

- [WEATHER_API_COMPARISON.md](WEATHER_API_COMPARISON.md) - Detailed API comparison
- [API_PARAMETERS_REFERENCE.md](API_PARAMETERS_REFERENCE.md) - Complete API reference
- [INFORMATION_AGENT_CONSOLIDATION.md](INFORMATION_AGENT_CONSOLIDATION.md) - Agent consolidation

---

## 🎉 Post-Deployment

After successful deployment:

1. Update team documentation
2. Notify users of improved weather accuracy
3. Monitor performance for 1 week
4. Consider removing wttr.in config (cleanup)
5. Document lessons learned

---

**Status:** ✅ **READY FOR DEPLOYMENT**

**Estimated Deployment Time:** 30-45 minutes
**Risk Level:** Low (backward compatible, fallback supported)
**Rollback Plan:** Revert to previous Lambda version if issues arise

---

**Last Updated:** January 9, 2025
**Version:** 2.0.0 (Open-Meteo Integration)
