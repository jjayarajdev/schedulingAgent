# Deployment Scripts

This folder contains deployment automation and documentation for the ProjectForce Bedrock Multi-Agent System.

## Quick Start

For a new AWS environment:

```bash
./dev_deploy.sh
```

That's it! This script will:
1. Run the main DEPLOY.sh (infrastructure + agents)
2. Run SETUP_COLLABORATION.sh (agent collaboration)
3. Show you next steps for testing

## Files in This Directory

| File | Purpose |
|------|---------|
| **dev_deploy.sh** | ✅ Automated deployment wrapper (recommended) |
| **DEPLOYMENT_GUIDE.md** | 📖 Complete deployment documentation |
| **README.md** | 📄 This file |
| ~~DEPLOY.sh~~ | ❌ Old duplicate - DO NOT USE (use `../DEPLOY.sh` instead) |

## Actual Working Scripts

The actual deployment scripts are one level up:

- `../DEPLOY.sh` - Main deployment (creates everything)
- `../SETUP_COLLABORATION.sh` - Configures agent collaboration

The `dev_deploy.sh` script here is just a convenient wrapper that runs both in sequence.

## Documentation

See [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) for:
- Prerequisites
- Step-by-step deployment instructions
- Troubleshooting
- Architecture overview
- File organization explanation

## Support

- Issues with deployment? Check the deployment guide's troubleshooting section
- Lambda errors? Check CloudWatch Logs: `/aws/lambda/pf-scheduling-actions`
- Agent behavior issues? Check the action group schemas in `../DEPLOY.sh`
