# Webhook Setup Guide

## Quick Start

1. **Install dependencies** (if not already installed):
```bash
pip install -r requirements.txt
```

2. **Set up database**:
```bash
python manage.py makemigrations
python manage.py migrate
```

3. **Set webhook URL**:
```bash
python manage.py setup_webhook --url https://yourdomain.com/webhook/telegram/
```

4. **Run Django server**:
```bash
# Development
python manage.py runserver

# Production
gunicorn ethiostore.wsgi:application --bind 0.0.0.0:8000
```

## Environment Variables

Make sure your `.env` file has:
```env
BOT_TOKEN=your-bot-token
WEBHOOK_URL=https://yourdomain.com/webhook/telegram/
DB_NAME=ethiostore_bot
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432
```

## Switching Between Webhook and Polling

**To use webhook** (recommended for production):
```bash
python manage.py setup_webhook --url https://yourdomain.com/webhook/telegram/
```

**To switch back to polling**:
```bash
python manage.py setup_webhook --remove
# Then run: python bot.py (the old polling script)
```

## Notes

- Webhooks are more reliable than polling
- Your server must be publicly accessible (use ngrok for testing)
- The webhook URL must be HTTPS (Telegram requirement)
- Make sure your firewall allows incoming connections on port 8000 (or your configured port)

