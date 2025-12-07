import asyncio
import hashlib
import hmac
import logging
import traceback
from datetime import datetime

import httpx
from fastapi import APIRouter, HTTPException, Request

from ...api import RESTRequestHandler
from ...core import AgentService, Config


class AgentInstagramRequestHandler(RESTRequestHandler):
    """
    Instagram Messaging API handler using Agent Kernel.

    Endpoints:
    - GET /health: Health check
    - GET /instagram/webhook: Webhook verification
    - POST /instagram/webhook: Handle incoming Instagram messages
    """

    def __init__(self):
        self._log = logging.getLogger("ak.api.instagram")
        self._instagram_agent = Config.get().instagram.agent if Config.get().instagram.agent != "" else None
        self._verify_token = Config.get().instagram.verify_token
        self._access_token = Config.get().instagram.access_token
        self._app_secret = Config.get().instagram.app_secret
        self._api_version = Config.get().instagram.api_version or "v24.0"
        self._base_url = f"https://graph.instagram.com/{self._api_version}"
        self._ig_account_id = getattr(Config.get().instagram, "account_id", "17841411831721478")

        # Message deduplication
        self._processed_message_ids = set()
        self._processed_message_lock = asyncio.Lock()

        if not all([self._access_token, self._verify_token]):
            self._log.error("Instagram configuration incomplete. Set access_token and verify_token.")
            raise ValueError("Incomplete Instagram configuration.")

    def get_router(self) -> APIRouter:
        """Returns the APIRouter instance."""
        router = APIRouter()

        @router.get("/health")
        def health():
            return {"status": "ok"}

        @router.get("/instagram/webhook")
        async def verify_webhook(request: Request):
            return await self._verify_webhook(request)

        @router.post("/instagram/webhook")
        async def handle_webhook(request: Request):
            return await self._handle_webhook(request)

        return router

    async def _verify_webhook(self, request: Request):
        """Verify webhook with Instagram."""
        mode = request.query_params.get("hub.mode")
        token = request.query_params.get("hub.verify_token")
        challenge = request.query_params.get("hub.challenge")

        if mode == "subscribe" and token == self._verify_token and challenge:
            self._log.info("Webhook verified successfully")
            return int(challenge)

        self._log.warning("Webhook verification failed")
        raise HTTPException(status_code=403, detail="Verification failed")

    def _verify_signature(self, payload: bytes, signature: str) -> bool:
        """Verify webhook signature from Instagram."""
        if not signature.startswith("sha256="):
            return False

        expected_signature = hmac.new(self._app_secret.encode(), payload, hashlib.sha256).hexdigest()
        received_signature = signature[7:]
        return hmac.compare_digest(expected_signature, received_signature)

    async def _handle_webhook(self, request: Request):
        """Handle incoming Instagram webhook events."""
        body_bytes = await request.body()

        # Verify signature if configured
        if self._app_secret:
            signature = request.headers.get("x-hub-signature-256", "")
            if signature and not self._verify_signature(body_bytes, signature):
                self._log.warning("Invalid request signature")
                raise HTTPException(status_code=403, detail="Invalid signature")

        # Process webhook
        try:
            import json

            body = json.loads(body_bytes)

            if body.get("object") == "instagram":
                for entry in body.get("entry", []):
                    for messaging_event in entry.get("messaging", []):
                        if "message" in messaging_event:
                            await self._handle_message(messaging_event)
                        elif "message_edit" in messaging_event:
                            await self._handle_message_edit(messaging_event)
                        elif "postback" in messaging_event:
                            await self._handle_postback(messaging_event)
                        elif "read" in messaging_event:
                            # Skip read receipts
                            pass
                        elif "delivery" in messaging_event:
                            # Skip delivery confirmations
                            pass

        except Exception as e:
            self._log.error(f"Error processing webhook: {e}\n{traceback.format_exc()}")

        return {"status": "ok"}

    async def _handle_message(self, messaging_event: dict):
        """Handle an individual Instagram message."""
        sender_id = messaging_event.get("sender", {}).get("id")
        message = messaging_event.get("message", {})
        message_id = message.get("mid")
        message_text = message.get("text")
        is_echo = message.get("is_echo", False)

        # Skip echo messages and bot's own messages
        if is_echo or sender_id == self._ig_account_id:
            return

        if not sender_id or not message_id or not message_text:
            return

        await self._process_agent_message(sender_id, message_text, message_id)

    async def _handle_message_edit(self, messaging_event: dict):
        """Handle message_edit events (Instagram sends num_edit=0 for new messages)."""
        message_edit = messaging_event.get("message_edit", {})
        message_id = message_edit.get("mid")
        num_edit = message_edit.get("num_edit", 0)
        message_text = message_edit.get("text")
        sender_id = messaging_event.get("sender", {}).get("id")
        timestamp = messaging_event.get("timestamp")

        # Skip already processed messages
        if message_id:
            async with self._processed_message_lock:
                if message_id in self._processed_message_ids:
                    return

        # New message (num_edit=0) - fetch from API
        if num_edit == 0 and not message_text:
            result = await self._get_latest_message(expected_sender_id=sender_id, expected_timestamp=timestamp)
            if result:
                sender_id, message_text, fetched_mid = result
                await self._process_agent_message(sender_id, message_text, fetched_mid)
        # Actual edit
        elif num_edit > 0 and message_text and sender_id:
            await self._process_agent_message(sender_id, message_text, message_id)

    async def _get_latest_message(self, expected_sender_id: str = None, expected_timestamp: int = None):
        """Get the latest message from conversations API."""
        await asyncio.sleep(1.5)  # Allow Instagram to index

        url = f"{self._base_url}/{self._ig_account_id}/conversations"
        headers = {"Authorization": f"Bearer {self._access_token}"}
        params = {"fields": "id,messages.limit(20){id,message,from,created_time}", "platform": "instagram"}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers, params=params)

                if response.status_code != 200:
                    self._log.error(f"Failed to fetch conversations: {response.status_code}")
                    return None

                data = response.json()
                conversations = data.get("data", [])

                if not conversations:
                    return None

                expected_time_seconds = expected_timestamp / 1000 if expected_timestamp else None

                # Find matching message
                for conv in conversations:
                    messages = conv.get("messages", {}).get("data", [])
                    for msg in messages:
                        sender = msg.get("from", {})
                        sender_id = sender.get("id")
                        message_text = msg.get("message")
                        created_time = msg.get("created_time")
                        msg_id = msg.get("id")

                        if not sender_id or sender_id == self._ig_account_id or not message_text:
                            continue

                        if expected_sender_id and sender_id != expected_sender_id:
                            continue

                        # Check timestamp match
                        if expected_time_seconds and created_time:
                            msg_time = datetime.fromisoformat(created_time.replace("Z", "+00:00")).timestamp()
                            if abs(msg_time - expected_time_seconds) > 30:
                                continue

                        return (sender_id, message_text, msg_id)

                return None

        except Exception as e:
            self._log.error(f"Error fetching latest message: {e}")
            return None

    async def _handle_postback(self, messaging_event: dict):
        """Handle postback events (button clicks, quick replies)."""
        sender_id = messaging_event.get("sender", {}).get("id")
        postback = messaging_event.get("postback", {})
        payload = postback.get("payload")
        title = postback.get("title")

        if not sender_id:
            return

        message_text = title or payload
        if not message_text:
            return

        await self._process_agent_message(sender_id, message_text, None)

    async def _process_agent_message(self, sender_id: str, message_text: str, message_id: str = None):
        """Process message using configured agent."""
        # Deduplication check
        if message_id:
            async with self._processed_message_lock:
                if message_id in self._processed_message_ids:
                    return

                self._processed_message_ids.add(message_id)

                # Keep set size manageable
                if len(self._processed_message_ids) > 100:
                    self._processed_message_ids.pop()

        service = AgentService()
        session_id = sender_id

        try:
            await self._mark_seen(sender_id)
            await self._send_typing_indicator(sender_id, True)

            # Run agent
            service.select(session_id=session_id, name=self._instagram_agent)
            if not service.agent:
                self._log.warning(f"No agent available: {self._instagram_agent}")
                await self._send_message(sender_id, "Sorry, no agent is available.")
                await self._send_typing_indicator(sender_id, False)
                return

            result = await service.run(message_text)
            response_text = str(result.raw) if hasattr(result, "raw") else str(result)

            await self._send_typing_indicator(sender_id, False)
            await self._send_message(sender_id, response_text)

        except Exception as e:
            self._log.error(f"Error handling message: {e}\n{traceback.format_exc()}")
            await self._send_typing_indicator(sender_id, False)
            await self._send_message(sender_id, "Sorry, there was an error processing your request.")

    async def _send_message(self, recipient_id: str, text: str):
        """Send Instagram message using Send API."""
        url = f"{self._base_url}/me/messages"
        headers = {"Authorization": f"Bearer {self._access_token}", "Content-Type": "application/json"}

        # Split if exceeds Instagram's 1000 char limit
        max_length = 1000
        messages = [text[i : i + max_length] for i in range(0, len(text), max_length)]

        async with httpx.AsyncClient(timeout=5.0) as client:
            for message_text in messages:
                payload = {
                    "recipient": {"id": recipient_id},
                    "message": {"text": message_text},
                }

                try:
                    response = await client.post(url, json=payload, headers=headers)
                    response.raise_for_status()
                except Exception as e:
                    self._log.error(f"Error sending message: {e}")
                    raise

    async def _send_typing_indicator(self, recipient_id: str, typing_on: bool = True):
        """Send typing indicator."""
        url = f"{self._base_url}/me/messages"
        headers = {"Authorization": f"Bearer {self._access_token}", "Content-Type": "application/json"}

        payload = {
            "recipient": {"id": recipient_id},
            "sender_action": "typing_on" if typing_on else "typing_off",
        }

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
        except Exception as e:
            self._log.warning(f"Failed to send typing indicator: {e}")

    async def _mark_seen(self, recipient_id: str):
        """Mark message as seen."""
        url = f"{self._base_url}/me/messages"
        headers = {"Authorization": f"Bearer {self._access_token}", "Content-Type": "application/json"}

        payload = {"recipient": {"id": recipient_id}, "sender_action": "mark_seen"}

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
        except Exception as e:
            self._log.warning(f"Failed to mark message as seen: {e}")
