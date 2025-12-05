# Quick Start Guide - SF Telegram Bot

Get your bot running in 5 minutes! ⚡

## 🚀 Fast Setup

### 1. Install Dependencies

```bash
# Using the setup script (recommended)
./setup.sh

# Or manually
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment

Edit `.env` file:
```bash
BOT_TOKEN=8410255574:AAFaRpc3qB22wXiO-CPhCXWJ9Sl0cCa2aJY
DB_PASSWORD=your_postgres_password
```

### 3. Set Up Database

```bash
# Option 1: Use Docker (easiest)
docker-compose up -d

# Option 2: Local PostgreSQL
sudo -u postgres psql
CREATE DATABASE ethiostore_bot;
\q
```

### 4. Run the Bot

```bash
# Activate virtual environment (if not already)
source venv/bin/activate

# Run
python bot.py
```

That's it! Your bot is now running! 🎉

## 📱 Testing the Bot

### As a Seller
1. Open Telegram and search for `@ethiostorebot`
2. Send `/start`
3. Choose "I'm a Seller"
4. Enter your store details
5. Send `/addproduct` to add your first product

### As a Buyer
1. Search for `@ethiostorebot`
2. Send `/start`
3. Choose "I'm a Buyer"
4. Use inline mode: Type `@ethiostorebot shoes` in any chat
5. Or use `/browse` to see latest products

## 🎯 Key Commands

### Seller Commands
- `/start` - Register your store
- `/addproduct` - Add new product
- `/myproducts` - View your products
- `/schedule` - Set up auto-posting
- `/buyers` - View your customers

### Buyer Commands
- `/start` - Register
- `/browse` - Browse products
- `/saved` - View saved items
- Inline: `@ethiostorebot keyword`

## ⚙️ Important Configuration

### Make Bot Admin of Your Channel
1. Go to your Telegram channel
2. Add `@ethiostorebot` as administrator
3. Give it permission to post messages
4. Update channel username in `/settings`

### Watermark Configuration
Edit `config.py` or `.env`:
- `WATERMARK_FONT_SIZE` - Font size (default: 24)
- `WATERMARK_OPACITY` - Transparency (default: 180)

### Premium Settings
- `MAX_FREE_PRODUCTS` - Free tier limit (default: 10)
- `PREMIUM_PRICE_BIRR` - Subscription price (default: 500)

## 🐛 Troubleshooting

### Bot not responding?
```bash
# Check if running
ps aux | grep bot.py

# Check logs
tail -f logs/bot_*.log
```

### Database errors?
```bash
# Test connection
python3 -c "from database.db import init_db; import asyncio; asyncio.run(init_db())"
```

### Import errors?
```bash
# Make sure you're in venv
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

## 🚢 Production Deployment

### Using Docker (Recommended)
```bash
docker-compose up -d
docker-compose logs -f bot
```

### Using Systemd
```bash
sudo cp ethiostore-bot.service /etc/systemd/system/
sudo systemctl enable ethiostore-bot
sudo systemctl start ethiostore-bot
```

## 📊 Project Status

✅ **Completed Features:**
- User onboarding (seller/buyer)
- Product management with watermarking
- Inline product search
- Engagement system (like, save, order)
- Auto-posting scheduler
- Customer database
- Order management

🔄 **Planned Features:**
- Multi-channel posting
- Advanced analytics dashboard
- Auto-translation (Amharic/English)
- Broadcast messaging
- Payment integration
- Product inventory tracking

## 📞 Support

Need help? Check:
1. `README.md` - Full documentation
2. Logs in `logs/` directory
3. GitHub Issues

---

**Happy Selling! 🛍️**



