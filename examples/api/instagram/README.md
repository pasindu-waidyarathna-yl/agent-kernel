# Instagram Messaging Integration Example

This example demonstrates how to create an Instagram Messaging Platform integration with Agent Kernel.

## Prerequisites

1. Facebook Developer Account
2. Facebook App with Instagram product added
3. Instagram Business or Creator Account connected to a Facebook Page
4. Webhook configured in Facebook Developer Portal
5. Required credentials (see below)

## Setup

### 1. Get Instagram Messaging Credentials

Follow the setup guide in [AgentInstagramRequestHandler](../../../ak-py/src/agentkernel/integration/instagram/README.md)

You'll need:
- Page Access Token (for your Instagram-connected Facebook Page)
- App Secret (optional but recommended)
- Verify Token (you create this)

### 2. Configure Environment Variables

Create a `.env` file or export these variables:

```bash
export AK_INSTAGRAM__VERIFY_TOKEN="your_secure_verify_token"
export AK_INSTAGRAM__ACCESS_TOKEN="your_page_access_token"
export AK_INSTAGRAM__APP_SECRET="your_app_secret"
export AK_INSTAGRAM__API_VERSION="v24.0"  # Optional, defaults to v24.0

# OpenAI API Key for the agent
export OPENAI_API_KEY="your_openai_api_key"
```

### 3. Create Configuration File

Create `config.yaml`:

```yaml
instagram:
  agent: "general"
  api_version: "v24.0"
```

## Build

Install dependencies using:

```bash
./build.sh
```

For local development with Agent Kernel source:

```bash
./build.sh local
```

## Run

Start the server:

```bash
uv run server.py
```

The server will start on `http://localhost:8000` by default.

## Expose Local Server

For local testing, expose your server using a tunnel:

### Using ngrok:
```bash
ngrok http 8000
```

### Using pinggy:
```bash
ssh -p443 -R0:localhost:8000 a.pinggy.io
```


Copy the HTTPS URL and configure it in your Instagram webhook settings.

## Configure Instagram Webhook

