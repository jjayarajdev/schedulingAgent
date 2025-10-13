# Bedrock Multi-Agent Scheduling System

AWS Bedrock-based multi-agent collaboration system for property management scheduling.

## 📁 Project Structure

```
bedrock/
├── docs/                   # Documentation
│   ├── README.md          # Main project documentation
│   ├── ARCHITECTURE.md    # System architecture
│   ├── DEPLOYMENT_GUIDE.md
│   ├── TESTING_GUIDE.md
│   ├── ENABLE_API_ACCESS.md
│   └── AWS_SUPPORT_TICKET.md
│
├── tests/                 # Test scripts
│   ├── README.md          # Testing documentation
│   ├── test_api_access.py # API access validation
│   ├── test_agents_interactive.py # Interactive testing
│   └── test_agent.py      # Basic test (legacy)
│
├── utils/                 # Utility scripts
│   ├── README.md          # Utilities documentation
│   └── prepare_all_agents.py # Agent preparation
│
├── scripts/               # Shell scripts
│   ├── README.md          # Scripts documentation
│   ├── gather_diagnostics.sh # Diagnostic collection
│   └── verify_deployment.sh  # Deployment verification
│
├── infrastructure/        # Terraform IaC
│   └── terraform/        # Terraform configurations
│       ├── bedrock_agents.tf
│       ├── main.tf
│       ├── variables.tf
│       └── terraform.tfvars
│
├── backend/              # Backend services (future)
│   └── api/             # FastAPI backend
│
├── frontend/            # Frontend app (future)
│   └── app/            # React application
│
├── lambda/              # Lambda functions
│   └── action-groups/  # Agent action group handlers
│
└── knowledge-base/      # Knowledge base content
    └── documents/      # Documentation for agents
```

---

## 🚀 Quick Start

### 1. Test Your Deployment
```bash
# Run deployment verification
./scripts/verify_deployment.sh

# Prepare all agents
python3 utils/prepare_all_agents.py

# Test API access
python3 tests/test_api_access.py
```

### 2. Interactive Testing
```bash
# Launch interactive testing mode
python3 tests/test_agents_interactive.py

# Choose:
# 1. Run predefined test scenarios
# 2. Interactive chat mode
# 3. Show AWS Console instructions
```

### 3. Troubleshooting
```bash
# Gather diagnostics for support ticket
./scripts/gather_diagnostics.sh

# View summary
cat /tmp/bedrock_diagnostics_*/0_SUMMARY.txt
```

---

## 📚 Documentation

### Getting Started
- **[Main Documentation](docs/README.md)** - Project overview and architecture
- **[Deployment Guide](docs/DEPLOYMENT_GUIDE.md)** - Step-by-step deployment
- **[Testing Guide](docs/TESTING_GUIDE.md)** - How to test the system

### Troubleshooting
- **[Enable API Access](docs/ENABLE_API_ACCESS.md)** - Fix 403 errors
- **[AWS Support Ticket](docs/AWS_SUPPORT_TICKET.md)** - Pre-filled support template
- **[Architecture](docs/ARCHITECTURE.md)** - System design and components

### Component READMEs
- **[Tests README](tests/README.md)** - Testing scripts documentation
- **[Utils README](utils/README.md)** - Utility scripts documentation
- **[Scripts README](scripts/README.md)** - Shell scripts documentation

---

## 🤖 Agents

### Supervisor Agent
- **ID**: `5VTIWONUMO`
- **Latest Alias**: `HH2U7EZXMW` (version 6)
- **Model**: Claude Sonnet 4.5
- **Role**: Routes requests to specialized collaborators

### Collaborator Agents

| Agent | ID | V4 Alias | Purpose |
|-------|-----|----------|---------|
| **Chitchat** | `BIUW1ARHGL` | `THIPMPJCPI` | Greetings, help, conversation |
| **Scheduling** | `IX24FSMTQH` | `TYJRF3CJ7F` | Appointments, availability |
| **Information** | `C9ANXRIO8Y` | `YVNFXEKPWO` | Project details, hours, weather |
| **Notes** | `G5BVBYEPUM` | `F9QQNLZUW8` | Note management |

All agents use: **Claude Sonnet 4.5** (`us.anthropic.claude-sonnet-4-5-20250929-v1:0`)

---

## 🧪 Testing

### Quick Tests
```bash
# API access validation
python3 tests/test_api_access.py

# Interactive testing
python3 tests/test_agents_interactive.py
```

### Console Testing (Always Works)
1. Go to: https://console.aws.amazon.com/bedrock/home?region=us-east-1#/agents
2. Click: `scheduling-agent-supervisor`
3. Click: **Test** button
4. Try: "Hello! How are you?"

