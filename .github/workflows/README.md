# GitHub Actions Workflows

Automated testing workflows for the a2a-x402 project.

## Workflows

### 1. E2E HTTP Tests (`test-e2e-http.yml`)

**Purpose**: Fast, reliable protocol-level testing suitable for continuous integration.

**Runs on**:
- Push to `main`, `feat/*`, `test/*` branches
- Pull requests to `main`
- Manual trigger via workflow_dispatch

**Duration**: ~5-10 minutes

**Tests**:
- Complete payment flow via HTTP/A2A protocol
- Multiple plan selection
- Different products (parametrized)
- Concurrent purchases
- Invalid task ID handling
- Timeout handling

**Artifacts**:
- Test results (JUnit XML)
- Agent logs

### 2. E2E Browser Tests (`test-e2e-browser.yml`)

**Purpose**: Comprehensive UI/UX validation through browser automation.

**Runs on**:
- Push to `main`, `feat/*`, `test/*` branches
- Pull requests to `main`
- Manual trigger via workflow_dispatch
- Scheduled daily at 2 AM UTC (optional)

**Duration**: ~20-30 minutes

**Tests**:
- Happy path browser flow
- Timeout handling
- Invalid plan selection (99, abc, cancel)
- Multiple consecutive purchases
- UI element validation
- Accessibility checks

**Artifacts**:
- Test results (JUnit XML)
- Browser screenshots
- Agent logs

**Special features**:
- Automatically comments on PRs with screenshot links
- Uploads screenshots for debugging failures

## Required Configuration

Configure these in your GitHub repository settings.

### Repository Secrets

Sensitive credentials that must be kept private:

- `NVM_API_KEY_SERVER` - Merchant/server API key (format: `sandbox:jwt-token`)
- `NVM_API_KEY_CLIENT` - Subscriber/client API key (format: `sandbox:jwt-token`)
- `GOOGLE_API_KEY` - Google AI API key for Gemini

**Note**: Use test/sandbox credentials, not production keys!

### Repository Variables

Non-sensitive configuration values (can be public):

- `NVM_ENVIRONMENT` - Environment name (e.g., `sandbox`, `staging`, `production`)
- `NVM_CREDITS_PLAN_ID` - Credits-based payment plan ID
- `NVM_PAYASYOUGO_PLAN_ID` - Pay-as-you-go payment plan ID (optional)
- `NVM_AGENT_ID` - Agent ID for x402 payments

**Why Variables Instead of Secrets?**
- Variables are visible in workflow logs (useful for debugging)
- These IDs are not credentials - they identify public resources
- Plan IDs and Agent IDs can be safely shared in logs
- Separating secrets from config improves security hygiene

**Security Note**: Never put API keys, JWT tokens, or passwords in variables - only in secrets!

## Setting Up Configuration

### Via GitHub UI

**Secrets** (Settings → Secrets and variables → Actions → Secrets tab):
1. Click **New repository secret**
2. Add each secret:
   - `NVM_API_KEY_SERVER` = `sandbox:your-server-jwt`
   - `NVM_API_KEY_CLIENT` = `sandbox:your-client-jwt`
   - `GOOGLE_API_KEY` = `your-google-api-key`

**Variables** (Settings → Secrets and variables → Actions → Variables tab):
1. Click **New repository variable**
2. Add each variable:
   - `NVM_ENVIRONMENT` = `sandbox`
   - `NVM_CREDITS_PLAN_ID` = `your-credits-plan-id`
   - `NVM_PAYASYOUGO_PLAN_ID` = `your-payg-plan-id`
   - `NVM_AGENT_ID` = `your-agent-id`

### Via GitHub CLI

```bash
# Set secrets (sensitive credentials)
gh secret set NVM_API_KEY_SERVER -b "sandbox:your-server-jwt"
gh secret set NVM_API_KEY_CLIENT -b "sandbox:your-client-jwt"
gh secret set GOOGLE_API_KEY -b "your-google-api-key"

# Set variables (non-sensitive configuration)
gh variable set NVM_ENVIRONMENT -b "sandbox"
gh variable set NVM_CREDITS_PLAN_ID -b "your-credits-plan-id"
gh variable set NVM_PAYASYOUGO_PLAN_ID -b "your-payg-plan-id"
gh variable set NVM_AGENT_ID -b "your-agent-id"
```

