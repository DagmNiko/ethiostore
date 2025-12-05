# Django Migration Guide

This project has been converted from a standalone aiogram bot with SQLAlchemy to a Django project with webhooks.

## What Changed

1. **Django Project Structure**: Added Django project files (`manage.py`, `settings.py`, `urls.py`)
2. **Django Models**: Created Django ORM models in `telegram_bot/models.py` (converted from SQLAlchemy)
3. **Webhook Support**: Bot now uses webhooks instead of polling
4. **PostgreSQL**: Configured to use PostgreSQL via Django settings

## Current Status

⚠️ **Important**: The bot features still use SQLAlchemy (`database/db.py`). You have two options:

### Option 1: Keep SQLAlchemy (Current)
- The bot will continue to work with SQLAlchemy
- Django models are available but not used by bot features yet
- You can gradually migrate features to Django ORM

### Option 2: Migrate to Django ORM
- Update all features to use Django models instead of SQLAlchemy
- Remove SQLAlchemy dependencies
- Use Django's database connection

## Setup Instructions

### 1. Environment Variables

Update your `.env` file with:

```env
# Django
DJANGO_SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database (PostgreSQL)
DB_NAME=ethiostore_bot
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432

# Telegram Bot
BOT_TOKEN=your-bot-token
BOT_USERNAME=@yourbot
WEBHOOK_URL=https://yourdomain.com/webhook/telegram/
WEBHOOK_SECRET=your-secret-token

# App Config
MEDIA_DIR=media/products
MAX_FREE_PRODUCTS=10
PREMIUM_PRICE_BIRR=500
```

### 2. Database Setup

```bash
# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create superuser (optional, for Django admin)
python manage.py createsuperuser
```

### 3. Set Up Webhook

```bash
# Set webhook URL
python manage.py setup_webhook --url https://yourdomain.com/webhook/telegram/

# Remove webhook (switch back to polling)
python manage.py setup_webhook --remove
```

### 4. Run Django Server

```bash
# Development
python manage.py runserver

# Production (with gunicorn)
gunicorn ethiostore.wsgi:application --bind 0.0.0.0:8000
```

## Docker Setup

The `docker-compose.yml` has been updated to include PostgreSQL. To run:

```bash
docker-compose up -d
```

## Migration from SQLAlchemy to Django ORM

If you want to migrate features to use Django ORM:

1. Update `database/db.py` to use Django models
2. Replace SQLAlchemy queries with Django ORM queries
3. Update all feature files to use Django models
4. Remove SQLAlchemy dependencies from `requirements.txt`

## Notes

- The bot will continue to work with SQLAlchemy until you migrate
- Django admin is available at `/admin/` for managing data
- Webhooks are more reliable than polling and recommended for production

