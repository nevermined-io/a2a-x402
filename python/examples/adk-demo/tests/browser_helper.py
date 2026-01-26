"""
Browser helper utilities for browser-based E2E testing.

Provides wrapper around Playwright for easier browser automation
in tests, with proper sandbox configuration for restricted environments.
"""

import asyncio
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from playwright.async_api import async_playwright, Browser, Page, Error as PlaywrightError


class BrowserTestHelper:
    """Helper class for browser automation in tests using Playwright."""

    def __init__(self, screenshot_dir: Optional[Path] = None, headless: bool = True):
        """
        Initialize browser test helper.

        Args:
            screenshot_dir: Directory to save screenshots (default: tests/screenshots)
            headless: Run browser in headless mode (default: True)
        """
        self.screenshot_dir = screenshot_dir or Path(__file__).parent / "screenshots"
        self.screenshot_dir.mkdir(exist_ok=True)

        self.headless = headless
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.current_url = None

    async def start(self):
        """Start browser and create page."""
        self.playwright = await async_playwright().start()

        # Launch with sandbox disabled (per CLAUDE.md AppArmor config)
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=["--no-sandbox", "--disable-setuid-sandbox"],
        )

        # Create new page
        self.page = await self.browser.new_page()

    async def navigate_and_wait(
        self, url: str, wait_time: float = 2.0
    ) -> None:
        """
        Navigate to URL and wait for page load.

        Args:
            url: URL to navigate to
            wait_time: Additional time to wait after navigation (seconds)
        """
        if not self.page:
            await self.start()

        await self.page.goto(url, wait_until="networkidle")
        self.current_url = url

        # Wait for page to settle
        await asyncio.sleep(wait_time)

    async def get_text_content(self, selector: str = "body") -> str:
        """
        Extract text content from page element.

        Args:
            selector: CSS selector (default: body)

        Returns:
            str: Text content of element
        """
        if not self.page:
            return ""

        try:
            element = await self.page.query_selector(selector)
            if element:
                return await element.inner_text()
        except PlaywrightError:
            pass

        return ""

    async def get_full_page_text(self) -> str:
        """
        Get all text content from the page.

        Returns:
            str: All text from page body
        """
        return await self.get_text_content("body")

    async def screenshot(self, name: str, selector: Optional[str] = None) -> Path:
        """
        Take screenshot of page or element.

        Args:
            name: Screenshot name (without extension)
            selector: Optional CSS selector for element screenshot

        Returns:
            Path: Screenshot file path
        """
        if not self.page:
            raise RuntimeError("Browser not started")

        filepath = self.screenshot_dir / f"{name}.png"

        if selector:
            element = await self.page.query_selector(selector)
            if element:
                await element.screenshot(path=str(filepath))
        else:
            await self.page.screenshot(path=str(filepath))

        return filepath

    async def fill_input(self, selector: str, value: str) -> None:
        """
        Fill input field with value.

        Args:
            selector: CSS selector for input field
            value: Value to fill
        """
        if not self.page:
            raise RuntimeError("Browser not started")

        await self.page.fill(selector, value)

    async def click_element(self, selector: str, timeout: float = 5000) -> None:
        """
        Click an element.

        Args:
            selector: CSS selector for element to click
            timeout: Timeout in milliseconds
        """
        if not self.page:
            raise RuntimeError("Browser not started")

        await self.page.click(selector, timeout=timeout)

    async def press_key(self, key: str) -> None:
        """
        Press a keyboard key.

        Args:
            key: Key to press (e.g., "Enter", "Escape")
        """
        if not self.page:
            raise RuntimeError("Browser not started")

        await self.page.keyboard.press(key)

    async def wait_for_text(
        self, text: str, timeout: float = 15.0, poll_interval: float = 0.5
    ) -> bool:
        """
        Wait for specific text to appear on page.

        Args:
            text: Text to wait for (case-insensitive)
            timeout: Maximum wait time in seconds
            poll_interval: Time between checks in seconds

        Returns:
            bool: True if text found, False if timeout
        """
        start_time = asyncio.get_event_loop().time()

        while (asyncio.get_event_loop().time() - start_time) < timeout:
            page_text = await self.get_full_page_text()

            if text.lower() in page_text.lower():
                return True

            await asyncio.sleep(poll_interval)

        return False

    async def wait_for_selector(
        self, selector: str, timeout: float = 5000, state: str = "visible"
    ) -> bool:
        """
        Wait for element to appear.

        Args:
            selector: CSS selector
            timeout: Timeout in milliseconds
            state: Element state to wait for (visible, attached, hidden)

        Returns:
            bool: True if element found
        """
        if not self.page:
            return False

        try:
            await self.page.wait_for_selector(selector, timeout=timeout, state=state)
            return True
        except PlaywrightError:
            return False

    async def find_transaction_hash(self) -> Optional[str]:
        """
        Search page for transaction hash pattern (0x + 64 hex chars).

        Returns:
            str or None: Transaction hash if found
        """
        page_text = await self.get_full_page_text()
        match = re.search(r"0x[a-fA-F0-9]{64}", page_text)
        return match.group(0) if match else None

    async def wait_for_transaction_hash(
        self, timeout: float = 30.0, poll_interval: float = 1.0
    ) -> Optional[str]:
        """
        Wait for transaction hash to appear on page.

        Args:
            timeout: Maximum wait time in seconds
            poll_interval: Time between checks in seconds

        Returns:
            str or None: Transaction hash if found within timeout
        """
        start_time = asyncio.get_event_loop().time()

        while (asyncio.get_event_loop().time() - start_time) < timeout:
            tx_hash = await self.find_transaction_hash()
            if tx_hash:
                return tx_hash

            await asyncio.sleep(poll_interval)

        return None

    async def check_element_exists(self, selector: str) -> bool:
        """
        Check if element exists on page.

        Args:
            selector: CSS selector

        Returns:
            bool: True if element exists
        """
        if not self.page:
            return False

        element = await self.page.query_selector(selector)
        return element is not None

    async def get_element_count(self, selector: str) -> int:
        """
        Count elements matching selector.

        Args:
            selector: CSS selector

        Returns:
            int: Number of matching elements
        """
        if not self.page:
            return 0

        elements = await self.page.query_selector_all(selector)
        return len(elements)

    async def get_element_attribute(
        self, selector: str, attribute: str
    ) -> Optional[str]:
        """
        Get attribute value from element.

        Args:
            selector: CSS selector
            attribute: Attribute name

        Returns:
            str or None: Attribute value if found
        """
        if not self.page:
            return None

        element = await self.page.query_selector(selector)
        if element:
            return await element.get_attribute(attribute)

        return None

    async def extract_plan_options(self) -> List[str]:
        """
        Extract payment plan options from page text.

        Returns:
            list: List of plan descriptions found
        """
        page_text = await self.get_full_page_text()

        # Look for common payment plan patterns
        plans = []

        # Pattern: "Plan 1:", "Option 1:", "1.", etc.
        plan_matches = re.findall(
            r"(?:Plan|Option)\s+(\d+)[:\.]?\s+([^\n]+)", page_text, re.IGNORECASE
        )
        plans.extend([f"Plan {num}: {desc}" for num, desc in plan_matches])

        # Pattern: Credits-based or pay-as-you-go
        if "credit" in page_text.lower():
            plans.append("Credits-based plan")
        if "pay" in page_text.lower() and "go" in page_text.lower():
            plans.append("Pay-as-you-go plan")

        return plans

    async def close(self):
        """Close browser and cleanup."""
        if self.page:
            await self.page.close()
            self.page = None

        if self.browser:
            await self.browser.close()
            self.browser = None

        if self.playwright:
            await self.playwright.stop()
            self.playwright = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
