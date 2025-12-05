# Quick Start: Local Webhook Setup

## Easiest Method: Using ngrok

### Step 1: Install ngrok
```bash
# Download from https://ngrok.com/download
# Or use package manager
sudo snap install ngrok  # Ubuntu
# or
brew install ngrok  # macOS
```

### Step 2: Start ngrok (Terminal 1)
```bash
ngrok http 8000
```

You'll see output like:
```
Forwarding  https://abc123.ngrok.io -> http://localhost:8000
```

Copy the HTTPS URL (e.g., `https://abc123.ngrok.io`)

### Step 3: Start Django (Terminal 2)
```bash
python manage.py runserver
```

### Step 4: Set webhook (Terminal 3)
```bash
# Automatic detection (if ngrok is running)
python manage.py setup_webhook_local

# OR manually specify the URL
python manage.py setup_webhook --url https://abc123.ngrok.io/webhook/telegram/
```

That's it! Your bot should now receive updates via webhook.

## Alternative: Use Polling (No Setup Needed)

If webhook setup is too complex, you can use polling for local development:

```bash
# Make sure webhook is removed first
python manage.py setup_webhook --remove

# Run the bot with polling
python bot.py
```

## Troubleshooting

**"Ngrok not found"**: Make sure ngrok is running. Check Terminal 1.

**"Connection refused"**: Make sure Django server is running. Check Terminal 2.

**"Webhook not receiving updates"**: 
1. Verify webhook URL: The URL should be `https://your-ngrok-url.ngrok.io/webhook/telegram/`
2. Make sure both ngrok and Django are running
3. Check Django logs for incoming requests

## Quick Commands

```bash
# Check webhook status
python manage.py setup_webhook_local

# Remove webhook
python manage.py setup_webhook_local --remove

# Set webhook manually
python manage.py setup_webhook --url https://your-url.com/webhook/telegram/
```

