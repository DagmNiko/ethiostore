"""
User onboarding feature
Handles /start command and user registration
"""
from aiogram import Router, F
from aiogram.filters import CommandStart, StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database.db import db
from utils.logger import logger

router = Router()

# FSM States for onboarding
class OnboardingStates(StatesGroup):
    choosing_role = State()
    # Seller states
    seller_store_name = State()
    seller_phone = State()
    seller_channel = State()
    # Buyer states
    buyer_name = State()
    buyer_phone = State()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Handle /start command - begin onboarding"""
    user_id = message.from_user.id
    
    # Check if user already exists
    user = await db.get_user(user_id)
    
    if user:
        # User already registered
        if user.role == "seller":
            await message.answer(
                f"👋 Welcome back, {user.store_name}!\n\n"
                "What would you like to do?\n\n"
                "📦 /addproduct - Add new product\n"
                "📋 /myproducts - View your products\n"
                "👥 /buyers - View your customers\n"
                "⏰ /schedule - Schedule auto-posts\n"
                "💎 /upgrade - Upgrade to Premium\n"
                "❓ /help - Get help"
            )
        else:
            await message.answer(
                f"👋 Welcome back, {user.first_name or 'there'}!\n\n"
                "You can browse products using inline mode:\n"
                f"Type @ethiostorebot <search term> in any chat\n\n"
                "Or use /browse to see latest products"
            )
        await state.clear()
        return
    
    # New user - start onboarding
    await message.answer(
        "🎉 **Welcome to SF - Your Store Automation Assistant!**\n\n"
        "I help you sell products on Telegram with ease.\n\n"
        "First, let me know who you are:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🏪 I'm a Seller", callback_data="role_seller"),
                InlineKeyboardButton(text="🛒 I'm a Buyer", callback_data="role_buyer")
            ]
        ])
    )
    
    await state.set_state(OnboardingStates.choosing_role)
    
    logger.info(f"New user started onboarding: {user_id}")

@router.callback_query(F.data == "role_seller", OnboardingStates.choosing_role)
async def role_seller_selected(callback: CallbackQuery, state: FSMContext):
    """User selected Seller role"""
    await callback.answer()
    
    await callback.message.edit_text(
        "🏪 **Great! Let's set up your store.**\n\n"
        "First, what's your store name?\n"
        "(This will be used as watermark on your product images)"
    )
    
    await state.update_data(role="seller")
    await state.set_state(OnboardingStates.seller_store_name)

@router.callback_query(F.data == "role_buyer", OnboardingStates.choosing_role)
async def role_buyer_selected(callback: CallbackQuery, state: FSMContext):
    """User selected Buyer role"""
    await callback.answer()
    
    # Create buyer with basic info
    user = await db.create_user(
        user_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        last_name=callback.from_user.last_name,
        role="buyer"
    )
    
    await callback.message.edit_text(
        "🛒 **Welcome, Buyer!**\n\n"
        "You're all set! You can now:\n\n"
        "🔍 Browse products using inline mode:\n"
        f"   Type @ethiostorebot <product name> in any chat\n\n"
        "📱 Or use /browse to see latest products\n\n"
        "Happy shopping! 🎉"
    )
    
    await state.clear()
    logger.info(f"Buyer registered: {user.id}")

@router.message(OnboardingStates.seller_store_name)
async def seller_store_name_received(message: Message, state: FSMContext):
    """Receive seller store name"""
    store_name = message.text.strip()
    
    if len(store_name) < 2:
        await message.answer("❌ Store name must be at least 2 characters. Please try again:")
        return
    
    await state.update_data(store_name=store_name)
    
    # Request phone number with contact button
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Share Phone Number", request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await message.answer(
        f"✅ Store name: **{store_name}**\n\n"
        "Now, please share your phone number so buyers can reach you.\n"
        "You can use the button below or type it manually:",
        reply_markup=keyboard
    )
    
    await state.set_state(OnboardingStates.seller_phone)

@router.message(OnboardingStates.seller_phone, F.contact)
async def seller_phone_contact_received(message: Message, state: FSMContext):
    """Receive seller phone via contact share"""
    phone = message.contact.phone_number
    await state.update_data(phone=phone)
    
    await message.answer(
        f"✅ Phone: {phone}\n\n"
        "Perfect! Now, do you have a Telegram channel where you want to post products?\n\n"
        "If yes, send me the channel username (e.g., @mychannel)\n"
        "If no, just type 'skip'",
        reply_markup=ReplyKeyboardRemove()
    )
    
    await state.set_state(OnboardingStates.seller_channel)

@router.message(OnboardingStates.seller_phone)
async def seller_phone_text_received(message: Message, state: FSMContext):
    """Receive seller phone as text"""
    phone = message.text.strip()
    
    # Basic validation
    if len(phone) < 7:
        await message.answer("❌ Please enter a valid phone number:")
        return
    
    await state.update_data(phone=phone)
    
    await message.answer(
        f"✅ Phone: {phone}\n\n"
        "Perfect! Now, do you have a Telegram channel where you want to post products?\n\n"
        "If yes, send me the channel username (e.g., @mychannel)\n"
        "If no, just type 'skip'",
        reply_markup=ReplyKeyboardRemove()
    )
    
    await state.set_state(OnboardingStates.seller_channel)

@router.message(OnboardingStates.seller_channel)
async def seller_channel_received(message: Message, state: FSMContext):
    """Receive seller channel (optional)"""
    channel = message.text.strip()
    
    # Get all stored data
    data = await state.get_data()
    
    # Create seller user
    if channel.lower() != 'skip':
        # Clean channel username
        if not channel.startswith('@'):
            channel = '@' + channel
        channel_username = channel
    else:
        channel_username = None
    
    user = await db.create_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        role="seller"
    )
    
    # Update seller-specific fields
    await db.update_user(
        user_id=user.id,
        store_name=data['store_name'],
        phone=data['phone'],
        channel_username=channel_username
    )
    
    welcome_message = (
        f"🎉 **Congratulations, {data['store_name']}!**\n\n"
        "Your store is ready! Here's what you can do:\n\n"
        "📦 /addproduct - Add a new product\n"
        "📋 /myproducts - View all your products\n"
        "⏰ /schedule - Schedule auto-posting\n"
        "👥 /buyers - See your customers\n"
        "📊 /stats - View statistics\n"
        "💎 /upgrade - Go Premium (unlimited products!)\n\n"
    )
    
    if channel_username:
        welcome_message += f"📢 Your channel: {channel_username}\n\n"
    
    welcome_message += (
        "💡 **Quick Start:**\n"
        "1. Add your first product with /addproduct\n"
        "2. I'll watermark it with your store name\n"
        "3. Post it to your channel or share inline\n\n"
        "Let's grow your business! 🚀"
    )
    
    await message.answer(welcome_message)
    await state.clear()
    
    logger.info(f"Seller registered: {user.id} - {data['store_name']}")

# Help command
@router.message(F.text == "/help")
async def cmd_help(message: Message):
    """Show help information"""
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    
    if not user:
        await message.answer(
            "👋 Welcome! Use /start to get started."
        )
        return
    
    if user.role == "seller":
        help_text = (
            "📖 **SF Bot Help - Seller Guide**\n\n"
            "**Product Management:**\n"
            "📦 /addproduct - Add new product with photo\n"
            "📋 /myproducts - View & manage products\n"
            "✏️ /editproduct - Edit product details\n\n"
            "**Posting & Automation:**\n"
            "⏰ /schedule - Auto-post products to channel\n"
            "📢 /post - Manually post product now\n\n"
            "**Customer Management:**\n"
            "👥 /buyers - View customers who ordered\n"
            "📊 /stats - View engagement statistics\n\n"
            "**Account:**\n"
            "💎 /upgrade - Upgrade to Premium\n"
            "⚙️ /settings - Update store settings\n\n"
            "**Premium Features (500 birr/month):**\n"
            "• Unlimited products (free: 10 max)\n"
            "• Advanced analytics\n"
            "• Multi-channel posting\n"
            "• Priority support\n\n"
            "Need help? Contact support."
        )
    else:
        help_text = (
            "📖 **SF Bot Help - Buyer Guide**\n\n"
            "**Browse Products:**\n"
            "🔍 Inline search: Type @ethiostorebot <keyword> in any chat\n"
            "📱 /browse - Browse latest products\n\n"
            "**Ordering:**\n"
            "1. Click 🛒 Order button on any product\n"
            "2. Enter quantity and details\n"
            "3. Your order is sent to the seller\n\n"
            "**Saved Products:**\n"
            "💾 /saved - View your saved products\n\n"
            "**Engagement:**\n"
            "❤️ Like products you love\n"
            "💾 Save for later\n"
            "📞 Call seller directly\n\n"
            "Happy shopping! 🛍️"
        )
    
    await message.answer(help_text)



