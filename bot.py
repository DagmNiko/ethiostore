"""
SF Telegram Bot - Main Entry Point
A Telegram SaaS bot for sellers to manage and automate product sales
"""
import os
import asyncio
import sys
import time

import django
from aiogram import Bot, Dispatcher, Router, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InputMediaPhoto, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramRetryAfter, TelegramNetworkError

# Configure Django so we can use the ORM from this standalone script
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ethiostore.settings")
django.setup()

from config import bot_config, app_config
from database.db import init_db
from utils.logger import logger

# Import routers
from features.onboarding import router as onboarding_router
from features.products import router as products_router
from features.inline_search import router as inline_router
from features.engagement import router as engagement_router
from features.scheduler import router as scheduler_router, start_scheduler, stop_scheduler

# Test router for multiple images with inline buttons
test_router = Router()

@test_router.message(Command("test_images"))
async def cmd_test_images(message: Message):
    """
    Test sending multiple images with inline buttons.
    NOTE: Telegram media groups DO NOT support inline keyboards in the UI.
    Even if the API accepts them, they won't display. So we send buttons separately.
    """
    try:
        # Inline keyboard
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Click me!", callback_data="button_click")],
                [InlineKeyboardButton(text="Another Button", callback_data="button_click2")]
            ]
        )

        # Real working image URLs
        media = [
            InputMediaPhoto(media="https://picsum.photos/600/400?random=1", caption="Random Image 1"),
            InputMediaPhoto(media="https://picsum.photos/600/400?random=2", caption="Random Image 2"),
            InputMediaPhoto(media="https://picsum.photos/600/400?random=3", caption="Random Image 3")
        ]

        # Send images as media group
        await message.answer("📤 Sending images...")
        sent_messages = await message.bot.send_media_group(chat_id=message.chat.id, media=media)
        
        # IMPORTANT: Telegram media groups do NOT display inline keyboards in the UI
        # Even if the API accepts the edit, the buttons won't appear on media groups
        # Solution: Send buttons in a separate message immediately after the media group
        await asyncio.sleep(0.3)  # Small delay for visual separation
        await message.answer(
            "🔘 **Choose an option:**",
            reply_markup=keyboard
        )
        
        logger.info("✅ Media group sent with buttons in follow-up message")
        
    except Exception as e:
        logger.error(f"Error in test_images: {e}")
        await message.answer(f"❌ Error: {e}")

@test_router.message(Command("test_images_seq"))
async def cmd_test_images_sequential(message: Message):
    """Alternative: Send images sequentially (not as group) - buttons will definitely work"""
    try:
        # Inline keyboard
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Click me!", callback_data="button_click")],
                [InlineKeyboardButton(text="Another Button", callback_data="button_click2")]
            ]
        )
        
        # Send images one by one (they'll appear close together but not as a media group)
        await message.answer("📤 Sending images sequentially...")
        
        await message.answer_photo(
            photo="https://picsum.photos/600/400?random=1",
            caption="Random Image 1"
        )
        await asyncio.sleep(0.3)
        
        await message.answer_photo(
            photo="https://picsum.photos/600/400?random=2",
            caption="Random Image 2"
        )
        await asyncio.sleep(0.3)
        
        # Last image with keyboard attached directly
        await message.answer_photo(
            photo="https://picsum.photos/600/400?random=3",
            caption="Random Image 3 - Choose an option:",
            reply_markup=keyboard
        )
        
        logger.info("✅ Successfully sent images sequentially with keyboard on last image")
        
    except Exception as e:
        logger.error(f"Error in test_images_sequential: {e}")
        await message.answer(f"❌ Error: {e}")

@test_router.callback_query(F.data.startswith("button_click"))
async def handle_test_button(callback: CallbackQuery):
    """Handle test button clicks"""
    try:
        button_id = callback.data
        await callback.answer(f"✅ Button {button_id} clicked!", show_alert=False)
    except Exception as e:
        logger.error(f"Error handling test button: {e}")
        try:
            await callback.answer("❌ Error", show_alert=True)
        except:
            pass

async def on_startup(bot: Bot):
    """Actions to perform on bot startup"""
    logger.info("🚀 Starting SF Telegram Bot...")
    
    # Initialize database
    try:
        await init_db()
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        sys.exit(1)
    
    # Start scheduler
    try:
        start_scheduler(bot)
        logger.info("✅ Scheduler started")
    except Exception as e:
        logger.error(f"⚠️ Failed to start scheduler: {e}")
    
    # Get bot info
    bot_info = await bot.get_me()
    logger.info(f"✅ Bot started: @{bot_info.username}")
    logger.info(f"📝 Bot name: {bot_info.first_name}")
    logger.info(f"🆔 Bot ID: {bot_info.id}")
    
    # Set bot commands
    from aiogram.types import BotCommand
    commands = [
        BotCommand(command="start", description="Start the bot / Register"),
        BotCommand(command="help", description="Get help"),
        BotCommand(command="addproduct", description="Add new product (Seller)"),
        BotCommand(command="myproducts", description="View your products (Seller)"),
        BotCommand(command="schedule", description="Schedule auto-posting (Seller)"),
        BotCommand(command="buyers", description="View customers (Seller)"),
        BotCommand(command="browse", description="Browse products (Buyer)"),
        BotCommand(command="saved", description="View saved products (Buyer)"),
        BotCommand(command="upgrade", description="Upgrade to Premium"),
    ]
    
    await bot.set_my_commands(commands)
    logger.info("✅ Bot commands set")

async def on_shutdown(bot: Bot):
    """Actions to perform on bot shutdown"""
    logger.info("🛑 Shutting down SF Telegram Bot...")
    
    # Stop scheduler
    try:
        stop_scheduler()
        logger.info("✅ Scheduler stopped")
    except Exception as e:
        logger.error(f"⚠️ Error stopping scheduler: {e}")
    
    await bot.session.close()
    logger.info("✅ Bot stopped gracefully")

async def main():
    """Main function to run the bot"""
    # Create bot instance
    bot = Bot(
        token=bot_config.TOKEN,
        default=DefaultBotProperties(
            parse_mode=ParseMode.MARKDOWN
        )
    )
    
    # Create dispatcher
    dp = Dispatcher()
    
    # Register routers
    dp.include_router(onboarding_router)
    dp.include_router(products_router)
    dp.include_router(inline_router)
    dp.include_router(engagement_router)
    dp.include_router(scheduler_router)
    dp.include_router(test_router)
    
    # Register startup/shutdown handlers
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    # Ensure webhook is disabled before starting polling (Telegram does not allow both)
    try:
        logger.info("🧹 Deleting existing webhook (if any) before starting polling...")
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("✅ Webhook deleted (or was not set)")
    except Exception as e:
        logger.error(f"⚠️ Failed to delete webhook: {e}")

    # Start polling; Ctrl+C (KeyboardInterrupt) will bubble up and stop asyncio.run(main)
    try:
        logger.info("🔄 Starting bot...")
        await dp.start_polling(bot, skip_updates=True, allowed_updates=dp.resolve_used_update_types())
    finally:
        # Clean up session on exit
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Bot stopped by user")
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
        sys.exit(1)


