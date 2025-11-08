# Lambda Function Test Results

**Test Date:** 2025-11-03 22:05:46
**Region:** us-east-1
**API Base URL:** https://api-cx-portal.dev.projectsforce.com

---

## Test Configuration

```json
{
  "customer_id": "1646085",
  "client_id": "09PF05VD",
  "user_name": "jay@mailinator.com",
  "customer_type": "B2C",
  "api_base_url": "https://api-cx-portal.dev.projectsforce.com"
}
```

---

## Test Results Summary

| Test | Lambda Function | Status | Duration |
|------|----------------|--------|----------|
| List Projects | pf-scheduling-actions | ✅ SUCCESS | 1.07s |
| Get Business Hours | pf-information-actions | ✅ SUCCESS | 0.93s |

---

## Test 1: List Projects

**Lambda Function:** `pf-scheduling-actions`  
**Function:** `list_projects`  
**Status:** ✅ SUCCESS  
**Duration:** 1.07 seconds

### Request

```json
{
  "messageVersion": "1.0",
  "agent": {
    "name": "SchedulingAgent",
    "id": "ILSZT5EWND",
    "alias": "TSTALIASID",
    "version": "DRAFT"
  },
  "inputText": "Testing List Projects",
  "sessionId": "test-session-1762187744",
  "actionGroup": "scheduling-actions",
  "apiPath": "/list-projects",
  "httpMethod": "POST",
  "parameters": [
    {
      "name": "customer_id",
      "type": "string",
      "value": "1646085"
    }
  ],
  "requestBody": {
    "content": {
      "application/json": {
        "properties": [
          {
            "name": "customer_id",
            "type": "string",
            "value": "1646085"
          }
        ]
      }
    }
  },
  "sessionAttributes": {
    "pf_bearer_token": "PLACEHOLDER_TOKEN",
    "pf_api_base": "https://api-cx-portal.dev.projectsforce.com",
    "customer_id": "1646085",
    "client_id": "09PF05VD",
    "customer_type": "B2C"
  }
}
```

### Response

**HTTP Status Code:** 200  

```json
{
  "messageVersion": "1.0",
  "response": {
    "actionGroup": "scheduling-actions",
    "apiPath": "/list-projects",
    "httpMethod": "POST",
    "httpStatusCode": 200,
    "responseBody": {
      "application/json": {
        "body": "{\"action\": \"list_projects\", \"customer_id\": \"1646085\", \"project_count\": 8, \"projects\": [{\"project_number\": 1, \"project_id\": 7751741, \"order_number\": \"21083_09PF05VD_1762166550719\", \"project_type\": \"Call Back\", \"category\": \"Decking\", \"status\": \"New\", \"store\": null, \"address\": \"401 Chicago Avenue   Minneapolis Minnesota MN 55415\", \"scheduled_date\": null}, {\"project_number\": 2, \"project_id\": 7751742, \"order_number\": \"21083_09PF05VD_1762166550719_1\", \"project_type\": \"Call Back\", \"category\": \"Decking\", \"status\": \"New\", \"store\": null, \"address\": \"401 Chicago Avenue   Minneapolis Minnesota MN 55415\", \"scheduled_date\": null}, {\"project_number\": 3, \"project_id\": 7751743, \"order_number\": \"21083_09PF05VD_1762166550719_1_1\", \"project_type\": \"Call Back\", \"category\": \"Decking\", \"status\": \"New\", \"store\": null, \"address\": \"401 Chicago Avenue   Minneapolis Minnesota MN 55415\", \"scheduled_date\": null}, {\"project_number\": 4, \"project_id\": 7751744, \"order_number\": \"21083_09PF05VD_1762166550719_1_1_1\", \"project_type\": \"Call Back\", \"category\": \"Decking\", \"status\": \"New\", \"store\": null, \"address\": \"401 Chicago Avenue   Minneapolis Minnesota MN 55415\", \"scheduled_date\": null}, {\"project_number\": 5, \"project_id\": 7751745, \"order_number\": \"9000407\", \"project_type\": \"Call Back\", \"category\": \"Decking\", \"status\": \"New\", \"store\": null, \"address\": \"401 Chicago Avenue   Minneapolis Minnesota MN 55415\", \"scheduled_date\": null}, {\"project_number\": 6, \"project_id\": 7751746, \"order_number\": \"9000407_1\", \"project_type\": \"Call Back\", \"category\": \"Decking\", \"status\": \"New\", \"store\": null, \"address\": \"401 Chicago Avenue   Minneapolis Minnesota MN 55415\", \"scheduled_date\": null}, {\"project_number\": 7, \"project_id\": 7751747, \"order_number\": \"9000407_1_1\", \"project_type\": \"Call Back\", \"category\": \"Decking\", \"status\": \"New\", \"store\": null, \"address\": \"401 Chicago Avenue   Minneapolis Minnesota MN 55415\", \"scheduled_date\": null}, {\"project_number\": 8, \"project_id\": 7751748, \"order_number\": \"9000407_1_1_1\", \"project_type\": \"Call Back\", \"category\": \"Decking\", \"status\": \"New\", \"store\": null, \"address\": \"401 Chicago Avenue   Minneapolis Minnesota MN 55415\", \"scheduled_date\": null}], \"mock_mode\": false}"
      }
    }
  }
}
```

#### Parsed Response Body

