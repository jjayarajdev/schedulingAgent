# Bulk Scheduling & Coordinator Operations - Design Document

**Version:** 1.0
**Date:** October 13, 2025
**Status:** Design Complete - Ready for Implementation
**Phase:** Phase 1 Enhancement - Coordinator Features

---

## Executive Summary

This document details the design for **bulk scheduling operations** that enable coordinators to:
1. **Route optimization** - Process 10-50 projects and generate optimized technician routes
2. **Bulk team assignments** - Assign multiple projects to teams with conflict detection
3. **Project validation** - Validate permits, measurements, and scheduling conflicts in bulk

### Key Benefits

| Feature | Benefit | Time Savings |
|---------|---------|--------------|
| **Route Optimization** | Optimize 50 projects at once | 2 hours → 30 seconds |
| **Bulk Assignment** | Assign 30 projects simultaneously | 1.5 hours → 2 minutes |
| **Batch Validation** | Check 100 projects for conflicts | 3 hours → 5 minutes |

**Total coordinator time savings:** ~80% for bulk operations

---

## Architecture Overview

### Current Architecture (Phase 1 + 2)

```
Customer → Chat/SMS → Bedrock Agent → 4 Collaborators (1-to-1 operations)
                              ↓
                        Single appointment operations
```

### Enhanced Architecture (with Bulk Operations)

```
Coordinator → Chat/API → Bedrock Supervisor → Coordinator Collaborator
                                                        ↓
                                              Bulk Operations Handler
                                                        ↓
                            ┌──────────────┬────────────────┬─────────────────┐
                            ↓              ↓                ↓                 ↓
                    Route Optimizer   Bulk Assigner   Validator   Conflict Detector
                            ↓              ↓                ↓                 ↓
                            └──────────────┴────────────────┴─────────────────┘
                                                        ↓
                                              PF360 API (batch operations)
                                                        ↓
                                              Response aggregator
                                                        ↓
                                              Coordinator (formatted results)
```

---

## Use Cases

### Use Case 1: Route Optimization

**Actor:** Field Coordinator
**Goal:** Generate optimal route for 30 projects scheduled for tomorrow

**Input:**
```
Coordinator: "Optimize route for tomorrow's projects in Tampa"
Agent: "I found 32 projects scheduled for Tampa tomorrow. Processing..."

[Agent processes 32 project IDs through route optimizer]

Agent: "Route optimized! Here's the sequence:
- Start: 8:00 AM - Project #12345 (123 Main St) - ETA: 45 min
- Next: 9:15 AM - Project #12347 (456 Oak Ave) - ETA: 30 min
- Next: 10:00 AM - Project #12350 (789 Pine Rd) - ETA: 1 hr
...
Total drive time: 3.2 hours (saved 1.8 hours vs unoptimized)
Would you like me to update the schedule?"
```

**Alternative - Paste Project IDs:**
```
Coordinator: "Optimize these projects: 12345, 12347, 12350, 12352, 12355"
Agent: "Processing 5 projects... Route optimized!"
```

### Use Case 2: Bulk Team Assignment

**Actor:** Operations Manager
**Goal:** Assign 20 new projects to Team A for next week

**Input:**
```
Coordinator: "Assign projects 15001-15020 to Team A for next week"
Agent: "Checking availability for Team A next week..."

[Checks conflicts, availability, skills, certifications]

Agent: "Analysis complete:
✅ Can assign: 18 projects (no conflicts)
⚠️ Conflicts found: 2 projects
  - #15005: Team A on vacation Oct 20
  - #15012: Missing required permit

Shall I proceed with assigning the 18 projects?"

Coordinator: "Yes, proceed"
Agent: "Assigned 18 projects to Team A. Would you like me to suggest alternatives for the 2 conflicted projects?"
```

### Use Case 3: Project Validation

**Actor:** Quality Coordinator
**Goal:** Validate 50 projects before scheduling

**Input:**
```
Coordinator: "Validate all projects in queue for permit compliance"
Agent: "Found 47 projects in queue. Running validation..."

[Checks: permits, measurements, access, conflicts]

Agent: "Validation complete:
✅ Ready: 42 projects (89%)
⚠️ Issues: 5 projects (11%)

Issues breakdown:
- Missing permits: 3 projects (#10001, #10005, #10012)
- Measurement incomplete: 1 project (#10008)
- Access restrictions: 1 project (#10015)

Would you like details on the issues?"
```

---

## Technical Design

