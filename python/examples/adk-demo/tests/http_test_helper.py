"""
HTTP test helper utilities for E2E testing via A2A protocol.

Provides helper functions for interacting with agents via HTTP/JSON-RPC
without going through the browser UI.
"""

import uuid
from typing import Any, Dict, List, Optional

import httpx
from payments_py import Payments


class HTTPTestHelper:
    """Helper utilities for HTTP-based E2E tests."""

    def __init__(self, merchant_url: str, payments_client: Payments):
        """
        Initialize HTTP test helper.

        Args:
            merchant_url: Base URL of merchant agent
            payments_client: Payments SDK instance for generating tokens
        """
        self.merchant_url = merchant_url
        self.payments = payments_client
        self.client = httpx.AsyncClient(timeout=30)

    async def send_purchase_request(
        self, product: str, task_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send initial purchase request to merchant.

        Args:
            product: Product description (e.g., "laptop")
            task_id: Optional task ID (generated if not provided)

        Returns:
            dict: JSON-RPC response from merchant
        """
        message_id = str(uuid.uuid4())
        request_id = str(uuid.uuid4())

        message = {
            "messageId": message_id,
            "role": "user",
            "parts": [{"kind": "text", "text": f"I want to buy a {product}"}],
        }

        # Only include taskId if explicitly provided (for continuing conversation)
        if task_id is not None:
            message["taskId"] = task_id

        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "message/send",
            "params": {"message": message},
        }

        response = await self.client.post(self.merchant_url, json=payload)
        return response.json()

    async def submit_payment(
        self,
        task_id: str,
        context_id: str,
        plan_index: int,
        payment_requirements: Dict[str, Any],
        access_token: str,
    ) -> Dict[str, Any]:
        """
        Submit payment for a task.

        Args:
            task_id: Task ID from initial request
            context_id: Context ID from initial response
            plan_index: Index of selected plan (0-based)
            payment_requirements: Payment requirements from payment-required response
            access_token: X402 access token

        Returns:
            dict: JSON-RPC response from merchant with payment result
        """
        message_id = str(uuid.uuid4())

        # Extract selected plan details
        selected_plan = payment_requirements["accepts"][plan_index]

        # Create payment payload
        payment_payload = {
            "x402Version": 2,
            "scheme": "nvm:erc4337",
            "network": selected_plan.get("network", "eip155:84532"),
            "payload": {"sessionKey": access_token},
        }

        # Build request
        request_id = str(uuid.uuid4())

        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "message/send",
            "params": {
                "message": {
                    "messageId": message_id,
                    "taskId": task_id,
                    "contextId": context_id,
                    "role": "user",
                    "parts": [
                        {
                            "kind": "text",
                            "text": f"sign_and_send_payment: {plan_index + 1}",
                        }
                    ],
                    "metadata": {
                        "x402.payment.status": "payment-submitted",
                        "x402.payment.payload": payment_payload,
                    },
                }
            },
        }

        response = await self.client.post(self.merchant_url, json=payload)
        return response.json()

    def extract_payment_requirements(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract payment requirements from response metadata.

        Args:
            response: JSON-RPC response containing payment requirements

        Returns:
            dict: Payment requirements object

        Raises:
            KeyError: If payment requirements not found in response
        """
        result = response.get("result", {})

        # Check in task status message metadata
        status = result.get("status", {})
        status_message = status.get("message", {})
        message_metadata = status_message.get("metadata", {})

        # Try different metadata keys
        if "x402.payment.required" in message_metadata:
            return message_metadata["x402.payment.required"]
        elif "x402.payment.requirements" in message_metadata:
            return message_metadata["x402.payment.requirements"]
        elif "payment_requirements" in message_metadata:
            return message_metadata["payment_requirements"]

        # Also try top-level metadata
        metadata = result.get("metadata", {})
        if "x402.payment.required" in metadata:
            return metadata["x402.payment.required"]
        elif "x402.payment.requirements" in metadata:
            return metadata["x402.payment.requirements"]
        elif "payment_requirements" in metadata:
            return metadata["payment_requirements"]
        else:
            raise KeyError(
                f"Payment requirements not found in response. "
                f"Message metadata keys: {list(message_metadata.keys())}, "
                f"Task metadata keys: {list(metadata.keys())}"
            )

    def extract_payment_status(self, response: Dict[str, Any]) -> str:
        """
        Extract payment status from response metadata.

        Args:
            response: JSON-RPC response

        Returns:
            str: Payment status (e.g., "payment-required", "payment-completed")
        """
        result = response.get("result", {})

        # Check in task status message metadata
        status = result.get("status", {})
        status_message = status.get("message", {})
        message_metadata = status_message.get("metadata", {})

        if "x402.payment.status" in message_metadata:
            return message_metadata["x402.payment.status"]

        # Also try top-level metadata
        metadata = result.get("metadata", {})
        return metadata.get("x402.payment.status", "unknown")

    def extract_transaction_hash(self, response: Dict[str, Any]) -> Optional[str]:
        """
        Extract transaction hash from completed payment response.

        Args:
            response: JSON-RPC response from completed payment

        Returns:
            str or None: Transaction hash if found
        """
        # Transaction hash might be in different places
        result = response.get("result", {})

        # Check metadata
        metadata = result.get("metadata", {})
        if "txHash" in metadata:
            return metadata["txHash"]
        if "transactionHash" in metadata:
            return metadata["transactionHash"]

        # Check in parts (agent response text)
        parts = result.get("parts", [])
        for part in parts:
            if part.get("kind") == "text":
                text = part.get("text", "")
                # Look for hex pattern
                import re

                match = re.search(r"0x[a-fA-F0-9]{64}", text)
                if match:
                    return match.group(0)

        return None

    def get_task_state(self, response: Dict[str, Any]) -> str:
        """
        Get task state from response.

        Args:
            response: JSON-RPC response

        Returns:
            str: Task state (e.g., "input_required", "completed", "working")
        """
        result = response.get("result", {})
        status = result.get("status", {})
        return status.get("state", "unknown")

    async def generate_access_token(
        self, plan_id: str, agent_id: str
    ) -> str:
        """
        Generate X402 access token for payment.

        Args:
            plan_id: Payment plan ID
            agent_id: Agent ID

        Returns:
            str: X402 access token
        """
        token_response = self.payments.x402.get_x402_access_token(
            plan_id=plan_id, agent_id=agent_id
        )
        return token_response

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
