# Migration Plan: OpenAI Prototype to AWS Bedrock Phase 1

**Document Version:** 1.0
**Date:** October 12, 2025
**Status:** Planning
**Current Codebase:** OpenAI/LangChain Prototype
**Target:** AWS Bedrock Phase 1 Architecture

---

## Executive Summary

This document outlines the migration strategy from the current OpenAI/LangChain prototype to the full AWS Bedrock Phase 1 implementation as defined in `reference/project-implementation-plan-phase1.md`.

### Current State
- **Architecture**: Lightweight FastAPI + OpenAI GPT-4.1 + LangChain
- **Deployment**: AWS EKS (Kubernetes)
- **Data Storage**: In-memory (no persistence)
- **Completeness**: ~30-40% of Phase 1 plan

### Target State (Phase 1)
- **Architecture**: AWS Bedrock Agent + Aurora PostgreSQL + Redis
- **Deployment**: AWS ECS Fargate with Terraform IaC
- **Data Storage**: Aurora PostgreSQL with full audit trail
- **Completeness**: 100% of Phase 1 requirements

### Migration Approach
**Parallel Development** - Build new Bedrock implementation alongside existing prototype, then cutover.

---

## Gap Analysis Summary

### Critical Gaps (Must Fix)
1. ❌ **No Database** - Aurora PostgreSQL required
2. ❌ **No Redis** - Session management required
3. ❌ **Wrong LLM Provider** - OpenAI → AWS Bedrock Agent
4. ❌ **No Tests** - Zero test coverage
5. ❌ **No Knowledge Base** - ChromaDB integration needed

### High Priority Gaps
1. ⚠️ **Not Async** - Uses sync `requests` instead of `httpx`
2. ⚠️ **No Authentication** - JWT implementation needed
3. ⚠️ **No Monitoring** - CloudWatch dashboards required
4. ⚠️ **Streamlit UI** - React production UI needed

### Medium Priority Gaps
1. 🔶 **No IaC** - Terraform for infrastructure
2. 🔶 **No Circuit Breaker** - Resilience patterns missing
3. 🔶 **Lambda Functions** - PF360 integration via Lambda
4. 🔶 **Different Deployment** - EKS → ECS Fargate

---

## Migration Strategy

### Phase 1: Foundation (Weeks 1-2)
**Goal**: Set up AWS infrastructure and database

**Tasks**:
1. Create AWS infrastructure with Terraform
   - Aurora PostgreSQL Serverless v2
   - Redis ElastiCache
   - S3 buckets
   - VPC and security groups
   - AWS Secrets Manager

2. Design and implement database schema
   - Conversations table
   - Messages table
   - Sessions table
   - Audit logs table
   - SQLAlchemy models

3. Set up AWS Bedrock Agent
   - Create agent with Claude 3.5 Sonnet
   - Configure IAM roles
   - Set up basic instruction prompt

**Deliverables**:
- Infrastructure as Code (Terraform)
- Database schema with migrations
- AWS Bedrock Agent created

---

### Phase 2: Core Backend (Weeks 3-4)
**Goal**: Build FastAPI backend with Bedrock integration

**Tasks**:
1. Migrate tools to Lambda functions
   - Convert LangChain tools to Bedrock action groups
   - Implement Lambda functions for PF360 integration
   - Create OpenAPI schemas

2. Implement async FastAPI backend
   - Async endpoints with SQLAlchemy
   - Redis session management
   - Bedrock Agent invocation
   - JWT authentication

3. Replace sync operations with async
   - Use `httpx` instead of `requests`
   - Implement async database operations
   - Add circuit breakers

**Deliverables**:
- Lambda functions deployed
- Bedrock Agent with action groups
- Async FastAPI backend

---

### Phase 3: Knowledge Base & Testing (Weeks 5-6)
**Goal**: Add knowledge base and comprehensive testing

**Tasks**:
1. Set up ChromaDB knowledge base
   - Deploy ChromaDB server
   - Integrate with Bedrock Knowledge Base
   - Load initial FAQs and policies