### Component Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Bedrock Supervisor Agent                     │
│                                                                  │
│  Routes coordinator requests to → Coordinator Collaborator      │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│              Coordinator Collaborator Agent                     │
│                                                                  │
│  Detects bulk operation intent and routes to action groups:    │
│  • optimize_route                                               │
│  • bulk_assign_teams                                            │
│  • validate_projects                                            │
│  • detect_conflicts                                             │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│                  Lambda: Bulk Operations Handler                │
│                                                                  │
│  Orchestrates bulk operations:                                  │
│  1. Parse input (project IDs, date range, team, etc.)          │
│  2. Fetch data from PF360 API (parallel requests)              │
│  3. Process through specialized handlers                        │
│  4. Aggregate results                                           │
│  5. Return formatted response                                   │
└──────────────────────────────┬──────────────────────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        ↓                      ↓                      ↓
┌──────────────┐    ┌──────────────────┐    ┌───────────────────┐
│ Route        │    │ Bulk Assignment  │    │ Validation        │
│ Optimizer    │    │ Engine           │    │ Engine            │
│              │    │                  │    │                   │
│ - TSP solver │    │ - Conflict check │    │ - Permit check    │
│ - Google API │    │ - Skill match    │    │ - Measurement     │
│ - ETA calc   │    │ - Load balance   │    │ - Access check    │
└──────────────┘    └──────────────────┘    └───────────────────┘
        │                      │                      │
        └──────────────────────┴──────────────────────┘
                               │
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│                      PF360 API Gateway                          │
│                                                                  │
│  Batch endpoints:                                               │
│  • GET /projects/batch?ids=1,2,3...                            │
│  • POST /assignments/bulk                                       │
│  • POST /validation/batch                                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Models

### Bulk Operation Request

```typescript
interface BulkOperationRequest {
  operation_type: 'route_optimize' | 'bulk_assign' | 'validate';
  project_ids?: string[];          // Explicit project IDs
  filters?: {
    date_range?: [string, string]; // ISO dates
    region?: string;               // e.g., "Tampa"
    status?: string[];             // e.g., ["pending", "scheduled"]
    team?: string;                 // Team name/ID
  };
  options?: {
    max_projects?: number;         // Limit (default: 50)
    ignore_conflicts?: boolean;    // Force assignment
    optimize_for?: 'time' | 'distance' | 'cost';
  };
}
```

### Route Optimization Response

```typescript
interface RouteOptimizationResult {
  operation: 'route_optimize';
  project_count: number;
  optimized_route: RouteStop[];
  metrics: {
    total_distance_miles: number;
    total_drive_time_minutes: number;
    time_saved_minutes: number;
    savings_percentage: number;
  };
  warnings?: string[];
}

interface RouteStop {
  sequence: number;
  project_id: string;
  address: string;
  arrival_time: string;           // ISO datetime
  duration_minutes: number;
  drive_time_to_next_minutes: number;
  coordinates: [number, number];  // [lat, lng]
}
```

### Bulk Assignment Response

```typescript
interface BulkAssignmentResult {
  operation: 'bulk_assign';
  requested_count: number;
  successful: number;
  failed: number;
  assignments: Assignment[];
  conflicts: Conflict[];
  summary: {
    team: string;
    assigned_projects: string[];
    total_hours_allocated: number;
  };
}

interface Assignment {
  project_id: string;
  team: string;
  scheduled_date: string;
  estimated_hours: number;
  status: 'assigned' | 'failed';
}

interface Conflict {
  project_id: string;
  reason: string;
  severity: 'warning' | 'error';
  suggested_resolution?: string;
}
```

### Validation Response

```typescript
interface ValidationResult {
  operation: 'validate';
  total_projects: number;
  valid_count: number;
  issues_count: number;
  projects: ProjectValidation[];
  summary: {
    ready_to_schedule: string[];
    requires_action: string[];
    blocked: string[];
  };
}

interface ProjectValidation {
  project_id: string;
  is_valid: boolean;
  checks: {
    permit_valid: boolean;
    measurements_complete: boolean;
    access_approved: boolean;
    no_conflicts: boolean;
  };
  issues: ValidationIssue[];
}

interface ValidationIssue {
  type: 'permit' | 'measurement' | 'access' | 'conflict';
  severity: 'warning' | 'error' | 'blocking';
  message: string;
  resolution_steps?: string[];
}
```

---

## API Specifications

### Action Group: Coordinator Operations

**OpenAPI Schema:** `coordinator_actions.json`

