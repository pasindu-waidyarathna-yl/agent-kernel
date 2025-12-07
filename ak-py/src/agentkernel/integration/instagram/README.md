# Instagram Integration

Instagram Messaging API integration for Agent Kernel using webhooks.

The `AgentInstagramRequestHandler` class handles conversations with agents via Instagram Messaging API webhooks. This integration uses the Instagram Graph API (https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login) without requiring third-party libraries beyond standard HTTP clients.

## How It Works

1. When a message is received from Instagram, it's verified and authenticated
2. The message text is extracted and passed to your chosen Agent
3. The Agent response is sent back as an Instagram Direct Message
4. Long messages are automatically split to respect Instagram's character limits (1000 characters)

## Instagram API Setup

### Prerequisites

1. A Facebook Developer account
2. An Instagram Professional or Business account
3. A Facebook App with Instagram API enabled

### Configuration Steps

1. **Create a Facebook App**
   - Go to [Facebook Developers](https://developers.facebook.com/)
   - Create a new app and select "Business" or "Consumer" type
   - Add the Instagram API product

2. **Set Up Instagram API with Instagram Login**
   - In your app dashboard, go to Instagram API setup
   - Add required permissions: `instagram_business_basic`, `instagram_manage_comments`, `instagram_business_manage_messages`
   - Add your Instagram account as a tester

3. **Get Your Credentials**
   - **Access Token**: Generate from the Instagram API setup page
   - **App Secret**: Found in App Settings > Basic
   - **Verify Token**: Create your own secure random string for webhook verification

4. **Configure Webhook**
   - Go to Instagram API > Configure Webhooks
   - Set callback URL: `https://your-domain.com/instagram/webhook`
   - Set verify token: Your chosen verify token
   - Subscribe to webhook fields: `messages`, `message_edit`, `messaging_postbacks`

### Required Environment Variables

```bash
export AK_INSTAGRAM__VERIFY_TOKEN="your_verify_token"
export AK_INSTAGRAM__ACCESS_TOKEN="your_instagram_access_token"
export AK_INSTAGRAM__APP_SECRET="your_app_secret"
export AK_INSTAGRAM__API_VERSION="v24.0"  # Optional, defaults to v24.0
```

### Webhook Verification

The handler automatically responds to Instagram's webhook verification challenge via `<hosted URL>/instagram/webhook`. When you configure the webhook URL in Meta's developer portal, Instagram will send a GET request to verify the endpoint.

## Simple Instagram Integration Code

```python
from agents import Agent as OpenAIAgent
from agentkernel.api import RESTAPI
from agentkernel.openai import OpenAIModule
from agentkernel.instagram import AgentInstagramRequestHandler

# Create your agent
general_agent = OpenAIAgent(
    name="general",
    handoff_description="Agent for general questions",
    instructions="You provide assistance with general queries. Give short and clear answers suitable for Instagram DMs.",
)

# Initialize module with agent
OpenAIModule([general_agent])

if __name__ == "__main__":
    handler = AgentInstagramRequestHandler()
    RESTAPI.run([handler])
```

## Configuration Options

### config.yaml

```yaml
instagram:
  agent: "general"  # Name of the agent to handle Instagram messages
  api_version: "v24.0"  # Optional
```

It is strongly recommended not to keep secrets and keys in the config file. Set them as environment variables.

## Features

### Supported Message Types

- **Text Messages**: Standard text messages
- **Story Mentions**: When users mention your account in stories
- **Story Replies**: Replies to your stories
- **Postbacks**: Button clicks and quick replies

### Message Handling

- **Automatic Message Splitting**: Messages longer than 1000 characters are automatically split
- **Session Management**: Uses sender ID as session ID to maintain conversation context
- **Typing Indicator**: Shows typing status while processing
- **Read Receipts**: Marks messages as seen

### Development Mode Workaround

In development mode, Instagram only sends `message_edit` events without full message data. The handler automatically polls the Conversations API to retrieve the actual message content.

### Security

- **Webhook Signature Verification**: All incoming webhooks are verified using HMAC-SHA256
- **Token Authentication**: Uses verify token for webhook setup
- **Secure API Calls**: All API calls use Bearer token authentication

## Testing

### Local Development

For local testing, use a tunneling service to expose your local server:

**Using ngrok:**
```bash
ngrok http 8000
```

**Using pinggy:**
```bash
ssh -p443 -R0:localhost:8000 a.pinggy.io
```

Update your Instagram webhook URL with the tunnel URL.

### Important: Development Mode Limitations

- Your app must be in **published state** to receive webhooks from non-tester accounts
- Add Instagram accounts as **testers** in App Roles to test in development mode
- Testers must accept the invitation in their Instagram settings

### Testing Steps

1. Start your local server
2. Set up the tunnel
3. Configure Instagram webhook with tunnel URL
4. Add test Instagram account as app tester
5. Send a test message to your Instagram account
6. Check logs for request/response flow

## Advanced Usage

### Custom Message Handling

You can extend the handler for custom behavior:

```python
from agentkernel.instagram import AgentInstagramRequestHandler

class CustomInstagramHandler(AgentInstagramRequestHandler):
    async def _handle_message(self, messaging_event: dict):
        message = messaging_event.get("message", {})
        message_text = message.get("text")
        sender_id = messaging_event.get("sender", {}).get("id")

        # Custom logic here
        if message_text and message_text.startswith("/help"):
            await self._send_message(sender_id, "Available commands: /help")
            return

        # Call parent handler
        await super()._handle_message(messaging_event)
```

## Troubleshooting

### Common Issues

**Webhook verification fails:**
- Ensure verify token matches what you set in Meta developer portal
- Check that your endpoint is accessible via HTTPS
- Verify the callback URL is correct

**Webhooks not being received:**
- App must be in published state OR use tester accounts
- Check webhook subscription is active for `messages` field
- Verify app secret and access token are correct
- Review server logs for errors

**Authentication errors:**
- Ensure access token has correct permissions
- Verify access token hasn't expired
- Check app secret is correct

**Messages not sending:**
- Verify access token has `instagram_business_manage_messages` permission
- Check recipient has an open conversation with your account
- Ensure Instagram account is properly connected

### Debug Logging

Enable debug logging to troubleshoot:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## API Rate Limits

Instagram API has rate limits:
- **API Calls**: 200 calls per user per hour
- **Messaging**: Subject to Instagram's messaging policies
- **Webhooks**: Must respond within 20 seconds

## References

- [Instagram API Documentation](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login)
- [Instagram Messaging API](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/messaging-api)
- [Webhook Reference](https://developers.facebook.com/docs/instagram-platform/webhooks)