2. Implement testing suite
   - Unit tests (80%+ coverage)
   - Integration tests
   - E2E tests with Playwright
   - Load testing

3. Add monitoring and observability
   - CloudWatch dashboards
   - Structured logging
   - Metrics and alarms

**Deliverables**:
- ChromaDB knowledge base
- Comprehensive test suite
- Monitoring dashboards

---

### Phase 4: Frontend & Deployment (Weeks 7-8)
**Goal**: Production-ready deployment

**Tasks**:
1. Build React production UI
   - TypeScript + Vite
   - Chat interface components
   - WebSocket integration
   - Responsive design

2. Set up CI/CD and deployment
   - GitHub Actions pipeline
   - ECS Fargate configuration
   - Staging environment
   - Production deployment

3. Documentation and training
   - API documentation
   - Operations runbook
   - User training materials

**Deliverables**:
- React production UI
- CI/CD pipeline
- Complete documentation

---

## Folder Structure

```
bedrock/
├── MIGRATION_PLAN.md           # This document
├── infrastructure/             # Terraform IaC
│   ├── main.tf
│   ├── variables.tf
│   ├── aurora.tf
│   ├── redis.tf
│   ├── bedrock.tf
│   └── outputs.tf
├── backend/                    # FastAPI application
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   │   └── routes.py
│   │   ├── models/            # SQLAlchemy models
│   │   ├── schemas/           # Pydantic schemas
│   │   ├── services/          # Business logic
│   │   └── core/              # Config, deps
│   ├── alembic/               # Database migrations
│   ├── tests/
│   └── requirements.txt
├── lambda/                     # Lambda functions
│   ├── pf360_integration/
│   ├── validation/
│   └── shared/
├── frontend/                   # React application
│   ├── src/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── services/
│   │   └── App.tsx
│   └── package.json
├── knowledge-base/             # ChromaDB content
│   ├── faqs/
│   ├── policies/
│   └── scripts/
├── docs/                       # Documentation
│   ├── API_REFERENCE.md
│   ├── DEPLOYMENT.md
│   └── OPERATIONS.md
└── scripts/                    # Utility scripts
    ├── deploy.sh
    └── seed-data.sh
```

---

## Technology Stack Mapping

### Current → Target

| Component | Current | Target | Migration Effort |
|-----------|---------|--------|------------------|
| **LLM** | OpenAI GPT-4.1 | AWS Bedrock (Claude 3.5) | HIGH - Complete rewrite |
| **Agent Framework** | LangChain | AWS Bedrock Agent | HIGH - Different paradigm |
| **Backend** | FastAPI (sync) | FastAPI (async) | MEDIUM - Refactor to async |
| **Database** | In-memory dict | Aurora PostgreSQL | HIGH - New infrastructure |
| **Session Store** | In-memory dict | Redis ElastiCache | MEDIUM - New service |
| **Knowledge Base** | None | ChromaDB + Bedrock KB | HIGH - New capability |
| **Frontend** | Streamlit | React + TypeScript | HIGH - Complete rewrite |
| **Deployment** | EKS (manual) | ECS Fargate (Terraform) | MEDIUM - Different platform |
| **Integration** | Direct API calls | Lambda functions | MEDIUM - Architectural change |
| **Testing** | None | Pytest + Playwright | HIGH - Build from scratch |

---

## Code Reusability Assessment

### Reusable Components (40%)
- ✅ **Tool Logic**: Business logic in tools can be ported to Lambda
- ✅ **PF360 Integration**: API calls can be adapted
- ✅ **System Prompt**: Can be adapted for Bedrock Agent instructions
- ✅ **Data Models**: Pydantic schemas from `models/schemas.py`
- ✅ **Deployment Scripts**: Bitbucket pipeline concepts

### Must Rewrite (60%)
- ❌ **Agent Configuration**: LangChain → Bedrock Agent
- ❌ **Session Management**: In-memory → Redis
- ❌ **Data Persistence**: None → Aurora PostgreSQL
- ❌ **Frontend**: Streamlit → React
- ❌ **Testing**: Build from scratch

---

