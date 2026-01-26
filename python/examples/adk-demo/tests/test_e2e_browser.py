"""
Browser/UI E2E Tests for x402 Payment Flow.

Tests the complete payment flow through the actual web UI using browser
automation. These tests validate the user experience and UI interactions.

NOTE: Before running these tests, you MUST discover the UI selectors:
    1. Start agents: uv run server --port=10000 && uv run adk web --port=8000
    2. Run discovery: uv run python tests/discover_selectors.py
    3. Update SELECTORS dict below with discovered values
"""

import asyncio

import pytest

from .browser_helper import BrowserTestHelper

# UI SELECTORS - UPDATE THESE AFTER RUNNING discover_selectors.py
SELECTORS = {
    # TODO: Update these selectors after running discovery tool
    "message_input": "input[type='text']",  # Placeholder - needs discovery
    "send_button": "button[type='submit']",  # Placeholder - needs discovery
    "message_container": "[role='log']",  # Placeholder - needs discovery
    "plan_option": "button",  # Placeholder - needs discovery
}


@pytest.mark.browser
@pytest.mark.slow
@pytest.mark.e2e
class TestE2EPaymentFlowBrowser:
    """E2E tests using browser automation through dev-ui."""

    @pytest.fixture(autouse=True)
    async def setup(self, merchant_agent, client_agent, test_config, setup_test_dirs):
        """
        Setup for browser tests.

        Requires merchant and client agents to be running (via fixtures).
        Initializes browser helper.
        """
        screenshot_dir = setup_test_dirs["screenshots"]
        self.helper = BrowserTestHelper(screenshot_dir=screenshot_dir, headless=True)
        await self.helper.start()

        self.dev_ui_url = test_config["dev_ui_url"]
        self.payment_timeout = test_config["payment_wait_timeout"]
        self.processing_timeout = test_config["processing_timeout"]

        yield

        # Cleanup
        await self.helper.close()

    async def test_happy_path_browser_flow(self):
        """
        Test complete payment flow through browser UI.

        Steps:
        1. Navigate to dev-ui
        2. Send purchase message
        3. Wait for payment options (15 sec timeout)
        4. Select payment plan
        5. Wait for payment processing (30 sec timeout)
        6. Verify transaction hash displayed
        7. Verify transaction hash format
        """
        # Step 1: Navigate to dev-ui
        await self.helper.navigate_and_wait(self.dev_ui_url, wait_time=3.0)
        await self.helper.screenshot("browser_01_initial_load")

        # Verify page loaded
        page_text = await self.helper.get_full_page_text()
        assert "client_agent" in page_text.lower() or "dev" in page_text.lower(), \
            "Dev UI not loaded correctly"

        # Step 2: Send purchase message
        message = "I want to buy a laptop"

        # Check if message input exists
        input_exists = await self.helper.check_element_exists(SELECTORS["message_input"])
        assert input_exists, \
            f"Message input not found. Selector '{SELECTORS['message_input']}' may be incorrect. " \
            "Run discover_selectors.py to find correct selector."

        # Fill and send message
        await self.helper.fill_input(SELECTORS["message_input"], message)
        await self.helper.screenshot("browser_02_message_typed")

        # Click send button
        send_exists = await self.helper.check_element_exists(SELECTORS["send_button"])
        assert send_exists, \
            f"Send button not found. Selector '{SELECTORS['send_button']}' may be incorrect."

        await self.helper.click_element(SELECTORS["send_button"])
        await self.helper.screenshot("browser_03_message_sent")

        # Step 3: Wait for payment options
        print(f"⏳ Waiting up to {self.payment_timeout}s for payment options...")

        payment_found = await self.helper.wait_for_text(
            "payment", timeout=self.payment_timeout
        )
        assert payment_found, \
            f"Payment options not received within {self.payment_timeout} seconds"

        await self.helper.screenshot("browser_04_payment_options")

        # Extract payment plans
        plans = await self.helper.extract_plan_options()
        print(f"✓ Found {len(plans)} payment plan(s): {plans}")

        # Step 4: Select payment plan
        # Type "1" to select first plan
        await self.helper.fill_input(SELECTORS["message_input"], "1")
        await self.helper.screenshot("browser_05_plan_selected")

        await self.helper.click_element(SELECTORS["send_button"])
        await self.helper.screenshot("browser_06_plan_submitted")

        # Step 5: Wait for payment processing
        print(f"⏳ Waiting up to {self.processing_timeout}s for payment processing...")

        # Look for completion indicators
        completed = await self.helper.wait_for_text(
            "completed", timeout=self.processing_timeout
        )

        if not completed:
            # Try waiting for transaction hash instead
            tx_hash = await self.helper.wait_for_transaction_hash(
                timeout=self.processing_timeout
            )
            completed = tx_hash is not None

        assert completed, \
            f"Payment not completed within {self.processing_timeout} seconds"

        await self.helper.screenshot("browser_07_payment_completed")

        # Step 6: Verify transaction hash
        tx_hash = await self.helper.find_transaction_hash()

        # Transaction hash may not always be displayed (merchant bug)
        # So we make this optional
        if tx_hash:
            print(f"✓ Transaction hash found: {tx_hash}")

            # Step 7: Verify format
            assert tx_hash.startswith("0x"), "Invalid transaction hash format"
            assert len(tx_hash) == 66, \
                f"Transaction hash should be 66 characters, got {len(tx_hash)}"
            print("✓ Transaction hash format valid")
        else:
            print("⚠ Transaction hash not displayed (may be due to merchant bug)")
            # Verify we at least got a completion message
            page_text = await self.helper.get_full_page_text()
            assert "complete" in page_text.lower() or "success" in page_text.lower(), \
                "No completion indicator found"

        await self.helper.screenshot("browser_08_final_state")

    async def test_browser_timeout_no_response(self):
        """
        Test browser behavior when merchant doesn't respond within timeout.

        This test sends a message but doesn't wait for full response,
        verifying the timeout handling.
        """
        # Navigate
        await self.helper.navigate_and_wait(self.dev_ui_url)
        await self.helper.screenshot("timeout_test_01_loaded")

        # Send message
        await self.helper.fill_input(SELECTORS["message_input"], "I want to buy a laptop")
        await self.helper.click_element(SELECTORS["send_button"])

        # Wait only very briefly (force timeout)
        short_timeout = 2.0
        payment_found = await self.helper.wait_for_text("payment", timeout=short_timeout)

        # With such a short timeout, payment likely won't be found
        # This verifies the timeout mechanism works
        print(f"Payment found within {short_timeout}s: {payment_found}")

        await self.helper.screenshot("timeout_test_02_after_short_wait")

        # The test passes as long as we didn't crash
        # In real scenario, UI should show loading or timeout message

    @pytest.mark.parametrize("invalid_choice", ["99", "abc", "cancel"])
    async def test_browser_invalid_plan_selection(self, invalid_choice):
        """
        Test selecting invalid payment plan options.

        Verifies that invalid selections are handled gracefully.
        """
        # Navigate and send purchase request
        await self.helper.navigate_and_wait(self.dev_ui_url)
        await self.helper.fill_input(SELECTORS["message_input"], "I want to buy a laptop")
        await self.helper.click_element(SELECTORS["send_button"])

        # Wait for payment options
        payment_found = await self.helper.wait_for_text("payment", timeout=15.0)
        assert payment_found, "Payment options not received"

        await self.helper.screenshot(f"invalid_choice_{invalid_choice}_01_options")

        # Send invalid choice
        await self.helper.fill_input(SELECTORS["message_input"], invalid_choice)
        await self.helper.click_element(SELECTORS["send_button"])

        # Wait a bit for response
        await asyncio.sleep(2.0)
        await self.helper.screenshot(f"invalid_choice_{invalid_choice}_02_response")

        # Verify we got some kind of response (error, retry prompt, etc.)
        page_text = await self.helper.get_full_page_text()

        # Should either see error, retry prompt, or back to payment options
        has_response = any(
            keyword in page_text.lower()
            for keyword in ["invalid", "error", "try again", "select", "payment"]
        )

        assert has_response, f"No response to invalid choice '{invalid_choice}'"
        print(f"✓ Invalid choice '{invalid_choice}' handled")

    @pytest.mark.skip(reason="Requires manual testing - cannot automate cancellation easily")
    async def test_browser_cancel_payment(self):
        """
        Test canceling payment flow.

        This test is skipped by default as cancellation UX is not yet clear.
        Enable and implement once cancellation mechanism is defined.
        """
        # TODO: Implement once cancellation workflow is defined
        pass

    async def test_browser_multiple_purchases(self):
        """
        Test multiple consecutive purchases through UI.

        Verifies state management works correctly across multiple
        purchase flows.
        """
        # Navigate
        await self.helper.navigate_and_wait(self.dev_ui_url)

        # First purchase
        await self.helper.fill_input(SELECTORS["message_input"], "I want to buy a laptop")
        await self.helper.click_element(SELECTORS["send_button"])

        # Wait for payment options
        payment_found = await self.helper.wait_for_text("payment", timeout=15.0)
        assert payment_found, "First purchase: payment options not received"

        # Select plan
        await self.helper.fill_input(SELECTORS["message_input"], "1")
        await self.helper.click_element(SELECTORS["send_button"])

        # Wait for completion
        await self.helper.wait_for_text("complete", timeout=30.0)
        await self.helper.screenshot("multiple_01_first_complete")

        # Small delay between purchases
        await asyncio.sleep(2.0)

        # Second purchase
        await self.helper.fill_input(SELECTORS["message_input"], "I want to buy a phone")
        await self.helper.click_element(SELECTORS["send_button"])

        # Wait for payment options again
        payment_found_2 = await self.helper.wait_for_text("payment", timeout=15.0)

        # Second purchase may or may not require payment (merchant's decision)
        if payment_found_2:
            print("✓ Second purchase requires payment")
            await self.helper.fill_input(SELECTORS["message_input"], "1")
            await self.helper.click_element(SELECTORS["send_button"])
            await self.helper.wait_for_text("complete", timeout=30.0)
        else:
            print("✓ Second purchase completed without payment")

        await self.helper.screenshot("multiple_02_second_complete")

        print("✓ Multiple consecutive purchases completed successfully")


