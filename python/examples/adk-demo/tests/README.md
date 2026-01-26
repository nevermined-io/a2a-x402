# E2E Tests for ADK x402 Payment Flow

Automated end-to-end tests for validating the complete payment flow in the ADK x402 demo.

## Overview

This test suite provides comprehensive validation of the payment flow through two approaches:

1. **HTTP/A2A Protocol Tests** (`test_e2e_http.py`) - Fast, reliable tests that interact directly with the A2A protocol
2. **Browser Automation Tests** (`test_e2e_browser.py`) - *(Coming soon)* Tests that validate the actual user interface workflow

## Quick Start

### 1. Setup Test Environment

```bash
# Copy your .env to tests/.env.test
cp .env tests/.env.test

# Or if you don't have .env yet, copy from sample
cp .env.sample tests/.env.test

# Edit tests/.env.test and configure your test credentials
# IMPORTANT: Use test/sandbox environment credentials
vim tests/.env.test
```

### 2. Install Test Dependencies

```bash
# Install all dependencies including test group
uv sync --group test

# Install Playwright browsers (required for browser tests)
uv run playwright install chromium
```

### 3. Discover UI Selectors (Required for Browser Tests)

```bash
# Start agents in separate terminals:
# Terminal 1: uv run server --port=10000
# Terminal 2: uv run adk web --port=8000

# Then run selector discovery:
uv run python tests/discover_selectors.py

# Check output and update SELECTORS in tests/test_e2e_browser.py
```

### 4. Run Tests

```bash
# Run all HTTP tests (recommended for CI/CD)
uv run pytest tests/test_e2e_http.py -v

# Run browser tests (requires UI selectors to be discovered first)
uv run pytest tests/test_e2e_browser.py -v

# Run all tests (HTTP + browser)
uv run pytest tests/ -v

# Run specific test
uv run pytest tests/test_e2e_http.py::TestE2EPaymentFlowHTTP::test_happy_path_payment_flow -v -s

# Run with detailed output
uv run pytest tests/ -v -s

# Run only fast tests (exclude slow browser tests)
uv run pytest tests/ -m "not slow" -v

# Run only browser tests
uv run pytest tests/ -m browser -v
```

## Test Structure

```
tests/
├── __init__.py                 # Test package marker
├── conftest.py                 # Pytest fixtures and configuration
├── process_manager.py          # Agent process start/stop utilities
├── http_test_helper.py         # HTTP/A2A protocol helpers
├── browser_helper.py           # Browser automation helper (Playwright)
├── test_e2e_http.py            # HTTP-based E2E tests
├── test_e2e_browser.py         # Browser-based E2E tests
├── discover_selectors.py       # UI selector discovery tool
├── .env.test                   # Test environment configuration (not in git)
├── screenshots/                # Browser test screenshots (not in git)
├── logs/                       # Process logs (not in git)
└── README.md                   # This file
```

## HTTP Tests (test_e2e_http.py)

### Test Classes

#### `TestE2EPaymentFlowHTTP`
Complete payment flow tests including:
- `test_happy_path_payment_flow()` - Full purchase flow with payment and verification
- `test_multiple_plan_selection()` - Selecting different payment plans
- `test_different_products()` - Parametrized test for various products
- `test_concurrent_purchases()` - Multiple simultaneous purchase requests

#### `TestE2EPaymentEdgeCases`
Edge case and error handling:
- `test_insufficient_credits()` - *(Skipped by default)* Requires depleted credits account
- `test_invalid_task_id()` - Submitting payment for non-existent task
- `test_timeout_handling()` - Very short timeout behavior

### What HTTP Tests Validate

✅ Agent startup and health checks
✅ Purchase request initiates payment flow
✅ Payment requirements returned correctly
✅ Multiple payment plans offered
✅ X402 access token generation
✅ Payment submission accepted
✅ Payment completion with transaction hash
✅ Transaction hash format (0x + 64 hex characters)
✅ Credits deducted from balance
✅ Concurrent request handling
✅ Error handling for edge cases