## Running Workflows Manually

### Via GitHub UI

1. Go to **Actions** tab
2. Select workflow (HTTP or Browser tests)
3. Click **Run workflow**
4. Select branch and click **Run workflow**

### Via GitHub CLI

```bash
# Run HTTP tests
gh workflow run test-e2e-http.yml --ref main

# Run browser tests
gh workflow run test-e2e-browser.yml --ref feat/my-feature
```

## Viewing Results

### Test Results

- Click on workflow run
- Check the **Summary** page for test results
- Green checkmark = all tests passed
- Red X = some tests failed

### Downloading Artifacts

1. Go to workflow run
2. Scroll to **Artifacts** section at bottom
3. Download:
   - `http-test-results` - HTTP test logs
   - `browser-test-results` - Browser test logs
   - `browser-screenshots` - Browser test screenshots

### Screenshots on PRs

For pull requests, browser tests automatically comment with:
- Number of screenshots captured
- List of key screenshot files
- Link to download full artifact

## Workflow Configuration

### Customizing Triggers

Edit the `on:` section in workflow files:

```yaml
on:
  push:
    branches: [main, develop]  # Add/remove branches
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM UTC
```

### Adjusting Timeouts

```yaml
jobs:
  test-browser:
    timeout-minutes: 30  # Change job timeout

steps:
  - name: Run Browser E2E Tests
    run: |
      uv run pytest tests/test_e2e_browser.py --timeout=180  # Change pytest timeout
```

### Caching Dependencies

Both workflows use `enable-cache: true` for uv to cache dependencies:

```yaml
- name: Install uv
  uses: astral-sh/setup-uv@v4
  with:
    enable-cache: true
    cache-dependency-glob: "python/examples/adk-demo/uv.lock"
```

This speeds up subsequent runs by ~2-3 minutes.

## Troubleshooting

### Tests Fail with Missing Configuration

**Error**: Variables or secrets not found

**Solution**: Ensure all required secrets AND variables are configured:
- Go to **Settings** → **Secrets and variables** → **Actions**
- Check **Secrets** tab for API keys
- Check **Variables** tab for environment/plan/agent IDs

### Browser tests fail with Playwright errors

**Solution**: Check that Playwright browsers are installed correctly:
```yaml
- name: Install Playwright browsers
  run: |
    uv run python -m playwright install --with-deps chromium
```

### Tests timeout

**Causes**:
- Agents taking too long to start
- Network issues with Nevermined API
- Merchant payment verification bug

**Solutions**:
- Increase timeout values
- Check agent logs in artifacts
- Review known issues in test documentation

### Tests pass locally but fail in CI

**Common causes**:
- Missing secrets
- Different Python version
- Environment-specific dependencies

**Debug steps**:
1. Download test artifacts
2. Review agent logs
3. Check screenshots (browser tests)
4. Verify secrets are set correctly

## Best Practices

1. **Use HTTP tests for CI/CD**: Faster feedback loop, run on every push
2. **Use browser tests for validation**: Comprehensive UI testing, run on PRs or scheduled
3. **Monitor test duration**: Optimize if tests consistently take >15 min (HTTP) or >30 min (browser)
4. **Review screenshots**: Always check screenshots when browser tests fail
5. **Keep secrets updated**: Use fresh test credentials, rotate periodically

## Maintenance

### Updating Dependencies

When updating Python packages:
1. Run `uv lock` locally
2. Commit updated `uv.lock`
3. Workflows will automatically use new dependencies

### Adding New Tests

1. Add tests to `tests/test_e2e_http.py` or `tests/test_e2e_browser.py`
2. Test locally: `uv run pytest tests/test_e2e_http.py -v`
3. Push changes - workflows run automatically
4. Monitor first run to ensure tests pass in CI

## Support

For issues with workflows:
1. Check workflow logs in Actions tab
2. Download and review test artifacts
3. Open issue with:
   - Workflow run URL
   - Error messages
   - Test artifacts (if applicable)
