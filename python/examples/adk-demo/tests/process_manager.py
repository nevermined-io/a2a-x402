"""
Process management utilities for starting and stopping merchant and client agents during tests.
"""

import asyncio
import os
import subprocess
import time
from pathlib import Path
from typing import Optional

import httpx


class AgentProcessManager:
    """Manages merchant and client agent processes for testing."""

    def __init__(self, base_dir: Optional[Path] = None):
        """
        Initialize process manager.

        Args:
            base_dir: Base directory for the adk-demo project.
                     Defaults to the parent directory of tests/
        """
        if base_dir is None:
            # Default to python/examples/adk-demo
            self.base_dir = Path(__file__).parent.parent
        else:
            self.base_dir = Path(base_dir)

        self.merchant_process: Optional[subprocess.Popen] = None
        self.client_process: Optional[subprocess.Popen] = None

    async def start_merchant(
        self, port: int = 10000, host: str = "localhost"
    ) -> subprocess.Popen:
        """
        Start merchant agent server.

        Args:
            port: Port to run merchant on (default: 10000)
            host: Host to bind to (default: localhost)

        Returns:
            subprocess.Popen: The merchant process

        Raises:
            RuntimeError: If merchant fails to start or health check fails
        """
        print(f"Starting merchant agent on {host}:{port}...")

        # Build command
        cmd = ["uv", "run", "server", "--host", host, "--port", str(port)]

        # Get test environment
        test_env = self._get_test_env()
        
        # Debug: Check if OPENAI_API_KEY is set
        openai_key_set = "OPENAI_API_KEY" in test_env and test_env["OPENAI_API_KEY"]
        print(f"DEBUG: OPENAI_API_KEY is {'set' if openai_key_set else 'NOT SET'} in test environment")
        
        # Start process
        self.merchant_process = subprocess.Popen(
            cmd,
            cwd=str(self.base_dir),
            env=test_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Wait for health check
        health_url = f"http://{host}:{port}/agents/merchant_agent/.well-known/agent-card.json"
        await self._wait_for_health(health_url, timeout=30, process_name="merchant")

        print(f"✓ Merchant agent started successfully on port {port}")
        return self.merchant_process

    async def start_client(self, port: int = 8000) -> subprocess.Popen:
        """
        Start client agent web UI.

        Args:
            port: Port to run client on (default: 8000)

        Returns:
            subprocess.Popen: The client process

        Raises:
            RuntimeError: If client fails to start or health check fails
        """
        print(f"Starting client agent web UI on port {port}...")

        # Build command
        cmd = ["uv", "run", "adk", "web", "--port", str(port)]

        # Start process
        self.client_process = subprocess.Popen(
            cmd,
            cwd=str(self.base_dir),
            env=self._get_test_env(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Wait for health check (ADK web server root)
        health_url = f"http://localhost:{port}/"
        await self._wait_for_health(health_url, timeout=30, process_name="client")

        print(f"✓ Client agent web UI started successfully on port {port}")
        return self.client_process

    async def _wait_for_health(
        self, url: str, timeout: int = 30, process_name: str = "agent"
    ):
        """
        Wait for service to be healthy by polling URL.

        Args:
            url: URL to check for health
            timeout: Maximum seconds to wait
            process_name: Name of process for error messages

        Raises:
            RuntimeError: If health check times out or process dies
        """
        start_time = time.time()
        last_error = None

        async with httpx.AsyncClient() as client:
            while time.time() - start_time < timeout:
                try:
                    response = await client.get(url, timeout=2.0)
                    if response.status_code < 500:  # Accept any non-5xx response
                        return
                except Exception as e:
                    last_error = str(e)

                # Check if process is still alive
                process = (
                    self.merchant_process
                    if process_name == "merchant"
                    else self.client_process
                )
                if process and process.poll() is not None:
                    # Process has terminated
                    stdout, stderr = process.communicate()
                    raise RuntimeError(
                        f"{process_name} process terminated unexpectedly.\n"
                        f"Return code: {process.returncode}\n"
                        f"Stdout: {stdout}\n"
                        f"Stderr: {stderr}"
                    )

                await asyncio.sleep(0.5)

        raise RuntimeError(
            f"Health check for {process_name} at {url} timed out after {timeout}s. "
            f"Last error: {last_error}"
        )

    def _get_test_env(self) -> dict:
        """
        Get environment variables for test processes.

        Loads from .env.test file if it exists.

        Returns:
            dict: Environment variables
        """
        env = os.environ.copy()

        # Load .env.test if it exists
        env_test_path = self.base_dir / "tests" / ".env.test"
        if env_test_path.exists():
            # Simple .env parser (or use python-dotenv)
            try:
                from dotenv import dotenv_values

                test_env = dotenv_values(env_test_path)
                env.update(test_env)
            except ImportError:
                # Fallback: simple parsing
                with open(env_test_path) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, value = line.split("=", 1)
                            env[key.strip()] = value.strip()

        return env

    def stop_all(self):
        """Stop all running agent processes."""
        if self.merchant_process:
            print("Stopping merchant agent...")
            self.merchant_process.terminate()
            try:
                self.merchant_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.merchant_process.kill()
            self.merchant_process = None
            print("✓ Merchant agent stopped")

        if self.client_process:
            print("Stopping client agent...")
            self.client_process.terminate()
            try:
                self.client_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.client_process.kill()
            self.client_process = None
            print("✓ Client agent stopped")

    def __del__(self):
        """Cleanup: ensure processes are stopped."""
        self.stop_all()