## Browser Tests (test_e2e_browser.py)

### Test Classes

#### `TestE2EPaymentFlowBrowser`
Complete payment flow through web UI:
- `test_happy_path_browser_flow()` - Full purchase flow via browser
- `test_browser_timeout_no_response()` - Timeout behavior
- `test_browser_invalid_plan_selection()` - Invalid plan choices
- `test_browser_multiple_purchases()` - Multiple consecutive purchases

#### `TestBrowserUIElements`
UI validation and accessibility:
- `test_ui_elements_exist()` - Verify all UI elements present
- `test_page_accessibility()` - Check ARIA roles and accessibility

### What Browser Tests Validate

✅ UI loads correctly in browser
✅ Message input field functional
✅ Send button clickable
✅ Purchase message displays
✅ Payment options appear in UI
✅ Plan selection works
✅ Transaction hash visible
✅ UI handles timeouts gracefully
✅ Invalid selections show errors
✅ Multiple purchases work sequentially

### Important Notes

**UI Selector Discovery Required**: Browser tests require discovering CSS selectors first:
1. Start agents: `uv run server --port=10000` and `uv run adk web --port=8000`
2. Run: `uv run python tests/discover_selectors.py`
3. Update `SELECTORS` dict in `test_e2e_browser.py` with discovered values

**Playwright Installation**: Browser tests require Playwright browsers:
```bash
uv run playwright install chromium
```

**AppArmor Configuration**: Browser launches with `--no-sandbox` flags due to Ubuntu AppArmor restrictions (per CLAUDE.md). This is normal and expected.

## Environment Configuration

### Required Variables (tests/.env.test)

```bash
# Nevermined Authentication
NVM_API_KEY_SERVER=sandbox:your-merchant-jwt-token
NVM_API_KEY_CLIENT=sandbox:your-subscriber-jwt-token
NVM_ENVIRONMENT=sandbox

# Agent Configuration
NVM_CREDITS_PLAN_ID=your-credits-plan-id
NVM_PAYASYOUGO_PLAN_ID=your-payasyougo-plan-id  # Optional
NVM_AGENT_ID=your-agent-id

# LLM Provider
GOOGLE_API_KEY=your-google-api-key
# OR for OpenAI:
# LLM_PROVIDER=openai
# OPENAI_API_KEY=your-openai-api-key
```

### Optional Test-Specific Variables

```bash
# Test configuration
TEST_TIMEOUT=30
TEST_BROWSER_HEADLESS=true
TEST_SCREENSHOT_DIR=tests/screenshots
```

## Test Fixtures

### Agent Process Fixtures (conftest.py)

- `merchant_agent` - Starts merchant agent on port 10000
- `client_agent` - Starts client agent web UI on port 8000
- `process_manager` - Manages agent lifecycle and cleanup

### Configuration Fixtures

- `test_config` - URLs, timeouts, directories
- `test_env_vars` - Loads variables from .env.test
- `setup_test_dirs` - Ensures screenshot/log directories exist

### Test Markers

- `@pytest.mark.e2e` - End-to-end integration tests
- `@pytest.mark.http` - HTTP/A2A protocol tests
- `@pytest.mark.browser` - Browser automation tests
- `@pytest.mark.slow` - Tests taking significant time

## Running Specific Test Categories

```bash
# Only HTTP tests
uv run pytest -m http -v

# Only E2E tests
uv run pytest -m e2e -v

# Skip slow tests
uv run pytest -m "not slow" -v

# Run with coverage
uv run pytest --cov=server --cov=client_agent tests/
```

## Troubleshooting

### Tests Fail with "Health check timeout"

**Cause**: Agents failed to start or took too long to initialize

**Solutions**:
- Check `.env.test` has valid credentials
- Ensure ports 8000 and 10000 are not in use
- Check agent logs in `tests/logs/`
- Increase timeout in `process_manager.py`

