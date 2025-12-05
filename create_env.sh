#!/bin/bash
cat > .env << 'EOF'
# Telegram Bot Configuration
BOT_TOKEN=8410255574:AAFaRpc3qB22wXiO-CPhCXWJ9Sl0cCa2aJY
BOT_USERNAME=@ethiostorebot
ADMIN_IDS=

# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ethiostore_bot
DB_USER=ethiostore
DB_PASSWORD=ethiostore123

# Application Settings
MEDIA_DIR=media/products
MAX_FREE_PRODUCTS=10
PREMIUM_PRICE_BIRR=500
WATERMARK_FONT_SIZE=24
WATERMARK_OPACITY=180
DEBUG=False
EOF
echo "✅ .env file created successfully!"
