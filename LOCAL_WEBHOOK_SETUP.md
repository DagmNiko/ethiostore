# Local Webhook Setup Guide

Since Telegram requires HTTPS for webhooks, you need to use a tunneling service to expose your localhost to the internet.

## Quick Setup

### Option 1: Using ngrok (Recommended)

1. **Install ngrok**:
   ```bash
   # Download from https://ngrok.com/download
   # Or using package manager:
   sudo apt install ngrok  # Ubuntu/Debian
   # Or brew install ngrok  # macOS
   ```

2. **Start ngrok in one terminal**:
   ```bash
   ngrok http 8000
   ```
   
   This will give you a public URL like: `https://abc123.ngrok.io`

3. **Start Django server**:
   ```bash
   python manage.py runserver
   ```

4. **Set up webhook** (in another terminal):
   ```bash
   python manage.py setup_webhook_local
   ```
   
   This command automatically detects your ngrok URL and sets the webhook.

### Option 2: Using localtunnel (No installation needed)

1. **Start Django server**:
   ```bash
   python manage.py runserver
   ```

2. **Start localtunnel** (in another terminal):
   ```bash
   npx localtunnel --port 8000
   ```
   
   This will give you a public URL.

3. **Set webhook manually**:
   ```bash
   python manage.py setup_webhook --url https://your-tunnel-url.loca.lt/webhook/telegram/
   ```

### Option 3: Using cloudflared (Cloudflare Tunnel)

1. **Install cloudflared**:
   ```bash
   # Download from https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/
   ```

2. **Start tunnel**:
   ```bash
   cloudflared tunnel --url http://localhost:8000
   ```

3. **Set webhook**:
   ```bash
   python manage.py setup_webhook --url https://your-cloudflare-url.trycloudflare.com/webhook/telegram/
   ```

## Development Workflow

### Start Everything

1. **Terminal 1 - Start Django**:
   ```bash
   python manage.py runserver
   ```

2. **Terminal 2 - Start ngrok**:
   ```bash
   ngrok http 8000
   ```

3. **Terminal 3 - Set webhook**:
   ```bash
   python manage.py setup_webhook_local
   ```

### Check Webhook Status

```bash
python manage.py setup_webhook_local --remove  # Remove webhook
python manage.py setup_webhook_local           # Set webhook again
```

## Troubleshooting

### Ngrok URL not detected

If `setup_webhook_local` can't find your ngrok URL:

1. Make sure ngrok is running on port 4040 (default)
2. Or specify custom port: `python manage.py setup_webhook_local --ngrok-port 4041`
3. Or set webhook manually:
   ```bash
   python manage.py setup_webhook --url https://your-ngrok-url.ngrok.io/webhook/telegram/
   ```

### Webhook not receiving updates

1. Check that Django server is running
2. Check that ngrok is running and URL is correct
3. Verify webhook is set:
   ```python
   from aiogram import Bot
   from django.conf import settings
   bot = Bot(token=settings.BOT_TOKEN)
   info = await bot.get_webhook_info()
   print(info.url)
   ```

### Switch back to polling

If you want to test with polling instead:

```bash
python manage.py setup_webhook_local --remove
python bot.py  # Use the old polling script
```

## Notes

- **Ngrok free tier**: URLs change on restart. You'll need to update webhook each time.
- **Ngrok paid tier**: Can use custom domains with stable URLs.
- **Development**: For quick testing, polling might be easier. Use webhooks for production-like testing.
- **Security**: The webhook endpoint is public. Make sure your Django app handles authentication properly.

## Alternative: Use Polling for Development

If webhook setup is too complex for local development, you can use polling:

```bash
# Remove webhook
python manage.py setup_webhook_local --remove

# Use the old bot.py with polling (update it to use Django ORM)
python bot.py
```

