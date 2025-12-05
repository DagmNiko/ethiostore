# Deployment Guide - SF Telegram Bot

Complete guide for deploying the SF Telegram Bot to production.

## 📋 Pre-Deployment Checklist

- [ ] Bot token obtained from @BotFather
- [ ] PostgreSQL database ready
- [ ] Server/hosting platform selected
- [ ] Domain name (optional, for webhooks)
- [ ] SSL certificate (optional, for webhooks)
- [ ] Environment variables configured

## 🖥️ Deployment Options

### Option 1: Docker Deployment (Recommended) 🐳

**Advantages:** Isolated environment, easy to manage, portable

#### Steps:

1. **Install Docker and Docker Compose**
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install docker.io docker-compose
sudo systemctl start docker
sudo systemctl enable docker

# Add your user to docker group
sudo usermod -aG docker $USER
# Log out and log back in
```

2. **Configure Environment**
```bash
cd /home/dagmniko/ethiostore
cp .env.example .env
nano .env  # Edit with your settings
```

3. **Build and Run**
```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f bot

# Stop services
docker-compose down

# Restart bot
docker-compose restart bot
```

4. **Update Bot**
```bash
# Pull latest changes
git pull

# Rebuild and restart
docker-compose up -d --build
```

---

### Option 2: Systemd Service (Linux) 🐧

**Advantages:** Native Linux integration, auto-start on boot

#### Steps:

1. **Create Service File**
```bash
sudo nano /etc/systemd/system/ethiostore-bot.service
```

Add this content:
```ini
[Unit]
Description=SF Telegram Store Automation Bot
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=dagmniko
Group=dagmniko
WorkingDirectory=/home/dagmniko/ethiostore
Environment="PATH=/home/dagmniko/ethiostore/venv/bin"
ExecStart=/home/dagmniko/ethiostore/venv/bin/python /home/dagmniko/ethiostore/bot.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

2. **Enable and Start Service**
```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable auto-start
sudo systemctl enable ethiostore-bot

# Start the bot
sudo systemctl start ethiostore-bot

# Check status
sudo systemctl status ethiostore-bot

# View logs
sudo journalctl -u ethiostore-bot -f

# Restart bot
sudo systemctl restart ethiostore-bot
```

3. **Update Bot**
```bash
# Pull changes
cd /home/dagmniko/ethiostore
git pull

# Activate venv and install updates
source venv/bin/activate
pip install -r requirements.txt

# Restart service
sudo systemctl restart ethiostore-bot
```

---

### Option 3: Cloud Platforms ☁️

#### A. Render.com

1. Create new **Web Service**
2. Connect GitHub repository
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `python bot.py`
5. Add PostgreSQL database from dashboard
6. Set environment variables:
   - `BOT_TOKEN`
   - `DB_HOST` (from Render PostgreSQL)
   - `DB_PASSWORD` (from Render PostgreSQL)
   - `DB_NAME`
   - `DB_USER`
7. Deploy!

**Cost:** Free tier available, ~$7/month for paid

---

#### B. Railway.app

1. Create new project
2. Add **PostgreSQL** from services
3. Add **GitHub Repo** deployment
4. Set environment variables (Railway auto-sets DB vars)
5. Deploy

**Cost:** Free $5 credit/month, then pay-as-you-go

---

#### C. Heroku

```bash
# Install Heroku CLI
curl https://cli-assets.heroku.com/install.sh | sh

# Login
heroku login

# Create app
heroku create ethiostore-bot

# Add PostgreSQL
heroku addons:create heroku-postgresql:mini

# Set environment variables
heroku config:set BOT_TOKEN=your_token
heroku config:set MAX_FREE_PRODUCTS=10
heroku config:set PREMIUM_PRICE_BIRR=500

# Create Procfile
echo "worker: python bot.py" > Procfile

# Deploy
git add .
git commit -m "Deploy to Heroku"
git push heroku main

# Scale worker
heroku ps:scale worker=1

# View logs
heroku logs --tail
```

**Cost:** Free tier ended, ~$7/month minimum

---

#### D. DigitalOcean Droplet

1. **Create Droplet**
   - Ubuntu 22.04 LTS
   - Basic plan: $6/month
   - Choose datacenter region

2. **Setup Server**
```bash
# SSH into server
ssh root@your_server_ip

# Update system
apt update && apt upgrade -y

# Install dependencies
apt install -y python3.11 python3-pip python3-venv postgresql postgresql-contrib git

# Create user
adduser ethiostore
usermod -aG sudo ethiostore
su - ethiostore

# Clone repository
git clone https://github.com/yourusername/ethiostore.git
cd ethiostore

# Setup
./setup.sh
```

3. **Configure PostgreSQL**
```bash
sudo -u postgres psql
CREATE DATABASE ethiostore_bot;
CREATE USER ethiostore WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE ethiostore_bot TO ethiostore;
\q
```

4. **Setup Systemd Service** (see Option 2 above)

5. **Setup Firewall**
```bash
sudo ufw allow OpenSSH
sudo ufw allow 5432/tcp  # PostgreSQL (only if needed externally)
sudo ufw enable
```

---

### Option 4: VPS with Screen/Tmux (Quick & Dirty)

**Not recommended for production, but works for testing**

