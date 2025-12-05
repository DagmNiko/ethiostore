"""
Scheduler feature
Handles automatic posting of products to channels
"""
from datetime import datetime, timedelta
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from database.db import db
from utils.helpers import format_product_caption, create_product_keyboard, calculate_next_post_time
from utils.logger import logger
from config import app_config, bot_config

router = Router()
scheduler = AsyncIOScheduler()

# FSM States for scheduling
class ScheduleStates(StatesGroup):
    selecting_product = State()
    setting_interval = State()
    setting_time = State()

@router.message(Command("schedule"))
async def cmd_schedule(message: Message, state: FSMContext):
    """Start scheduled autoposting setup"""
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    
    if not user or user.role != "seller":
        await message.answer("❌ This command is only for sellers.")
        return
    
    if not user.channel_username:
        await message.answer(
            "❌ You haven't set up a channel yet.\n"
            "Use /settings to add your channel first."
        )
        return
    
    # Enforce freemium limit: max 4 active scheduled autoposts
    if not user.is_premium:
        active_count = await db.count_seller_active_schedules(user_id)
        if active_count >= 4:
            await message.answer(
                "⚠️ **Free Plan Limit Reached for Scheduled Autoposting**\n\n"
                f"You already have {active_count} active scheduled autoposts (max: 4 on the free plan).\n\n"
                "Upgrade to Premium for unlimited scheduled autoposting!\n"
                f"💎 /upgrade - Only {app_config.PREMIUM_PRICE_BIRR} birr/month"
            )
            return
    
    # Get seller's products
    products = await db.get_seller_products(user_id)
    
    if not products:
        await message.answer(
            "📦 **No products to schedule!**\n\n"
            "Add products first with /addproduct"
        )
        return
    
    # Show products to select from
    keyboard = []
    for product in products[:10]:  # Limit to 10 for now
        keyboard.append([
            InlineKeyboardButton(
                text=f"{product.title} - {product.price} Birr",
                callback_data=f"sched_prod_{product.id}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton(text="❌ Cancel", callback_data="sched_cancel")])
    
    await message.answer(
        "⏰ **Scheduled Autoposting**\n\n"
        "Select a product to schedule for automatic posting:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    
    await state.set_state(ScheduleStates.selecting_product)

@router.callback_query(F.data.startswith("sched_prod_"), ScheduleStates.selecting_product)
async def schedule_product_selected(callback: CallbackQuery, state: FSMContext):
    """Product selected for scheduling"""
    await callback.answer()
    
    product_id = int(callback.data.split('_')[2])
    product = await db.get_product(product_id)
    
    await state.update_data(product_id=product_id)
    
    # Ask for interval
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Every Day", callback_data="interval_1"),
            InlineKeyboardButton(text="Every 2 Days", callback_data="interval_2")
        ],
        [
            InlineKeyboardButton(text="Every 3 Days", callback_data="interval_3"),
            InlineKeyboardButton(text="Every Week", callback_data="interval_7")
        ],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="sched_cancel")]
    ])
    
    await callback.message.edit_text(
        f"✅ Selected: **{product.title}**\n\n"
        "How often should I repost this product?",
        reply_markup=keyboard
    )
    
    await state.set_state(ScheduleStates.setting_interval)

@router.callback_query(F.data.startswith("interval_"), ScheduleStates.setting_interval)
async def schedule_interval_selected(callback: CallbackQuery, state: FSMContext):
    """Interval selected"""
    await callback.answer()
    
    interval_days = int(callback.data.split('_')[1])
    await state.update_data(interval_days=interval_days)
    
    # Ask for time
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="9:00 AM", callback_data="time_09:00"),
            InlineKeyboardButton(text="12:00 PM", callback_data="time_12:00")
        ],
        [
            InlineKeyboardButton(text="3:00 PM", callback_data="time_15:00"),
            InlineKeyboardButton(text="6:00 PM", callback_data="time_18:00")
        ],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="sched_cancel")]
    ])
    
    interval_text = "day" if interval_days == 1 else f"{interval_days} days"
    
    await callback.message.edit_text(
        f"✅ Interval: Every {interval_text}\n\n"
        "What time should I post?",
        reply_markup=keyboard
    )
    
    await state.set_state(ScheduleStates.setting_time)