## Migration Risks & Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Bedrock Agent learning curve | HIGH | HIGH | Early POC, AWS training |
| Aurora cost overrun | MEDIUM | MEDIUM | Use Serverless v2, monitor costs |
| PF360 API instability | HIGH | LOW | Circuit breakers, retries, stubs |
| Timeline slippage | MEDIUM | MEDIUM | 20% buffer, weekly reviews |
| Data migration complexity | LOW | LOW | Start fresh, no legacy data |

---

## Success Criteria

### Phase 1 Complete When:
1. ✅ AWS Bedrock Agent responding with >95% accuracy
2. ✅ Aurora PostgreSQL storing all conversations
3. ✅ Redis managing sessions across instances
4. ✅ React UI deployed and functional
5. ✅ 80%+ test coverage
6. ✅ <1s p95 latency
7. ✅ Production deployment successful
8. ✅ Documentation complete

---

## Next Steps

1. **Immediate Actions** (This Week):
   - [ ] Review and approve this migration plan
   - [ ] Set up AWS Bedrock access
   - [ ] Initialize Terraform repository
   - [ ] Create project board with tasks

2. **Week 1 Kickoff**:
   - [ ] Provision AWS infrastructure
   - [ ] Set up development environments
   - [ ] Create database schema
   - [ ] Begin Bedrock Agent configuration

3. **Ongoing**:
   - [ ] Weekly progress reviews
   - [ ] Maintain existing prototype for reference
   - [ ] Document learnings and blockers
   - [ ] Update this plan as needed

---

## Appendix: Comparison Table

### Detailed Feature Comparison

| Feature | Prototype (Current) | Phase 1 (Target) | Status |
|---------|-------------------|------------------|--------|
| **LLM Provider** | OpenAI GPT-4.1 | AWS Bedrock Claude 3.5 | ❌ Not Started |
| **Agent Framework** | LangChain | AWS Bedrock Agent | ❌ Not Started |
| **Database** | None (in-memory) | Aurora PostgreSQL | ❌ Not Started |
| **Session Store** | In-memory dict | Redis ElastiCache | ❌ Not Started |
| **Knowledge Base** | None | ChromaDB + Bedrock KB | ❌ Not Started |
| **Backend Framework** | FastAPI | FastAPI | ✅ Same |
| **Async Support** | Partial (mixed) | Full async | ⚠️ Needs Work |
| **Authentication** | Header passthrough | JWT with validation | ❌ Not Started |
| **Rate Limiting** | LLM only (0.8 RPS) | API + LLM | ⚠️ Partial |
| **Frontend** | Streamlit (dev) | React + TypeScript | ❌ Not Started |
| **Testing** | None | 80%+ coverage | ❌ Not Started |
| **Monitoring** | Basic logs | CloudWatch dashboards | ❌ Not Started |
| **Deployment** | EKS (manual) | ECS Fargate (IaC) | ❌ Not Started |
| **Infrastructure** | Manual | Terraform | ❌ Not Started |
| **CI/CD** | Bitbucket Pipelines | GitHub Actions | ⚠️ Different Tool |
| **Health Check** | `/api/healthz` | `/api/healthz` | ✅ Same |
| **API Docs** | Swagger UI | Swagger UI | ✅ Same |
| **Error Handling** | Basic | Structured + retry | ⚠️ Needs Enhancement |
| **Circuit Breaker** | None | Implemented | ❌ Not Started |
| **Audit Trail** | None | Full database logging | ❌ Not Started |

---

## Conclusion

The current prototype serves as a **proof of concept** demonstrating the scheduling agent's capabilities with OpenAI/LangChain. The full Phase 1 implementation will:

1. **Migrate to AWS Bedrock** for enterprise-grade AI
2. **Add persistence** with Aurora PostgreSQL
3. **Scale horizontally** with Redis sessions
4. **Enhance with RAG** via ChromaDB knowledge base
5. **Production-ready** with tests, monitoring, IaC

**Estimated Effort**: 480-600 hours (8-10 weeks, 3 engineers)

**Recommendation**: Proceed with parallel development in `bedrock/` folder while maintaining prototype for reference.
