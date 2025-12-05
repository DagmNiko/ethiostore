"""
Configuration module for SF Telegram Bot
Loads environment variables and provides app settings
"""
import os
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@dataclass
class BotConfig:
    """Bot configuration"""
    TOKEN: str = os.getenv("BOT_TOKEN", "8410255574:AAFaRpc3qB22wXiO-CPhCXWJ9Sl0cCa2aJY")
    BOT_USERNAME: str = os.getenv("BOT_USERNAME", "@ethiostorebot")
    ADMIN_IDS: list = None
    
    def __post_init__(self):
        admin_ids_str = os.getenv("ADMIN_IDS", "")
        self.ADMIN_IDS = [int(id.strip()) for id in admin_ids_str.split(",") if id.strip()]

@dataclass
class DatabaseConfig:
    """Database configuration"""
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_NAME: str = os.getenv("DB_NAME", "ethiostore_bot")
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "postgres")
    
    @property
    def database_url(self) -> str:
        """Get PostgreSQL connection URL"""
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

@dataclass
class AppConfig:
    """Application settings"""
    MEDIA_DIR: str = os.getenv("MEDIA_DIR", "media/products")
    MAX_FREE_PRODUCTS: int = int(os.getenv("MAX_FREE_PRODUCTS", "30"))
    PREMIUM_PRICE_BIRR: int = int(os.getenv("PREMIUM_PRICE_BIRR", "500"))
    WATERMARK_FONT_SIZE: int = int(os.getenv("WATERMARK_FONT_SIZE", "24"))
    WATERMARK_OPACITY: int = int(os.getenv("WATERMARK_OPACITY", "180"))
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"

# Initialize configurations
bot_config = BotConfig()
db_config = DatabaseConfig()
app_config = AppConfig()

# Create media directory if it doesn't exist
os.makedirs(app_config.MEDIA_DIR, exist_ok=True)