@router.callback_query(F.data.startswith("time_"), ScheduleStates.setting_time)
async def schedule_time_selected(callback: CallbackQuery, state: FSMContext):
    """Time selected - finalize schedule"""
    await callback.answer()
    
    post_time = callback.data.split('_')[1]
    data = await state.get_data()
    
    user_id = callback.from_user.id
    user = await db.get_user(user_id)
    product = await db.get_product(data['product_id'])
    
    # Calculate next post time
    next_post = calculate_next_post_time(data['interval_days'], post_time)
    
    # Create schedule in database
    schedule = await db.create_schedule(
        seller_id=user_id,
        product_id=product.id,
        channel_username=user.channel_username,
        interval_days=data['interval_days'],
        post_time=post_time
    )
    
    # Update next post time
    await db.update_schedule_post_time(schedule.id, None, next_post)
    
    interval_text = "day" if data['interval_days'] == 1 else f"{data['interval_days']} days"
    
    await callback.message.edit_text(
        f"✅ **Schedule Created!**\n\n"
        f"📦 Product: {product.title}\n"
        f"📢 Channel: {user.channel_username}\n"
        f"🔄 Frequency: Every {interval_text}\n"
        f"⏰ Time: {post_time}\n"
        f"📅 Next post: {next_post.strftime('%B %d at %I:%M %p')}\n\n"
        "I'll automatically post this product to your channel!"
    )
    
    await state.clear()
    logger.info(f"Schedule {schedule.id} created for product {product.id}")

@router.callback_query(F.data == "sched_cancel")
async def schedule_cancel(callback: CallbackQuery, state: FSMContext):
    """Cancel scheduling"""
    await callback.answer()
    await callback.message.edit_text("❌ Scheduling cancelled.")
    await state.clear()

@router.message(Command("schedules"))
async def cmd_view_schedules(message: Message):
    """View active schedules"""
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    
    if not user or user.role != "seller":
        await message.answer("❌ This command is only for sellers.")
        return
    
    # Get user's schedules using Django ORM
    from telegram_bot.models import PostSchedule, Product
    
    schedules = list(PostSchedule.objects.filter(
        seller_id=user_id,
        is_active=True
    ).order_by('next_post_at'))
    
    if not schedules:
        await message.answer(
            "⏰ **No active schedules**\n\n"
            "Create one with /schedule"
        )
        return
    
    response = f"⏰ **Your Schedules** ({len(schedules)})\n\n"
    
    for i, schedule in enumerate(schedules, 1):
        product = await db.get_product(schedule.product_id)
        interval_text = "day" if schedule.interval_days == 1 else f"{schedule.interval_days} days"
        
        response += (
            f"{i}. **{product.title}**\n"
            f"   📢 {schedule.channel_username}\n"
            f"   🔄 Every {interval_text} at {schedule.post_time}\n"
        )
        
        if schedule.next_post_at:
            response += f"   📅 Next: {schedule.next_post_at.strftime('%b %d at %I:%M %p')}\n"
        
        response += f"   /pause_{schedule.id} | /delete_{schedule.id}\n\n"
    
    await message.answer(response)

# Background job to check and post scheduled products
async def check_and_post_scheduled(bot: Bot):
    """Background task to check schedules and post products"""
    try:
        now = datetime.now()
        schedules = await db.get_active_schedules()
        
        for schedule in schedules:
            # Check if it's time to post
            if schedule.next_post_at and schedule.next_post_at <= now:
                try:
                    # Get product and seller
                    product = await db.get_product(schedule.product_id)
                    seller = await db.get_user(schedule.seller_id)
                    
                    if not product or not product.is_active:
                        continue
                    
                    # Create caption and keyboard
                    caption = format_product_caption(
                        title=product.title,
                        description=product.description,
                        price=product.price,
                        category=product.category,
                        engagement_stats={
                            'likes_count': product.likes_count,
                            'saves_count': product.saves_count,
                            'orders_count': product.orders_count
                        }
                    )
                    
                    custom_button = None
                    if product.custom_button_text and product.custom_button_url:
                        custom_button = (product.custom_button_text, product.custom_button_url)
                    
                    keyboard = create_product_keyboard(
                        product_id=product.id,
                        seller_phone=seller.phone,
                        custom_button=custom_button,
                        likes_count=product.likes_count,
                        saves_count=product.saves_count,
                        like_enabled=product.like_enabled,
                        save_enabled=product.save_enabled,
                        order_enabled=product.order_enabled
                    )
                    
                    # Post to channel
                    photo = FSInputFile(product.image_path)
                    await bot.send_photo(
                        chat_id=schedule.channel_username,
                        photo=photo,
                        caption=caption,
                        reply_markup=keyboard
                    )
                    
                    # Calculate next post time
                    next_post = calculate_next_post_time(schedule.interval_days, schedule.post_time)
                    
                    # Update schedule
                    await db.update_schedule_post_time(schedule.id, now, next_post)
                    
                    logger.info(f"Scheduled post completed: schedule {schedule.id}, product {product.id}")
                    
                except Exception as e:
                    logger.error(f"Error posting scheduled product {schedule.id}: {e}")
        
    except Exception as e:
        logger.error(f"Error in scheduled posting job: {e}")

def start_scheduler(bot: Bot):
    """Start the scheduler with periodic checks"""
    # Check every 5 minutes for scheduled posts
    scheduler.add_job(
        check_and_post_scheduled,
        trigger=IntervalTrigger(minutes=5),
        args=[bot],
        id='check_schedules',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("Scheduler started")

def stop_scheduler():
    """Stop the scheduler"""
    scheduler.shutdown()
    logger.info("Scheduler stopped")


