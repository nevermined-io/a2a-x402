"""
Pytest configuration and fixtures for E2E tests.

Provides shared fixtures for both HTTP and browser-based tests including:
- Agent process management (merchant and client)
- Environment setup
- Test cleanup
"""

import asyncio
import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from .process_manager import AgentProcessManager

# Load .env file before running tests
dotenv_path = Path(__file__).parent.parent / ".env"
print(f"[CONFTEST] Loading .env from: {dotenv_path}")
print(f"[CONFTEST] .env file exists: {dotenv_path.exists()}")
print(f"[CONFTEST] Current os.environ NVM_API_KEY_CLIENT (BEFORE loading): {len(os.getenv('NVM_API_KEY_CLIENT', ''))} chars")
if dotenv_path.exists():
    print(f"[CONFTEST] .env file size: {dotenv_path.stat().st_size} bytes")
    # Manually read and set environment variables to ensure they're actually set
    with open(dotenv_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value
                if key in ['NVM_API_KEY_CLIENT', 'NVM_API_KEY_SERVER', 'OPENAI_API_KEY']:
                    print(f"[CONFTEST] Set {key} (length: {len(value)})")
else:
    load_dotenv(dotenv_path=dotenv_path, override=True)
print(f"[CONFTEST] After loading:")
print(f"[CONFTEST]   NVM_API_KEY_CLIENT is set: {'NVM_API_KEY_CLIENT' in os.environ}")
print(f"[CONFTEST]   NVM_API_KEY_SERVER is set: {'NVM_API_KEY_SERVER' in os.environ}")
print(f"[CONFTEST]   OPENAI_API_KEY is set: {'OPENAI_API_KEY' in os.environ}")
if 'NVM_API_KEY_CLIENT' in os.environ:
    print(f"[CONFTEST]   NVM_API_KEY_CLIENT length: {len(os.getenv('NVM_API_KEY_CLIENT', ''))}")


# Configure pytest-asyncio
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
def process_manager():
    """
    Create and return agent process manager.

    This fixture is module-scoped so processes can be shared across tests
    in the same module for efficiency.
    """
    manager = AgentProcessManager()
    yield manager
    # Cleanup after all tests in module complete
    manager.stop_all()


@pytest.fixture(scope="module")
async def merchant_agent(process_manager):
    """
    Start merchant agent and keep it running for all tests in module.

    Args:
        process_manager: The process manager fixture

    Yields:
        subprocess.Popen: Running merchant process
    """
    process = await process_manager.start_merchant(port=10000)
    yield process
    # Cleanup handled by process_manager fixture


@pytest.fixture(scope="module")
async def client_agent(process_manager):
    """
    Start client agent web UI and keep it running for all tests in module.

    Args:
        process_manager: The process manager fixture

    Yields:
        subprocess.Popen: Running client process
    """
    process = await process_manager.start_client(port=8000)
    yield process
    # Cleanup handled by process_manager fixture


@pytest.fixture
def test_config():
    """
    Provide test configuration.

    Returns:
        dict: Test configuration including URLs, timeouts, etc.
    """
    return {
        "merchant_url": "http://localhost:10000/agents/merchant_agent",
        "client_url": "http://localhost:8000",
        "dev_ui_url": "http://localhost:8000/dev-ui/?app=client_agent",
        "default_timeout": 30,
        "payment_wait_timeout": 15,
        "processing_timeout": 30,
        "screenshot_dir": Path(__file__).parent / "screenshots",
        "logs_dir": Path(__file__).parent / "logs",
    }


@pytest.fixture(autouse=True)
def setup_test_dirs(test_config):
    """
    Ensure test directories exist before each test.

    Creates screenshot and log directories if they don't exist.
    """
    test_config["screenshot_dir"].mkdir(parents=True, exist_ok=True)
    test_config["logs_dir"].mkdir(parents=True, exist_ok=True)


@pytest.fixture
def test_env_vars():
    """
    Provide test environment variables from os.environ or .env.test file.

    First tries to load from .env.test (for local testing), then falls back
    to os.environ (for CI/CD workflows with environment variables set).

    Returns:
        dict: Environment variables for tests
    """
    env_test_path = Path(__file__).parent / ".env.test"

    # Try loading from .env.test file first (local development)
    if env_test_path.exists():
        try:
            from dotenv import dotenv_values

            return dotenv_values(env_test_path)
        except ImportError:
            # Fallback: simple parsing
            env_vars = {}
            with open(env_test_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        env_vars[key.strip()] = value.strip()
            return env_vars

    # Fallback to os.environ (CI/CD workflows)
    env_vars = dict(os.environ)
    print(f"[test_env_vars] Returning environment variables from os.environ")
    print(f"[test_env_vars]   os.environ NVM_API_KEY_CLIENT length: {len(os.environ.get('NVM_API_KEY_CLIENT', ''))}")
    print(f"[test_env_vars]   env_vars NVM_API_KEY_CLIENT length: {len(env_vars.get('NVM_API_KEY_CLIENT', ''))}")
    print(f"[test_env_vars]   os.environ NVM_API_KEY_CLIENT first 50: {os.environ.get('NVM_API_KEY_CLIENT', '')[:50]}")
    print(f"[test_env_vars]   env_vars NVM_API_KEY_CLIENT first 50: {env_vars.get('NVM_API_KEY_CLIENT', '')[:50]}")
    return env_vars


# Pytest configuration hooks
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "e2e: End-to-end integration tests")
    config.addinivalue_line("markers", "slow: Tests that take significant time")
    config.addinivalue_line("markers", "http: HTTP/A2A protocol tests")
    config.addinivalue_line("markers", "browser: Browser automation tests")


def pytest_collection_modifyitems(config, items):
    """Auto-mark tests based on their module/name."""
    for item in items:
        # Auto-mark browser tests as slow
        if "browser" in item.nodeid:
            item.add_marker(pytest.mark.slow)
            item.add_marker(pytest.mark.browser)

        # Auto-mark HTTP tests
        if "http" in item.nodeid:
            item.add_marker(pytest.mark.http)

        # Mark all E2E tests
        if "test_e2e" in item.nodeid:
            item.add_marker(pytest.mark.e2e)