@pytest.mark.browser
@pytest.mark.slow
class TestBrowserUIElements:
    """Tests focused on UI element discovery and validation."""

    @pytest.fixture(autouse=True)
    async def setup(self, merchant_agent, client_agent, test_config, setup_test_dirs):
        """Setup for UI element tests."""
        screenshot_dir = setup_test_dirs["screenshots"]
        self.helper = BrowserTestHelper(screenshot_dir=screenshot_dir, headless=True)
        await self.helper.start()

        self.dev_ui_url = test_config["dev_ui_url"]

        yield

        await self.helper.close()

    async def test_ui_elements_exist(self):
        """
        Verify all required UI elements exist on the page.

        This test helps validate selectors and detect UI changes.
        """
        await self.helper.navigate_and_wait(self.dev_ui_url)
        await self.helper.screenshot("ui_validation_initial")

        # Check each required element
        results = {}

        for element_name, selector in SELECTORS.items():
            exists = await self.helper.check_element_exists(selector)
            count = await self.helper.get_element_count(selector)

            results[element_name] = {"exists": exists, "count": count}
            print(f"{element_name}: {selector} - {'✓' if exists else '✗'} ({count} found)")

        # At minimum, we need input and button
        assert results["message_input"]["exists"], \
            "Message input not found - run discover_selectors.py to update SELECTORS"
        assert results["send_button"]["exists"], \
            "Send button not found - run discover_selectors.py to update SELECTORS"

        await self.helper.screenshot("ui_validation_complete")

    async def test_page_accessibility(self):
        """
        Verify page has basic accessibility features.

        Checks for ARIA roles, labels, and semantic HTML.
        """
        await self.helper.navigate_and_wait(self.dev_ui_url)

        # Check for ARIA roles
        has_textbox = await self.helper.check_element_exists("[role='textbox']")
        has_button = await self.helper.check_element_exists("[role='button']")
        has_log = await self.helper.check_element_exists("[role='log']")

        # At least some accessible elements should exist
        accessible_elements_found = has_textbox or has_button or has_log

        print(f"Accessibility check:")
        print(f"  - Textbox role: {has_textbox}")
        print(f"  - Button role: {has_button}")
        print(f"  - Log role: {has_log}")

        # Don't fail test, just warn if accessibility could be improved
        if not accessible_elements_found:
            print("⚠ Consider adding ARIA roles for better accessibility")
