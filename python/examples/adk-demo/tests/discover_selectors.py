#!/usr/bin/env python3
"""
UI Selector Discovery Tool

Manual script to help discover CSS selectors for browser automation tests.
Run this while agents are running to inspect the dev-ui page and identify
key elements needed for testing.

Usage:
    # Start agents first:
    # Terminal 1: uv run server --port=10000
    # Terminal 2: uv run adk web --port=8000

    # Then run this script:
    uv run python tests/discover_selectors.py
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from browser_helper import BrowserTestHelper


async def discover_selectors():
    """Discover and document UI selectors for testing."""
    screenshot_dir = Path(__file__).parent / "screenshots"
    screenshot_dir.mkdir(exist_ok=True)

    helper = BrowserTestHelper(screenshot_dir=screenshot_dir, headless=False)
    await helper.start()

    print("🔍 UI Selector Discovery Tool")
    print("=" * 60)
    print()

    # Navigate to dev-ui
    dev_ui_url = "http://localhost:8000/dev-ui/?app=client_agent"
    print(f"📍 Navigating to {dev_ui_url}")

    try:
        await helper.navigate_and_wait(dev_ui_url, wait_time=3.0)
        print("✓ Page loaded successfully")
        print()

        # Take initial screenshot
        await helper.screenshot("discovery_initial")
        print("✓ Screenshot saved: discovery_initial.png")
        print()

        # Get page HTML structure
        print("📄 Analyzing page structure...")
        print()

        # Common selectors to check
        selectors_to_check = [
            # Input fields
            ("input[type='text']", "Text input field"),
            ("textarea", "Textarea field"),
            ("input[placeholder]", "Input with placeholder"),
            ("[role='textbox']", "Textbox role element"),
            # Buttons
            ("button", "Button elements"),
            ("[type='submit']", "Submit button"),
            ("[role='button']", "Button role element"),
            # Chat/message containers
            (".message", "Message container (class)"),
            (".chat", "Chat container (class)"),
            ("[role='log']", "Log/chat role"),
            ("[role='list']", "List role (messages)"),
            # Common framework selectors
            ("[data-testid]", "Elements with test IDs"),
            ("[id]", "Elements with IDs"),
        ]

        print("🔎 Checking for common UI elements:")
        print("-" * 60)

        found_selectors = {}

        for selector, description in selectors_to_check:
            exists = await helper.check_element_exists(selector)
            count = await helper.get_element_count(selector)

            status = "✓" if exists else "✗"
            print(f"{status} {description:30} {selector:30} ({count} found)")

            if exists:
                found_selectors[description] = {"selector": selector, "count": count}

        print()
        print("=" * 60)
        print()

        # Get page text content
        print("📝 Page text content (first 500 chars):")
        print("-" * 60)
        page_text = await helper.get_full_page_text()
        print(page_text[:500])
        print()

        # Try to extract specific elements
        print("=" * 60)
        print("🎯 Recommended selectors for testing:")
        print("-" * 60)

        # Try to identify message input
        input_selectors = [
            "input[type='text']",
            "textarea",
            "[role='textbox']",
            "input[placeholder*='message' i]",
            "input[placeholder*='type' i]",
        ]

        for selector in input_selectors:
            if await helper.check_element_exists(selector):
                print(f"📝 Message Input: {selector}")
                found_selectors["message_input"] = selector
                break

        # Try to identify send button
        button_selectors = [
            "button[type='submit']",
            "button:contains('Send')",
            "[role='button']:contains('Send')",
            "button",
        ]

        for selector in button_selectors:
            if await helper.check_element_exists(selector):
                print(f"📤 Send Button: {selector}")
                found_selectors["send_button"] = selector
                break

        # Try to identify message container
        container_selectors = [
            "[role='log']",
            "[role='list']",
            ".messages",
            ".chat",
            "#messages",
        ]

        for selector in container_selectors:
            if await helper.check_element_exists(selector):
                print(f"💬 Message Container: {selector}")
                found_selectors["message_container"] = selector
                break

        print()
        print("=" * 60)
        print()

        # Save findings to file
        output_file = Path(__file__).parent / "discovered_selectors.txt"
        with open(output_file, "w") as f:
            f.write("UI Selectors Discovery Results\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"URL: {dev_ui_url}\n\n")

            f.write("Found Selectors:\n")
            f.write("-" * 60 + "\n")
            for name, info in found_selectors.items():
                if isinstance(info, dict):
                    f.write(f"{name}: {info['selector']} ({info['count']} elements)\n")
                else:
                    f.write(f"{name}: {info}\n")

            f.write("\n\nPage Text Preview:\n")
            f.write("-" * 60 + "\n")
            f.write(page_text[:1000])

        print(f"✓ Results saved to: {output_file}")
        print()

        print("💡 Next steps:")
        print("   1. Check screenshots/ directory for visual reference")
        print("   2. Review discovered_selectors.txt for selector details")
        print("   3. Use browser DevTools to inspect specific elements")
        print("   4. Update test_e2e_browser.py with correct selectors")
        print()

    except Exception as e:
        print(f"❌ Error: {e}")
        print()
        print("Make sure agents are running:")
        print("  Terminal 1: uv run server --port=10000")
        print("  Terminal 2: uv run adk web --port=8000")
        return 1

    finally:
        await helper.close()

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(discover_selectors())
    sys.exit(exit_code)
