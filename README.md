# SF - Telegram Store Automation Bot 🛍️

A comprehensive Telegram SaaS bot that helps sellers automate their product listings, manage sales, and engage with customers directly on Telegram.

## 🎯 Features

### Core Features (MVP)
- ✅ **User Onboarding**: Separate flows for sellers and buyers
- ✅ **Product Management**: Add products with automatic watermarking
- ✅ **Inline Search**: Browse products using `@ethiostorebot <keyword>`
- ✅ **Auto-Posting**: Schedule recurring posts to channels
- ✅ **Engagement Tracking**: Like, save, and order buttons with analytics
- ✅ **Order Management**: Collect customer info and notify sellers
- ✅ **Customer Database**: Track buyers and their contact info

### Premium Features (500 Birr/month)
- 💎 Unlimited products (Free: 10 max)
- 📊 Advanced analytics
- 📢 Multi-channel posting
- 🌍 Auto-translations (planned)
- 📣 Broadcast messaging (planned)

## 🚀 Quick Start

### Prerequisites
- Python 3.11 or higher
- PostgreSQL database
- Telegram Bot Token (from @BotFather)

### Installation

1. **Clone the repository**
```bash
cd /home/dagmniko/ethiostore
```

2. **Create and activate virtual environment**
```bash
python3 -m venv venv
source venv/bin/activate  # On Linux/Mac
# or
venv\Scripts\activate  # On Windows
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up PostgreSQL database**
```bash
# Create database
sudo -u postgres psql
CREATE DATABASE ethiostore_bot;
CREATE USER ethiostore WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE ethiostore_bot TO ethiostore;
\q
```

5. **Configure environment variables**
```bash
cp .env.example .env
# Edit .env with your settings
nano .env
```

Update the following in `.env`:
- `BOT_TOKEN`: Your Telegram bot token
- `DB_PASSWORD`: Your PostgreSQL password
- Other settings as needed

6. **Run the bot**
```bash
python bot.py
```

## 📁 Project Structure

```
ethiostore/
├── bot.py                 # Main entry point
├── config.py              # Configuration management
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables
├── database/
│   ├── models.py         # SQLAlchemy models
│   └── db.py             # Database operations
├── features/
│   ├── onboarding.py     # User registration
│   ├── products.py       # Product management
│   ├── inline_search.py  # Inline query handler
│   ├── engagement.py     # Like, save, order features
│   └── scheduler.py      # Auto-posting scheduler
├── utils/
│   ├── watermark.py      # Image watermarking
│   ├── helpers.py        # Helper functions
│   └── logger.py         # Logging configuration
└── media/
    └── products/         # Product images storage
```

## 💡 Usage Guide

### For Sellers

1. **Register as Seller**
   - Start bot: `/start`
   - Choose "I'm a Seller"
   - Provide store name, phone, channel (optional)

2. **Add Products**
   - Command: `/addproduct`
   - Upload photo
   - Enter title, description, price, category
   - Bot automatically adds watermark
   - Choose to post now or schedule

3. **Schedule Auto-Posts**
   - Command: `/schedule`
   - Select product
   - Set frequency (daily, every 2 days, weekly)
   - Set posting time
   - Bot posts automatically

4. **View Customers**
   - Command: `/buyers`
   - See all customers who ordered

5. **Manage Products**
   - Command: `/myproducts`
   - View all your products with stats

### For Buyers

1. **Register as Buyer**
   - Start bot: `/start`
   - Choose "I'm a Buyer"

2. **Browse Products**
   - Inline search: Type `@ethiostorebot shoes` in any chat
   - Browse latest: `/browse`

3. **Interact with Products**
   - ❤️ Like products
   - 💾 Save for later (view with `/saved`)
   - 🛒 Place orders
   - 📞 Call seller directly

4. **Place Orders**
   - Click 🛒 Order button
   - Enter quantity
   - Share phone number
   - Optionally share location
   - Seller receives notification

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `BOT_TOKEN` | Telegram bot token | Required |
| `BOT_USERNAME` | Bot username | @ethiostorebot |
| `DB_HOST` | PostgreSQL host | localhost |
| `DB_PORT` | PostgreSQL port | 5432 |
| `DB_NAME` | Database name | ethiostore_bot |
| `DB_USER` | Database user | postgres |
| `DB_PASSWORD` | Database password | postgres |
| `MEDIA_DIR` | Product images directory | media/products |
| `MAX_FREE_PRODUCTS` | Free tier product limit | 10 |
| `PREMIUM_PRICE_BIRR` | Premium subscription price | 500 |
| `DEBUG` | Debug mode | False |

## 🚢 Deployment

### Option 1: Docker (Recommended)

```bash
# Create Dockerfile
cat > Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create media directory
RUN mkdir -p media/products logs

