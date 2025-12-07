
# Instagram

Deploy your Agent Kernel agents as Instagram Messaging bots that can respond to direct messages in real-time. This integration connects your AI agents directly to Instagram DMs, enabling natural conversations with users through one of the world's most popular visual and messaging platforms.

## Overview

The `AgentInstagramRequestHandler` provides a seamless bridge between your Agent Kernel agents and Instagram Direct Messages. When users message your Instagram Business or Creator account, their messages are automatically routed to your AI agent, which processes them and sends intelligent responses back through Instagram.

**How it works:**

1. **User sends a message** to your Instagram Business/Creator account via Direct Messages
2. **Message is verified** using Facebook's security protocols (HMAC-SHA256)
3. **Visual feedback** is sent (message marked as seen, typing indicator appears)
4. **Agent processes** the message and generates a response
5. **Response is delivered** back to the user in Instagram DMs

The integration handles all the complexity of the Instagram Messaging API, including webhook verification, signature validation, message deduplication, and the unique message_edit events that Instagram sends.

## Key Features

- 🔐 **Secure Communication**: HMAC-SHA256 signature verification ensures all messages are authentic
- 💬 **Text Messaging**: Full support for text-based conversations in Instagram Direct Messages
- ⚡ **Real-time Feedback**: Automatic "seen" receipts and typing indicators for better user experience
- 🔄 **Session Management**: Maintains conversation context using Instagram-Scoped IDs (IGSID)
- 📊 **Message Splitting**: Automatically handles responses by splitting them at Instagram's 1000-character limit
- 🎯 **Event Handling**: Processes various Instagram events including messages, message edits, and postbacks

## Quick Start

### Prerequisites

Before you begin, you'll need:

- A [Facebook Developer account](https://developers.facebook.com/)
- An **Instagram Business or Creator account** (personal accounts are not supported)
- A Facebook Page connected to your Instagram account
- A Facebook App with Instagram product added
- A publicly accessible HTTPS endpoint (for webhook)

### 1. Set Up Your Facebook App

**Create your app:**

1. Visit the [Facebook Developers Portal](https://developers.facebook.com/apps)
2. Click "Create App" and select "Business" as the app type
3. Fill in your app details and create the app
4. From the dashboard, click "Add Product" and select "Instagram"

**Connect your Instagram account:**

1. In your app dashboard, go to **Use cases** → **Instagram messaging** → **Customise**
2. Click **API Setup**
3. Under "Add Instagram account", click **Add account**
4. Log in with your Instagram Business or Creator account
5. Authorize the connection

### 2. Get Your Credentials

**Generate a Page Access Token:**

1. In **Instagram API Setup**, find "Instagram account" section
2. Click **Generate token** next to your Instagram account
3. Copy and save this token securely - you'll need it as `AK_INSTAGRAM__ACCESS_TOKEN`

**Get your App Secret (recommended):**

1. Go to **App Settings** → **Basic** in the left sidebar
2. Click **Show** next to "App Secret"
3. Copy and save this secret - you'll use it as `AK_INSTAGRAM__APP_SECRET`

**Create a Verify Token:**

This is a random string you create yourself for webhook verification:
```bash
openssl rand -hex 32
```
Save this as `AK_INSTAGRAM__VERIFY_TOKEN`

### 3. Configure Environment Variables

Set these environment variables before starting your application:

```bash
export AK_INSTAGRAM__VERIFY_TOKEN="your_random_verify_token"
export AK_INSTAGRAM__ACCESS_TOKEN="your_page_access_token"
export AK_INSTAGRAM__APP_SECRET="your_app_secret"  \# Optional but recommended
export AK_INSTAGRAM__API_VERSION="v24.0"  \# Optional, defaults to v24.0

# OpenAI API Key for the agent

export OPENAI_API_KEY="your_openai_api_key"
```

### 4. Set Up Your Webhook

**For local development**, use a tunneling service to expose your local server:

```bash
# Using ngrok
ngrok http 8000

# Using pinggy
ssh -p443 -R0:localhost:8000 a.pinggy.io
```

**Configure the webhook in Facebook:**

1. In **Instagram API Setup**, scroll to "Configure webhooks"
2. Enter your webhook URL: `https://your-domain.com/instagram/webhook`
3. Enter your verify token (the one you created above)
4. Click **Verify and Save**

**Subscribe to webhook events:**

Under "Webhook fields", subscribe to:
- `messages` - To receive user direct messages (required)
- `message_reactions` - To receive message reactions
- `messaging_postbacks` - To handle button clicks
- `message_edit` - Instagram sends these for new messages (auto-subscribed)

## Implementation

### Basic Setup

Here's a complete example to get your Instagram bot running:

```bash
from agents import Agent as OpenAIAgent
from agentkernel.api import RESTAPI
from agentkernel.openai import OpenAIModule
from agentkernel.instagram import AgentInstagramRequestHandler

# Create your AI agent

instagram_agent = OpenAIAgent(
name="general",
handoff_description="Helpful Instagram assistant",
instructions="""You are a friendly assistant on Instagram Direct Messages.
- Keep responses very concise (Instagram users expect quick replies)
- Maximum 1000 characters per message
- Use emojis sparingly but appropriately
- Be conversational and casual
- Remember this is a mobile-first platform"""
)

# Initialize the module with your agent

OpenAIModule([instagram_agent])

# Start the server with Instagram integration

if __name__ == "__main__":
handler = AgentInstagramRequestHandler()
RESTAPI.run([handler])
```

### Configuration File

Optionally configure your agent and API settings in `config.yaml`:

```bash
instagram:
agent: "general"  \# Which agent handles Instagram messages
api_version: "v24.0"  \# Instagram Graph API version

```

**Security Note:** Never store tokens or secrets in configuration files. Always use environment variables for sensitive credentials.

## Testing Your Integration

### Development Mode Testing (Limited)

While in development mode, you can only receive messages (not send responses):

1. Add test users in App Dashboard → Roles → Test Users
2. Send messages from test Instagram accounts to your bot
3. **Bot will receive** messages and you'll see them in server logs
4. **Note**: Bot **CANNOT respond** in development mode ❌

### Full Testing (After Publishing)

After publishing your app to live mode:

1. Open Instagram mobile app
2. Go to your bot's Instagram profile
3. Tap "Message" button
4. Send a test message
5. Observe:
   - ✅ Message marked as "Seen"
   - ✅ Typing indicator appears
   - ✅ **Bot sends response**

### Test Message Examples

```bash
Hello
What can you do?
Tell me about your services
Help
```

## Advanced Usage

### Custom Message Handling

Extend the handler to add custom logic, commands, or preprocessing:

```bash
from agentkernel.instagram import AgentInstagramRequestHandler

class CustomInstagramHandler(AgentInstagramRequestHandler):
async def _handle_message(self, messaging_event: dict):
message = messaging_event.get("message", {})
message_text = message.get("text", "").strip()
sender_id = messaging_event.get("sender", {}).get("id")

        # Handle special commands
        if message_text.startswith("/"):
            await self._handle_command(message_text, sender_id)
            return
        
        # Continue with normal processing
        await super()._handle_message(messaging_event)
    
    async def _handle_command(self, command: str, sender_id: str):
        """Handle custom commands"""
        await self._mark_seen(sender_id)
        await self._send_typing_indicator(sender_id, True)
        
        if command == "/help":
            help_text = """🤖 Available Commands:
    /help - Show this message
/start - Start new conversation

Just message me normally to chat!"""
await self._send_message(sender_id, help_text)
elif command == "/start":
await self._send_message(
sender_id,
"👋 Hey! I'm here to help. What would you like to know?"
)
else:
await self._send_message(
sender_id,
f"Unknown command. Try /help"
)

        await self._send_typing_indicator(sender_id, False)
    
# Use your custom handler

if __name__ == "__main__":
handler = CustomInstagramHandler()
RESTAPI.run([handler])
```

### Multi-Agent Setup

Route different types of conversations to specialized agents:

```bash
# Create specialized agents for Instagram

customer_service = OpenAIAgent(
name="customer_service",
handoff_description="Customer support specialist",
instructions="You are a customer service agent on Instagram. Keep responses concise and friendly."
)

product_expert = OpenAIAgent(
name="product_expert",
handoff_description="Product information specialist",
instructions="You help customers learn about products on Instagram. Use bullet points for clarity."
)

general_chat = OpenAIAgent(
name="general",
handoff_description="General conversation handler",
instructions="You handle general Instagram DM conversations. Be friendly and engaging."
)

OpenAIModule([customer_service, product_expert, general_chat])

# Configure which agent to use in config.yaml
```

## Troubleshooting

### Webhook Verification Issues

**Problem:** "Webhook verification failed" error

**Solutions:**
- Ensure verify token exactly matches between environment variable and Facebook entry
- Verify server is running and accessible via HTTPS
- Check webhook URL path is `/instagram/webhook`
- Review server logs for incoming verification request

### No Messages Received

**Problem:** Webhook verified but messages don't reach agent

**Solutions:**
- Verify Instagram account is Business or Creator type
- Check Instagram account is connected to Facebook Page
- Ensure webhook subscription is active for `messages`
- Review server logs for incoming webhook requests
- Verify app isn't still in development mode

### Signature Verification Fails

**Problem:** "Invalid signature" errors

**Solutions:**
- Verify `AK_INSTAGRAM__APP_SECRET` matches your app's actual secret
- Ensure app secret hasn't been regenerated
- Check webhook payloads haven't been modified in transit

### Rate Limiting

If you hit rate limits:
- Implement message queuing
- Add retry logic with exponential backoff
- Monitor rate limit headers in API responses

**Instagram Rate Limits:**
```bash
- 200 API calls per hour per user
- 4,800 API calls per hour per app
- 100,000 API calls per day per app
- 1000 character limit per message
- 24-hour messaging window
```

### Enable Debug Logging

For detailed troubleshooting:

```bash
import logging

logging.basicConfig(
level=logging.DEBUG,
format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

## Production Deployment

### Pre-Launch Checklist

Before deploying to production:

1. ✅ **Complete Facebook App Review**
   - Request required permissions
   - Submit app for review with documentation
   - Wait for approval (3-5 business days)

2. ✅ **Security Measures**
   - Use environment variables for all secrets
   - Enable app secret verification
   - Implement HTTPS with valid SSL certificate
   - Use secure secret management

3. ✅ **Infrastructure**
   - Deploy behind a reverse proxy (nginx, Apache)
   - Set up load balancing for high traffic
   - Implement health checks and monitoring
   - Configure auto-scaling if using cloud services

4. ✅ **Monitoring & Logging**
   - Set up centralized logging (CloudWatch, Datadog)
   - Configure alerts for errors and anomalies
   - Track conversation metrics
   - Monitor API rate limits

5. ✅ **Compliance**
   - Review Facebook and Instagram Platform Policies
   - Ensure GDPR/CCPA compliance
   - Implement data retention policies
   - Provide data deletion capabilities

### Deployment Architecture

For production deployments, consider:

**Serverless (AWS Lambda):**
- Cost-effective for low-to-medium traffic
- Auto-scaling built-in

**Containerized (Docker/Kubernetes):**
- Better for high traffic
- Full control over environment

**Traditional Server:**
- Simple deployment for small-scale
- Use systemd or supervisor for process management

## Supported Message Types

### Text Messages
Standard text messages are fully supported with automatic context management and deduplication.

### Message Edits
Instagram sends `message_edit` events with `num_edit=0` for NEW messages (not actual edits). The integration automatically handles this by fetching the actual message content.

### Postbacks
Handle button clicks and quick reply selections. Postbacks are processed as text using the button title or payload.



## Instagram vs Messenger Comparison

| Feature | Instagram | Messenger |
|---------|-----------|-----------|
| **Message Limit** | 1000 characters | 2000 characters |
| **User Identifier** | Instagram-Scoped ID (IGSID) | Page-Scoped ID (PSID) |
| **Account Type** | Business/Creator only | Any page |
| **Rich Templates** | Limited | Extensive |
| **Persistent Menu** | No | Yes |

## Example Projects

Complete working examples:

- **Basic Example**: `examples/api/instagram/server.py`

## Additional Resources

- [Instagram Messaging API Documentation](https://developers.facebook.com/docs/messenger-platform/instagram)
- [Instagram Graph API Reference](https://developers.facebook.com/docs/instagram-api)
- [Webhook Reference](https://developers.facebook.com/docs/messenger-platform/webhooks)
- [App Review Process](https://developers.facebook.com/docs/app-review)
- [Facebook for Developers](https://developers.facebook.com/)

## Getting Help

If you encounter issues:

1. Check the [troubleshooting section](#troubleshooting) above
2. Enable debug logging to see detailed information
3. Review the Instagram Messaging API documentation
4. Check the [Agent Kernel GitHub Issues](https://github.com/yaalalabs/agent-kernel/issues)
5. Visit the [Facebook Developer Community](https://developers.facebook.com/community/)