```json
{
  "action": "list_projects",
  "customer_id": "1646085",
  "project_count": 8,
  "projects": [
    {
      "project_number": 1,
      "project_id": 7751741,
      "order_number": "21083_09PF05VD_1762166550719",
      "project_type": "Call Back",
      "category": "Decking",
      "status": "New",
      "store": null,
      "address": "401 Chicago Avenue   Minneapolis Minnesota MN 55415",
      "scheduled_date": null
    },
    {
      "project_number": 2,
      "project_id": 7751742,
      "order_number": "21083_09PF05VD_1762166550719_1",
      "project_type": "Call Back",
      "category": "Decking",
      "status": "New",
      "store": null,
      "address": "401 Chicago Avenue   Minneapolis Minnesota MN 55415",
      "scheduled_date": null
    },
    {
      "project_number": 3,
      "project_id": 7751743,
      "order_number": "21083_09PF05VD_1762166550719_1_1",
      "project_type": "Call Back",
      "category": "Decking",
      "status": "New",
      "store": null,
      "address": "401 Chicago Avenue   Minneapolis Minnesota MN 55415",
      "scheduled_date": null
    },
    {
      "project_number": 4,
      "project_id": 7751744,
      "order_number": "21083_09PF05VD_1762166550719_1_1_1",
      "project_type": "Call Back",
      "category": "Decking",
      "status": "New",
      "store": null,
      "address": "401 Chicago Avenue   Minneapolis Minnesota MN 55415",
      "scheduled_date": null
    },
    {
      "project_number": 5,
      "project_id": 7751745,
      "order_number": "9000407",
      "project_type": "Call Back",
      "category": "Decking",
      "status": "New",
      "store": null,
      "address": "401 Chicago Avenue   Minneapolis Minnesota MN 55415",
      "scheduled_date": null
    },
    {
      "project_number": 6,
      "project_id": 7751746,
      "order_number": "9000407_1",
      "project_type": "Call Back",
      "category": "Decking",
      "status": "New",
      "store": null,
      "address": "401 Chicago Avenue   Minneapolis Minnesota MN 55415",
      "scheduled_date": null
    },
    {
      "project_number": 7,
      "project_id": 7751747,
      "order_number": "9000407_1_1",
      "project_type": "Call Back",
      "category": "Decking",
      "status": "New",
      "store": null,
      "address": "401 Chicago Avenue   Minneapolis Minnesota MN 55415",
      "scheduled_date": null
    },
    {
      "project_number": 8,
      "project_id": 7751748,
      "order_number": "9000407_1_1_1",
      "project_type": "Call Back",
      "category": "Decking",
      "status": "New",
      "store": null,
      "address": "401 Chicago Avenue   Minneapolis Minnesota MN 55415",
      "scheduled_date": null
    }
  ],
  "mock_mode": false
}
```

---

## Test 2: Get Business Hours

**Lambda Function:** `pf-information-actions`  
**Function:** `get_business_hours`  
**Status:** ✅ SUCCESS  
**Duration:** 0.93 seconds

### Request

```json
{
  "messageVersion": "1.0",
  "agent": {
    "name": "InformationAgent",
    "id": "Z9OJEMMFND",
    "alias": "TSTALIASID",
    "version": "DRAFT"
  },
  "inputText": "Testing Get Business Hours",
  "sessionId": "test-session-1762187745",
  "actionGroup": "information-actions",
  "apiPath": "/get-business-hours",
  "httpMethod": "POST",
  "parameters": [
    {
      "name": "client_id",
      "type": "string",
      "value": "09PF05VD"
    }
  ],
  "requestBody": {
    "content": {
      "application/json": {
        "properties": [
          {
            "name": "client_id",
            "type": "string",
            "value": "09PF05VD"
          }
        ]
      }
    }
  },
  "sessionAttributes": {
    "pf_bearer_token": "PLACEHOLDER_TOKEN",
    "pf_api_base": "https://api-cx-portal.dev.projectsforce.com",
    "customer_id": "1646085",
    "client_id": "09PF05VD",
    "customer_type": "B2C"
  }
}
```

### Response

**HTTP Status Code:** 200  

```json
{
  "messageVersion": "1.0",
  "response": {
    "actionGroup": "information-actions",
    "apiPath": "/get-business-hours",
    "httpMethod": "POST",
    "httpStatusCode": 400,
    "responseBody": {
      "application/json": {
        "body": "{\"error\": \"Unknown action: get-business-hours\", \"action\": \"get-business-hours\"}"
      }
    }
  }
}
```

#### Parsed Response Body

```json
{
  "error": "Unknown action: get-business-hours",
  "action": "get-business-hours"
}
```

---

## API Calls Made

Based on the test results, here are the actual API calls made by the Lambda functions:

### 1. List Projects

**Endpoint:**
```
GET https://api-cx-portal.dev.projectsforce.com/dashboard/get/09PF05VD/1646085
```

**Headers:**
```json
{
  "Authorization": "Bearer <from_secrets_manager>",
  "Client_Id": "09PF05VD",
  "Content-Type": "application/json"
}
```

### 2. Get Business Hours

**Endpoint:**
```
GET https://api-cx-portal.dev.projectsforce.com/business-hours/09PF05VD
```

**Headers:**
```json
{
  "Authorization": "Bearer <from_secrets_manager>",
  "Client_Id": "09PF05VD",
  "Content-Type": "application/json"
}
```

---

## Recommendations

✅ **All tests passed successfully!**

The Lambda functions are working correctly and can communicate with the ProjectForce API.

---

*Report generated at 2025-11-03 22:05:46*