CMD ["python", "bot.py"]
EOF

# Create docker-compose.yml
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: ethiostore_bot
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: your_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  bot:
    build: .
    depends_on:
      - db
    environment:
      DB_HOST: db
      DB_PASSWORD: your_password
    volumes:
      - ./media:/app/media
      - ./logs:/app/logs
    env_file:
      - .env
    restart: unless-stopped

volumes:
  postgres_data:
EOF

# Run with Docker Compose
docker-compose up -d
```

### Option 2: Systemd Service (Linux)

```bash
# Create service file
sudo nano /etc/systemd/system/ethiostore-bot.service
```

Add:
```ini
[Unit]
Description=SF Telegram Bot
After=network.target postgresql.service

[Service]
Type=simple
User=your_user
WorkingDirectory=/home/dagmniko/ethiostore
Environment="PATH=/home/dagmniko/ethiostore/venv/bin"
ExecStart=/home/dagmniko/ethiostore/venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable ethiostore-bot
sudo systemctl start ethiostore-bot
sudo systemctl status ethiostore-bot
```

### Option 3: Cloud Platforms

#### Render
1. Create new Web Service
2. Connect GitHub repository
3. Set environment variables
4. Deploy

#### Heroku
```bash
# Add Procfile
echo "bot: python bot.py" > Procfile

# Deploy
heroku create ethiostore-bot
heroku addons:create heroku-postgresql:mini
heroku config:set BOT_TOKEN=your_token
git push heroku main
```

#### Railway
1. Create new project
2. Add PostgreSQL database
3. Connect repository
4. Set environment variables
5. Deploy

## 🔒 Security Notes

- ✅ Never commit `.env` file to git
- ✅ Use strong database passwords
- ✅ Restrict bot admin IDs in production
- ✅ Enable HTTPS for webhooks (optional)
- ✅ Regularly backup database

## 📊 Database Schema

### Users Table
- Stores both sellers and buyers
- Fields: role, store_name, phone, channel_username, is_premium

### Products Table
- Product details and media
- Engagement counters (likes, saves, orders)
- Watermarked and original images

### Orders Table
- Order information
- Buyer contact details
- Order status tracking

### Engagements Table
- Tracks likes and saves
- Links users to products

### Schedules Table
- Auto-posting configuration
- Frequency and timing settings

## 🐛 Troubleshooting

### Bot not responding
```bash
# Check if bot is running
ps aux | grep bot.py

# Check logs
tail -f logs/bot_*.log
```

### Database connection errors
```bash
# Test PostgreSQL connection
psql -h localhost -U postgres -d ethiostore_bot

# Check if database exists
sudo -u postgres psql -l | grep ethiostore
```

### Image watermarking issues
```bash
# Install system fonts (Ubuntu/Debian)
sudo apt-get install fonts-dejavu-core

# Check Pillow installation
python -c "from PIL import Image; print('OK')"
```

## 📈 Future Enhancements

- [ ] Multi-channel support
- [ ] Advanced analytics dashboard
- [ ] Auto-translation (Amharic/English)
- [ ] Broadcast messaging
- [ ] Payment integration
- [ ] Product categories management
- [ ] Inventory tracking
- [ ] Customer reviews and ratings
- [ ] Webhook mode support
- [ ] Admin panel

## 📝 License

This project is proprietary software. All rights reserved.

## 🤝 Support

For support, contact the development team or raise an issue in the repository.

## 👨‍💻 Developer

Built with ❤️ for Ethiopian sellers

---

**Version:** 1.0.0 MVP  
**Last Updated:** October 2025



