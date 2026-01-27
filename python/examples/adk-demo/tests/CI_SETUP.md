# CI/CD Setup for E2E Tests

## Overview
The E2E tests run successfully locally but require proper GitHub Secrets configuration to pass in CI/CD.

## Required GitHub Secrets

The following secrets must be configured in the GitHub repository settings:

### 1. `OPENAI_API_KEY`
- **Description**: OpenAI API key for LLM functionality
- **Format**: Starts with `sk-proj-` or `sk-`
- **Where to get**: https://platform.openai.com/account/api-keys
- **Common issues**:
  - Expired API key
  - Incorrect format (must not have quotes or extra whitespace)
  - Insufficient permissions/quota

### 2. `NVM_API_KEY_SERVER`
- **Description**: Nevermined API key for merchant/server agent
- **Format**: `sandbox-staging:<JWT>` or `production:<JWT>`
- **Where to get**: https://nevermined.app/permissions/global-permissions

### 3. `NVM_API_KEY_CLIENT`
- **Description**: Nevermined API key for client/subscriber agent
- **Format**: `sandbox-staging:<JWT>` or `production:<JWT>`
- **Where to get**: https://nevermined.app/permissions/global-permissions

## Current Issue (as of 2026-01-27)

**The CI tests are failing because the `OPENAI_API_KEY` GitHub Secret is invalid or expired.**

Error message from CI:
```
litellm.AuthenticationError: OpenAIException - Incorrect API key provided: sk-proj-***
```

### To Fix:
1. Go to GitHub repository settings → Secrets and variables → Actions
2. Update the `OPENAI_API_KEY` secret with a valid OpenAI API key
3. Re-run the failed workflow

## Verifying Secrets

To verify that secrets are set correctly in CI, check the workflow logs for:
- ✓ "All required secrets are set!" message in the "Verify secrets are set" step
- Environment variables loaded correctly in conftest.py output

## Local Testing

For local testing, create a `.env` file in `python/examples/adk-demo/` directory:

```bash
# Copy from repository root or create new
cp ../../../.env python/examples/adk-demo/.env

# Or manually create with your credentials
cat > python/examples/adk-demo/.env << 'EOF'
NVM_API_KEY_SERVER=sandbox-staging:<your-server-jwt>
NVM_API_KEY_CLIENT=sandbox-staging:<your-client-jwt>
NVM_ENVIRONMENT=staging_sandbox
OPENAI_API_KEY=sk-proj-<your-openai-key>
NVM_CREDITS_PLAN_ID=<plan-id>
NVM_PAYASYOUGO_PLAN_ID=<plan-id>
NVM_AGENT_ID=<agent-id>
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o
EOF
```

## Test Results Status

### Local Tests: ✅ PASSING (8 passed, 1 skipped)
All tests pass when run locally with valid credentials.

### CI Tests: ❌ FAILING
Tests fail in CI due to invalid `OPENAI_API_KEY`.

**Expected after fixing OPENAI_API_KEY**: All tests should pass in CI as well.