```bash
# Install screen
sudo apt install screen

# Start screen session
screen -S bot

# Activate venv and run
source venv/bin/activate
python bot.py

# Detach: Press Ctrl+A then D
# Reattach: screen -r bot
# Kill: screen -X -S bot quit
```

---

## 🔒 Security Best Practices

### 1. Environment Variables
```bash
# Never commit .env to git
echo ".env" >> .gitignore

# Use strong passwords
DB_PASSWORD=$(openssl rand -base64 32)

# Restrict file permissions
chmod 600 .env
```

### 2. Database Security
```bash
# Edit PostgreSQL config
sudo nano /etc/postgresql/*/main/pg_hba.conf

# Change to require passwords
# local   all   all   md5
# host    all   all   127.0.0.1/32   md5

# Restart PostgreSQL
sudo systemctl restart postgresql
```

### 3. Firewall
```bash
# Only allow SSH and necessary ports
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw enable
```

### 4. Bot Token Security
- Never share your bot token
- Regenerate if compromised (@BotFather → /revoke)
- Use environment variables only
- Don't hardcode in source

---

## 📊 Monitoring & Logging

### 1. Application Logs
```bash
# View logs
tail -f logs/bot_*.log

# Rotate logs (add to cron)
find logs/ -name "*.log" -mtime +7 -delete
```

### 2. System Monitoring
```bash
# Install htop
sudo apt install htop

# Monitor resources
htop

# Check disk space
df -h

# Check memory
free -h
```

### 3. Database Monitoring
```bash
# Connect to database
psql -U postgres -d ethiostore_bot

# Check table sizes
SELECT pg_size_pretty(pg_total_relation_size('products'));

# Check row counts
SELECT COUNT(*) FROM products;
SELECT COUNT(*) FROM users;
SELECT COUNT(*) FROM orders;
```

---

## 🔄 Backup & Recovery

### 1. Database Backup
```bash
# Create backup script
cat > /home/dagmniko/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/home/dagmniko/backups"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# Backup database
pg_dump -U postgres ethiostore_bot > $BACKUP_DIR/db_$DATE.sql

# Backup media
tar -czf $BACKUP_DIR/media_$DATE.tar.gz media/

# Keep only last 7 days
find $BACKUP_DIR -type f -mtime +7 -delete

echo "Backup completed: $DATE"
EOF

chmod +x /home/dagmniko/backup.sh

# Add to cron (daily at 2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * * /home/dagmniko/backup.sh") | crontab -
```

### 2. Restore from Backup
```bash
# Restore database
psql -U postgres ethiostore_bot < backups/db_20251013_020000.sql

# Restore media
tar -xzf backups/media_20251013_020000.tar.gz
```

---

## 🚀 Performance Optimization

### 1. Database Indexing
```sql
-- Connect to database
psql -U postgres -d ethiostore_bot

-- Add indexes for faster queries
CREATE INDEX idx_products_seller ON products(seller_id);
CREATE INDEX idx_products_active ON products(is_active, is_public);
CREATE INDEX idx_orders_seller ON orders(seller_id);
CREATE INDEX idx_orders_buyer ON orders(buyer_id);
CREATE INDEX idx_engagements_user_product ON engagements(user_id, product_id);
```

### 2. Image Optimization
```bash
# Install image optimization tools
sudo apt install optipng jpegoptim

# Optimize images (add to watermark.py)
jpegoptim --size=500k media/products/*.jpg
```

### 3. Enable Database Connection Pooling
Already configured in `database/db.py`:
- `pool_size=10`
- `max_overflow=20`

---

## 📈 Scaling Considerations

### When to Scale
- More than 1000 active sellers
- More than 10,000 products
- More than 100,000 daily requests

### Vertical Scaling
- Upgrade server RAM (4GB → 8GB → 16GB)
- Upgrade CPU cores (1 → 2 → 4)
- Upgrade database storage

### Horizontal Scaling
- Use webhook mode instead of polling
- Deploy multiple bot instances
- Use Redis for session storage
- Separate database server
- Use CDN for images

---

## 🐛 Troubleshooting

### Bot Not Starting
```bash
# Check Python version
python3 --version

# Check dependencies
pip list

# Check environment
cat .env | grep BOT_TOKEN

# Run with verbose logging
DEBUG=True python bot.py
```

### Database Connection Issues
```bash
# Test connection
pg_isready -h localhost -U postgres

# Check if PostgreSQL is running
sudo systemctl status postgresql

# Check logs
sudo tail -f /var/log/postgresql/postgresql-*-main.log
```

### High Memory Usage
```bash
# Check memory
free -h

# Find memory-hungry processes
ps aux --sort=-%mem | head

# Restart bot
sudo systemctl restart ethiostore-bot
```

---

## ✅ Post-Deployment Checklist

- [ ] Bot responding to `/start`
- [ ] Database connection working
- [ ] Product creation working
- [ ] Image watermarking working
- [ ] Inline search functional
- [ ] Order system working
- [ ] Scheduler running
- [ ] Logs being written
- [ ] Backups configured
- [ ] Monitoring setup
- [ ] Firewall configured
- [ ] SSL (if using webhooks)

---

## 📞 Support

If you encounter issues:
1. Check logs: `logs/bot_*.log`
2. Check system logs: `journalctl -u ethiostore-bot`
3. Check database: `psql -U postgres -d ethiostore_bot`
4. Review error messages
5. Consult README.md

---

**Good luck with your deployment! 🚀**