### Test Scenarios
- **Greeting**: "Hello! How are you today?"
- **Scheduling**: "I want to schedule an appointment"
- **Information**: "What are your working hours?"
- **Notes**: "Add a note that I prefer morning appointments"

---

## 🛠️ Development Workflow

### After Code Changes
```bash
# 1. Apply Terraform changes
cd infrastructure/terraform
terraform apply

# 2. Prepare agents
cd ../..
python3 utils/prepare_all_agents.py

# 3. Verify deployment
./scripts/verify_deployment.sh

# 4. Run tests
python3 tests/test_api_access.py
```

### Before Submitting PR
```bash
# Run full test suite
python3 tests/test_agents_interactive.py  # Choose option 1

# Verify all agents work
./scripts/verify_deployment.sh

# Generate diagnostic report
./scripts/gather_diagnostics.sh
```

---

## 🚨 Troubleshooting

### Common Issues

#### Issue: 403 Access Denied on Agent Invocation

**Symptoms:**
```
accessDeniedException: Access denied when calling Bedrock
```

**Solution:**
1. Check [ENABLE_API_ACCESS.md](docs/ENABLE_API_ACCESS.md)
2. Or submit support ticket using [AWS_SUPPORT_TICKET.md](docs/AWS_SUPPORT_TICKET.md)

**Workaround:** Use Console testing (always works)

---

#### Issue: Agent Not Prepared

**Symptoms:**
```
ValidationException: Agent must be in PREPARED state
```

**Solution:**
```bash
python3 utils/prepare_all_agents.py
```

Wait 30-60 seconds, then retry.

---

#### Issue: Model Not Found

**Symptoms:**
```
ResourceNotFoundException: Model not found
```

**Solution:** Verify model ID in agent configuration:
```bash
aws bedrock-agent get-agent --agent-id 5VTIWONUMO --region us-east-1 \
  --query 'agent.foundationModel'
```

Should output: `us.anthropic.claude-sonnet-4-5-20250929-v1:0`

---

## 📊 Current Status

**Phase**: ✅ Phase 1 Complete - Agents Deployed

**What Works:**
- ✅ Multi-agent collaboration architecture
- ✅ Agent routing and delegation
- ✅ Console testing
- ✅ Direct model invocation
- ✅ All agents prepared and configured

**What's Pending:**
- ⚠️ API access (waiting on AWS to enable on-demand access)
- ⏳ Backend API integration (Phase 2)
- ⏳ Frontend application (Phase 2)
- ⏳ Knowledge base integration (Phase 3)

---

## 🔧 Requirements

### AWS Resources
- AWS Account with Bedrock access
- IAM permissions for Bedrock agents
- Model access to Claude Sonnet 4.5

### Development Tools
```bash
# Python
python3 >= 3.8

# Python packages
pip install boto3

# AWS CLI
brew install awscli  # macOS
pip install awscli   # Other

# Terraform
brew install terraform  # macOS
```

### AWS Credentials
```bash
aws configure
# Provide: Access Key, Secret Key, Region (us-east-1)
```

---

## 📦 Installation

### Clone Repository
```bash
git clone <repository-url>
cd schedulingAgent-bb/bedrock
```

### Install Dependencies
```bash
pip install boto3
```

### Configure AWS
```bash
aws configure
# Region: us-east-1
```

### Deploy Infrastructure
```bash
cd infrastructure/terraform
terraform init
terraform plan
terraform apply
```

### Prepare Agents
```bash
cd ../..
python3 utils/prepare_all_agents.py
```

### Verify Deployment
```bash
./scripts/verify_deployment.sh
```

---

## 🤝 Contributing

### Making Changes

1. Create feature branch
2. Make changes
3. Test thoroughly:
   ```bash
   ./scripts/verify_deployment.sh
   python3 tests/test_agents_interactive.py
   ```
4. Update documentation
5. Submit PR

### Documentation Updates

When you update agents or add features:
1. Update relevant README in docs/
2. Update test scripts if needed
3. Update DOCUMENTATION_INDEX.md

---

## 📞 Support

### AWS Support
- Use template: [AWS_SUPPORT_TICKET.md](docs/AWS_SUPPORT_TICKET.md)
- Gather diagnostics: `./scripts/gather_diagnostics.sh`

### Internal Support
- Check [DOCUMENTATION_INDEX.md](docs/DOCUMENTATION_INDEX.md) for all guides
- Review [TESTING_GUIDE.md](docs/TESTING_GUIDE.md) for testing help

---

## 📝 License

[Your License Here]

---

## 🏗️ Project Status

- **Phase 1**: ✅ Complete - Multi-agent infrastructure deployed
- **Phase 2**: 📋 Planned - Backend API and frontend
- **Phase 3**: 📋 Planned - Knowledge base and advanced features

---

**Last Updated**: October 13, 2025
**AWS Region**: us-east-1
**Model**: Claude Sonnet 4.5