```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "Coordinator Operations API",
    "version": "1.0.0"
  },
  "paths": {
    "/optimize_route": {
      "post": {
        "operationId": "optimize_route",
        "summary": "Optimize route for multiple projects",
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "properties": {
                  "project_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of project IDs to optimize",
                    "minItems": 2,
                    "maxItems": 50
                  },
                  "date": {
                    "type": "string",
                    "format": "date",
                    "description": "Target date for route"
                  },
                  "optimize_for": {
                    "type": "string",
                    "enum": ["time", "distance", "cost"],
                    "default": "time"
                  }
                },
                "required": ["project_ids"]
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Optimized route",
            "content": {
              "application/json": {
                "schema": {"$ref": "#/components/schemas/RouteOptimizationResult"}
              }
            }
          }
        }
      }
    },
    "/bulk_assign": {
      "post": {
        "operationId": "bulk_assign_teams",
        "summary": "Assign multiple projects to a team",
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "properties": {
                  "project_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                    "maxItems": 100
                  },
                  "team": {
                    "type": "string",
                    "description": "Team ID or name"
                  },
                  "date_range": {
                    "type": "array",
                    "items": {"type": "string", "format": "date"},
                    "minItems": 2,
                    "maxItems": 2,
                    "description": "Start and end dates"
                  },
                  "ignore_conflicts": {
                    "type": "boolean",
                    "default": false
                  }
                },
                "required": ["project_ids", "team"]
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Bulk assignment result",
            "content": {
              "application/json": {
                "schema": {"$ref": "#/components/schemas/BulkAssignmentResult"}
              }
            }
          }
        }
      }
    },
    "/validate_projects": {
      "post": {
        "operationId": "validate_projects",
        "summary": "Validate multiple projects for scheduling",
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "properties": {
                  "project_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                    "maxItems": 100
                  },
                  "validation_checks": {
                    "type": "array",
                    "items": {
                      "type": "string",
                      "enum": ["permit", "measurement", "access", "conflicts"]
                    },
                    "default": ["permit", "measurement", "access", "conflicts"]
                  }
                },
                "required": ["project_ids"]
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Validation result",
            "content": {
              "application/json": {
                "schema": {"$ref": "#/components/schemas/ValidationResult"}
              }
            }
          }
        }
      }
    },
    "/detect_conflicts": {
      "post": {
        "operationId": "detect_conflicts",
        "summary": "Detect scheduling conflicts for projects",
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "properties": {
                  "project_ids": {
                    "type": "array",
                    "items": {"type": "string"}
                  },
                  "team": {
                    "type": "string",
                    "description": "Check conflicts for specific team"
                  },
                  "date_range": {
                    "type": "array",
                    "items": {"type": "string", "format": "date"},
                    "minItems": 2,
                    "maxItems": 2
                  }
                },
                "required": ["project_ids"]
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Conflict detection result",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "conflicts_found": {"type": "integer"},
                    "conflicts": {
                      "type": "array",
                      "items": {"$ref": "#/components/schemas/Conflict"}
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  },
  "components": {
    "schemas": {
      "RouteOptimizationResult": {},
      "BulkAssignmentResult": {},
      "ValidationResult": {},
      "Conflict": {}
    }
  }
}
```

---

## Implementation Plan

### Phase 1: Foundation (Week 1)

**Tasks:**
1. Create coordinator collaborator agent
2. Define OpenAPI schema for 4 action groups
3. Set up DynamoDB table for bulk operation tracking
4. Create Lambda skeleton for bulk operations handler

**Deliverables:**
- Coordinator agent configured in Bedrock
- OpenAPI schema deployed to S3
- Lambda function created

### Phase 2: Route Optimization (Week 2)

**Tasks:**
1. Implement TSP (Traveling Salesman Problem) solver
2. Integrate Google Maps Distance Matrix API
3. Build route optimization logic
4. Add ETA calculations
5. Test with 10, 25, 50 projects

**Deliverables:**
- Working route optimizer
- Unit tests (>80% coverage)
- Integration tests with PF360 API

### Phase 3: Bulk Assignment (Week 3)

**Tasks:**
1. Implement conflict detection engine
2. Build skill matching logic
3. Add load balancing algorithm
4. Create bulk assignment API
5. Test with various scenarios

**Deliverables:**
- Bulk assignment engine
- Conflict detection working
- Test suite with edge cases

### Phase 4: Validation Engine (Week 4)

**Tasks:**
1. Implement permit validation
2. Add measurement completeness check
3. Build access approval verification
4. Create comprehensive validator
5. Test with real project data

**Deliverables:**
- Validation engine
- Validation rules configurable
- Test coverage >85%

### Phase 5: Integration & Testing (Week 5)

**Tasks:**
1. Integrate all components
2. End-to-end testing
3. Performance optimization
4. Documentation
5. Coordinator training

**Deliverables:**
- Production-ready bulk operations
- Performance benchmarks
- Coordinator training materials

---

## Continued in next message...