### Tests Fail with "Test environment file not found"

**Cause**: Missing `tests/.env.test`

**Solution**:
```bash
cp .env tests/.env.test
# or
cp .env.sample tests/.env.test
# Then edit tests/.env.test with your credentials
```

### Tests Fail with "Module not found"

**Cause**: Missing test dependencies

**Solution**:
```bash
uv sync --group test
```

### Tests Hang or Don't Complete

**Cause**: Agent processes not cleaned up

**Solution**:
```bash
# Kill any orphaned processes
pkill -f "uv run server"
pkill -f "uv run adk"

# Or kill processes on ports 8000 and 10000
lsof -ti:8000 | xargs kill -9
lsof -ti:10000 | xargs kill -9
```

### Transaction Hash Not Found

**Cause**: Payment may not have completed on blockchain

**Check**:
- Verify sufficient credits in plan
- Check merchant logs for settlement errors
- Verify sandbox environment is accessible

## Test Development

### Adding New HTTP Tests

1. Add test method to `TestE2EPaymentFlowHTTP` or `TestE2EPaymentEdgeCases`
2. Use `self.helper` for HTTP interactions
3. Use `self.payments_client` for Nevermined API calls
4. Add appropriate markers (`@pytest.mark.http`, etc.)

Example:
```python
async def test_my_new_scenario(self):
    """Test description."""
    # Send request
    response = await self.helper.send_purchase_request("my-product")

    # Assertions
    assert self.helper.get_task_state(response) == "input_required"
```

### Adding Helper Methods

Add reusable methods to `http_test_helper.py`:

```python
async def my_helper_method(self, param: str) -> dict:
    """Helper description."""
    # Implementation
    pass
```

## CI/CD Integration

### GitHub Actions Workflows

Two automated workflows are configured in `.github/workflows/`:

1. **HTTP Tests** (`test-e2e-http.yml`):
   - Runs on push to main/feat/test branches
   - Fast protocol-level testing (~5-10 min)
   - Suitable for continuous integration

2. **Browser Tests** (`test-e2e-browser.yml`):
   - Runs on PRs and scheduled daily
   - Comprehensive UI validation (~20-30 min)
   - Uploads screenshots as artifacts

**Required Configuration** (in repository settings):

*Secrets* (sensitive):
- `NVM_API_KEY_SERVER` - Merchant API key
- `NVM_API_KEY_CLIENT` - Client API key
- `GOOGLE_API_KEY` - Google AI API key

*Variables* (non-sensitive):
- `NVM_ENVIRONMENT` - Environment (sandbox/staging/production)
- `NVM_CREDITS_PLAN_ID` - Credits-based payment plan ID
- `NVM_PAYASYOUGO_PLAN_ID` - Pay-as-you-go plan ID (optional)
- `NVM_AGENT_ID` - Agent ID for x402 payments

See `.github/workflows/README.md` for detailed documentation.

### Manual Workflow Trigger

```bash
# Run HTTP tests
gh workflow run test-e2e-http.yml --ref main

# Run browser tests
gh workflow run test-e2e-browser.yml --ref feat/my-feature
```

## Future Enhancements

### Planned (Phase 3)
- [ ] Browser automation tests with Puppeteer
- [ ] UI selector discovery tool
- [ ] Balance update verification in UI
- [ ] Payment cancellation flow
- [ ] Multiple consecutive purchases

### Ideas
- [ ] Performance benchmarks
- [ ] Load testing with multiple concurrent users
- [ ] Blockchain transaction verification
- [ ] Video recording of browser tests
- [ ] Test report generation with screenshots

## Support

For issues or questions:
1. Check the main [README](../README.md) for setup instructions
2. Review [RUN.md](../RUN.md) for running the demo manually
3. Check test logs in `tests/logs/`
4. Open an issue on GitHub