1. Go to [https://developers.facebook.com/apps](https://developers.facebook.com/apps)
2. Select your app
3. Go to Instagram > Configuration
4. In the "Webhooks" section, click "Edit"
5. Enter:
   - **Callback URL**: `https://your-tunnel-url.com/instagram/webhook`
   - **Verify Token**: Same as `AK_INSTAGRAM__VERIFY_TOKEN`
6. Click "Verify and Save"
7. Subscribe to these webhook fields:
   - `messages` - Incoming direct messages
   - `messaging_postbacks` - Button/quick reply interactions
   - `message_echoes` - Messages sent by your bot (optional)
   - `message_reads` - Read receipts (optional)

## Testing

### Development Mode Testing (Limited)

While in development mode, you can only test with approved test users:

1. Add test users in App Dashboard → Roles → Test Users
2. Send messages from test Instagram accounts
3. **Note**: Bot will receive messages but **CANNOT respond** in development mode
4. You'll see messages in server logs only

### Complete Testing (After Publishing)

After publishing your app to live mode:

1. Open Instagram mobile app
2. Send a message to your bot from ANY Instagram account
3. The bot will:
   - Mark the message as seen
   - Display a typing indicator
   - **Send the agent's response** ✅
4. Check server logs to see the request/response flow


### Test Message Examples

```
Hello
What can you help me with?
Tell me about your services
Can you answer technical questions?
```

## Advanced Examples

### Custom Message Handler

See `example_custom_handler.py` for extending the handler with custom logic:

```python
from agentkernel.instagram import AgentInstagramRequestHandler

class CustomInstagramHandler(AgentInstagramRequestHandler):
    async def _handle_message(self, messaging_event: dict):
        # Custom preprocessing
        message = messaging_event.get("message", {})
        text = message.get("text", "")
        sender_id = messaging_event["sender"]["id"]
        
        # Handle commands
        if text.startswith("/start"):
            await self._send_message(sender_id, "Welcome! How can I help you?")
            return
        
        # Default behavior
        await super()._handle_message(messaging_event)
```

### Multi-Agent Setup

```python
# Create specialized agents
support_agent = OpenAIAgent(
    name="support",
    handoff_description="Customer support agent",
    instructions="Provide helpful customer support responses optimized for Instagram DMs."
)

sales_agent = OpenAIAgent(
    name="sales",
    handoff_description="Sales inquiry agent",
    instructions="Help with product information and sales inquiries on Instagram."
)

# Initialize with multiple agents
OpenAIModule([support_agent, sales_agent])
```

## Troubleshooting

### Webhook Verification Fails

- Ensure verify token in config matches Facebook Developer Portal
- Check that your endpoint is accessible via HTTPS
- Verify the callback URL is correct
- Ensure server is running before verification

### No Messages Received

- Verify your Instagram account is a Business or Creator account
- Check that the Instagram account is connected to a Facebook Page
- Ensure webhook subscription is active
- Verify page is subscribed to webhook events
- Check that the app has required permissions
- Review server logs for errors
- Check webhook subscriptions in Facebook Developer Portal

### Agent Not Responding

- Verify OpenAI API key is set correctly
- Check agent configuration in config.yaml
- Review server logs for agent errors
- Ensure agent name matches configuration

### Messages Not Sending

- Verify access token is a **page access token**, not user token
- Check token has `instagram_manage_messages` permission
- Ensure the Instagram account is connected to the Facebook Page
- Review Facebook Business Suite for restrictions
- Check server logs for API errors
- Verify the recipient has messaged you within 24 hours (messaging window)

### Signature Verification Fails

- Ensure APP_SECRET is set correctly
- Verify the secret matches your Facebook app
- Check that the webhook payload hasn't been modified in transit

### Rate Limiting

If you hit rate limits:
- Implement message queuing
- Add retry logic with exponential backoff
- Monitor rate limit headers in API responses
- Consider applying for higher tier access

### Instagram-Specific Issues

**Account Type**: 
- Only Instagram Business and Creator accounts support messaging API
- Personal accounts cannot use the Instagram Messaging API
- Convert your account in Instagram settings

**Page Connection**:
- Instagram account must be connected to a Facebook Page
- Verify connection in Facebook Business Suite
- Ensure the Page has proper admin access

**Messaging Window**:
- Standard messaging has a 24-hour response window
- After 24 hours, you need message tags or user consent
- Plan your bot's response time accordingly

## Production Deployment

For production deployment:

1. **Use HTTPS**: Deploy behind nginx or similar with SSL certificate
2. **Environment Variables**: Use secure secret management (AWS Secrets Manager, HashiCorp Vault, etc.)
3. **Monitoring**: Add comprehensive logging and alerting (CloudWatch, Datadog, etc.)
4. **Scaling**: Use containerization and orchestration (Docker, Kubernetes)
5. **Error Handling**: Implement robust error handling and retries
6. **Rate Limiting**: Implement rate limiting and message queuing
7. **Get App Reviewed**: Complete Facebook app review before going live
8. **Database**: Use persistent storage for conversation history
9. **Load Balancing**: Distribute traffic across multiple instances
10. **Health Checks**: Implement health check endpoints

### Facebook App Review

Before going live with your app:

1. **Complete Platform Policy Review**
   - Review Facebook Platform Policies
   - Review Instagram Platform Policies
   - Ensure compliance with data handling requirements

2. **Submit for Review**
   - Request `instagram_manage_messages` permission
   - Request `instagram_basic` permission
   - Provide test credentials and detailed instructions
   - Submit screencast demonstrating functionality
   - Wait for approval (typically 3-5 business days)

3. **Switch to Live Mode**
   - After approval, switch app from development to live mode
   - Update webhook URLs if needed
   - Monitor for issues

### Deployment Architectures

See deployment documentation for:
- AWS Lambda + API Gateway (serverless)
- AWS ECS/EKS (containerized)
- Google Cloud Run
- Azure Container Apps

## Instagram-Specific Features

### Message Types

The integration handles these message types:

**Text Messages**:
```python
{
  "message": {
    "mid": "message-id",
    "text": "Hello!"
  }
}
```
### Message Limits

- **Maximum length**: 1000 characters (vs 2000 for Messenger)
- Messages are automatically split if longer
- Consider this when designing agent responses

## Differences from Messenger

Instagram Messaging API has some differences from Messenger:

| Feature | Instagram | Messenger |
|---------|-----------|-----------|
| Message length | 1000 chars | 2000 chars |
| Rich templates | Limited | Extensive |
| Persistent menu | No | Yes |
| Account type | Business/Creator only | Any page |
| Story integration | Yes | No |

## Resources

- [Instagram Messaging API Documentation](https://developers.facebook.com/docs/messenger-platform/instagram)
- [Instagram Graph API Reference](https://developers.facebook.com/docs/instagram-api)
- [Webhook Reference](https://developers.facebook.com/docs/messenger-platform/webhooks)
- [Platform Policy](https://developers.facebook.com/docs/messenger-platform/policy-overview)
- [Agent Kernel Documentation](../../../docs/)
- [Instagram Integration Guide](../../../ak-py/src/agentkernel/integration/instagram/README.md)

