"""
Product management feature
Handles product creation, editing, and listing
"""
import os
import time
import asyncio
import aiogram
from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, CallbackQuery, FSInputFile, InputMediaPhoto
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from asgiref.sync import sync_to_async

from database.db import db
from telegram_bot.models import Product
from utils.watermark import add_watermark
from utils.helpers import (format_price, create_product_keyboard, format_product_caption, 
                          escape_markdown, create_product_carousel_keyboard, create_cancel_keyboard)
from utils.logger import logger
from config import app_config, bot_config

router = Router()

# In-memory buffer for collecting album (media group) photos.
# Key: media_group_id, Value: list of dicts with message and file info
album_buffer = {}
# Track which album ids already have a scheduled processing task so we
# don't schedule multiple prompts for the same media_group_id.
album_tasks_scheduled: set[str] = set()

@router.callback_query(F.data == "cancel_fsm")
async def handle_cancel_fsm(callback: CallbackQuery, state: FSMContext):
    """Handle cancel button for any FSM state"""
    try:
        await state.clear()
        await callback.message.edit_text(
            "✅ **Operation cancelled**\n\n"
            "You can now use other bot commands\\.",
            parse_mode="MarkdownV2"
        )
        await callback.answer("Operation cancelled")
        logger.info(f"User {callback.from_user.id} cancelled FSM operation")
    except Exception as e:
        logger.error(f"Error handling cancel FSM: {e}")
        try:
            await callback.answer("❌ Error cancelling operation", show_alert=True)
        except:
            pass

def create_edit_keyboard(product_id: int) -> InlineKeyboardMarkup:
    """Create edit keyboard for product"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✏️ Edit Title", callback_data=f"edit_title_{product_id}"),
            InlineKeyboardButton(text="📝 Edit Description", callback_data=f"edit_desc_{product_id}")
        ],
        [
            InlineKeyboardButton(text="💰 Edit Price", callback_data=f"edit_price_{product_id}"),
            InlineKeyboardButton(text="📁 Edit Category", callback_data=f"edit_category_{product_id}")
        ],
        [
            InlineKeyboardButton(text="🖼️ Edit Photo", callback_data=f"edit_photo_{product_id}")
        ],
        [
            InlineKeyboardButton(text="🗑️ Delete Product", callback_data=f"delete_product_{product_id}")
        ],
        [
            InlineKeyboardButton(text="🔙 Back to Product", callback_data=f"view_{product_id}")
        ]
    ])

def create_edit_buttons_keyboard(product) -> InlineKeyboardMarkup:
    """Create edit buttons keyboard for button settings"""
    buttons = []
    
    # Like button toggle
    like_text = "🔴 Disable Like" if product.like_enabled else "🟢 Enable Like"
    buttons.append([
        InlineKeyboardButton(text=like_text, callback_data=f"toggle_like_{product.id}")
    ])
    
    # Save button toggle
    save_text = "🔴 Disable Save" if product.save_enabled else "🟢 Enable Save"
    buttons.append([
        InlineKeyboardButton(text=save_text, callback_data=f"toggle_save_{product.id}")
    ])
    
    # Order button toggle
    order_text = "🔴 Disable Orders" if product.order_enabled else "🟢 Enable Orders"
    buttons.append([
        InlineKeyboardButton(text=order_text, callback_data=f"toggle_order_{product.id}")
    ])
    
    # Add custom button
    if product.custom_button_text and product.custom_button_url:
        # Show edit and delete buttons side by side
        buttons.append([
            InlineKeyboardButton(text=f"✏️ Edit {product.custom_button_text}", callback_data=f"edit_custom_{product.id}"),
            InlineKeyboardButton(text=f"🗑️ Delete {product.custom_button_text}", callback_data=f"delete_custom_{product.id}")
        ])
        # Add premium "Add Button" below
        buttons.append([
            InlineKeyboardButton(text="💎 Add Button", callback_data=f"add_custom_{product.id}")
        ])
    else:
        buttons.append([
            InlineKeyboardButton(text="➕ Add Custom Button", callback_data=f"add_custom_{product.id}")
        ])
    
    # Back to product view
    buttons.append([
        InlineKeyboardButton(text="🔙 Back to Product", callback_data=f"view_{product.id}")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

async def show_my_product_carousel(message_or_callback, user_id: int, products: list, index: int, edit_mode: bool = False):
    """
    Show product in carousel view
    
    Args:
        message_or_callback: Message or CallbackQuery object
        user_id: User ID
        products: List of products
        index: Current product index
        edit_mode: Whether we're editing an existing message
    """
    if not products or index < 0 or index >= len(products):
        return
    
    product = products[index]
    
    # Create detailed caption
    caption = format_product_caption(
        title=product.title,
        description=product.description,
        price=product.price,
        category=product.category,
        product_type=getattr(product, 'product_type', 'standard'),
        category_fields=getattr(product, 'category_fields', None)
    )
    
    # Add owner stats
    status_emoji = "✅" if product.is_active else "❌"
    caption += f"\n\n📊 **Your Product Stats:**\n"
    caption += f"Status: {status_emoji} {'Active' if product.is_active else 'Inactive'}\n"
    caption += f"Views: {product.views_count}\n"
    caption += f"Created: {escape_markdown(product.created_at.strftime('%b %d, %Y'))}\n\n"
    caption += f"🔧 /edit\\_buttons\\_{product.id}"
    
    # Create carousel keyboard
    custom_button = None
    if product.custom_button_text and product.custom_button_url:
        custom_button = (product.custom_button_text, product.custom_button_url)
    
    keyboard = create_product_carousel_keyboard(
        product_id=product.id,
        current_index=index,
        total_count=len(products),
        show_admin_buttons=True,
        show_post_button=True,
        likes_count=product.likes_count,
        saves_count=product.saves_count,
        like_enabled=product.like_enabled,
        save_enabled=product.save_enabled,
        order_enabled=product.order_enabled,
        custom_button=custom_button
    )
    
    # Send or edit message
    try:
        if edit_mode and isinstance(message_or_callback, CallbackQuery):
            # Edit existing message - use FSInputFile for media
            photo = FSInputFile(product.image_path)
            await message_or_callback.message.edit_media(
                media=InputMediaPhoto(
                    media=photo,
                    caption=caption
                ),
                reply_markup=keyboard
            )
        else:
            # Send new message
            photo = FSInputFile(product.image_path)
            msg = message_or_callback if isinstance(message_or_callback, Message) else message_or_callback.message
            await msg.answer_photo(
                photo=photo,
                caption=caption,
                reply_markup=keyboard
            )
    except Exception as e:
        logger.error(f"Error showing product carousel: {e}")
        msg = message_or_callback if isinstance(message_or_callback, Message) else message_or_callback.message
        await msg.answer("❌ Error loading product")

# FSM States for product creation
class ProductStates(StatesGroup):
    waiting_product_type = State()  # standard or custom_description
    waiting_category = State()  # For standard products
    waiting_photo = State()
    waiting_main_image = State()  # For selecting main image from multiple photos
    waiting_title = State()
    waiting_description = State()
    waiting_price = State()
    waiting_category_fields = State()  # For category-specific fields
    confirming = State()
    post_action = State()

# FSM States for product editing
class EditStates(StatesGroup):
    waiting_edit_field = State()
    waiting_title = State()
    waiting_description = State()
    waiting_price = State()
    waiting_category = State()
    waiting_photo = State()
    confirming_delete = State()

# FSM States for custom button creation
class CustomButtonStates(StatesGroup):
    waiting_button_text = State()
    waiting_button_url = State()

@router.message(Command("addproduct"))
async def cmd_add_product(message: Message, state: FSMContext):
    """Start product creation process"""
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    
    if not user or user.role != "seller":
        await message.answer(
            "❌ This command is only for sellers.\n"
            "Use /start to register as a seller."
        )
        return
    
    # Check product limit for free users
    if not user.is_premium:
        products = await db.get_seller_products(user_id)
        if len(products) >= app_config.MAX_FREE_PRODUCTS:
            await message.answer(
                f"⚠️ **Free Plan Limit Reached**\n\n"
                f"You have {len(products)} products (max: {app_config.MAX_FREE_PRODUCTS}).\n\n"
                f"Upgrade to Premium for unlimited products!\n"
                f"💎 /upgrade - Only {app_config.PREMIUM_PRICE_BIRR} birr/month"
            )
            return
    
    # Show product type selection
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Standard Product", callback_data="product_type_standard")],
        [InlineKeyboardButton(text="📝 Custom Description", callback_data="product_type_custom")],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_fsm")]
    ])
    
    await message.answer(
        "📦 **Add New Product**\n\n"
        "What type of product would you like to create?\n\n"
        "• **Standard Product**: Choose category with specific fields\n"
        "• **Custom Description**: Just add your own description",
        reply_markup=keyboard
    )
    
    await state.set_state(ProductStates.waiting_product_type)

# Product type selection handlers
@router.callback_query(F.data == "product_type_standard")
async def handle_standard_product(callback: CallbackQuery, state: FSMContext):
    """Handle standard product type selection"""
    try:
        await state.update_data(product_type="standard")
        
        # Show category selection
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💻 Laptops", callback_data="category_laptops")],
            [InlineKeyboardButton(text="📱 Phones", callback_data="category_phones")],
            [InlineKeyboardButton(text="🚗 Cars", callback_data="category_cars")],
            [InlineKeyboardButton(text="🏠 Houses", callback_data="category_houses")],
            [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_fsm")]
        ])
        
        await callback.message.edit_text(
            "📦 **Standard Product**\n\n"
            "Select a category for your product:",
            reply_markup=keyboard
        )
        await state.set_state(ProductStates.waiting_category)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error handling standard product: {e}")
        await callback.answer("❌ Error", show_alert=True)

@router.callback_query(F.data == "product_type_custom")
async def handle_custom_description(callback: CallbackQuery, state: FSMContext):
    """Handle custom description product type selection"""
    try:
        await state.update_data(product_type="custom_description")
        
        await callback.message.edit_text(
            "📝 **Custom Description**\n\n"
            "Send me a **photo** first, then I'll ask for your custom description.\n"
            "(Make sure it's clear and shows the product well)"
        )
        await state.set_state(ProductStates.waiting_photo)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error handling custom description: {e}")
        await callback.answer("❌ Error", show_alert=True)

# Category selection handlers
@router.callback_query(F.data.startswith("category_"))
async def handle_category_selection(callback: CallbackQuery, state: FSMContext):
    """Handle category selection"""
    try:
        category = callback.data.replace("category_", "")
        await state.update_data(category=category)
        
        await callback.message.edit_text(
            f"📂 **Category: {category.title()}**\n\n"
            f"Now send me a **photo** of the product.\n"
            f"(Make sure it's clear and shows the product well)"
        )
        await state.set_state(ProductStates.waiting_photo)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error handling category selection: {e}")
        await callback.answer("❌ Error", show_alert=True)

async def process_single_photo(message: Message, state: FSMContext):
    """Process a single photo (fallback for single image uploads)"""
    photo = message.photo[-1]
    user_id = message.from_user.id
    timestamp = int(time.time() * 1000)
    
    # Get file info to determine extension
    file = await message.bot.get_file(photo.file_id)
    # Determine file extension from Telegram file_path (e.g., "photos/file_0.jpg" -> ".jpg")
    file_extension = os.path.splitext(file.file_path)[1] if file.file_path else ".jpg"
    if not file_extension:
        file_extension = ".jpg"  # Default fallback
    
    file_name = f"{user_id}_{timestamp}_{photo.file_id}{file_extension}"
    file_path = os.path.join(app_config.MEDIA_DIR, file_name)
    
    os.makedirs(app_config.MEDIA_DIR, exist_ok=True)
    
    await message.bot.download_file(file.file_path, file_path)
    
    # Get user info for watermark - prefer store name, then username.
    # Do not fall back to a hardcoded value so missing data is visible.
    user = await db.get_user(user_id)
    if user:
        store_name = user.store_name or user.username or ""
    else:
        store_name = ""
    
    # Watermark the image
    watermarked_path = await add_watermark(file_path, store_name, file_path)
    
    await state.update_data(
        photo_path=watermarked_path,
        photo_file_id=photo.file_id,
        main_image_index=0,
        all_images=[watermarked_path],
        all_original_images=[file_path]
    )
    
    # Get product type from state
    data = await state.get_data()
    product_type = data.get("product_type", "standard")
    
    if product_type == "custom_description":
        await message.answer(
            "✅ Photo received!\n\n"
            "Now, write your **custom description** for this product.\n"
            "You can include any details you want to share.",
            reply_markup=create_cancel_keyboard()
        )
        await state.set_state(ProductStates.waiting_description)
    else:
        await message.answer(
            "✅ Photo received!\n\n"
            "Now, what's the **product title**?\n"
            "(Keep it short and descriptive, e.g., 'iPhone 15 Pro Max')",
            reply_markup=create_cancel_keyboard()
        )
        await state.set_state(ProductStates.waiting_title)

@router.message(ProductStates.waiting_photo, F.photo)
async def product_photo_received(message: Message, state: FSMContext):
    """Receive product photo(s).

    New behaviour:
    - Every photo (single or album) is just collected into state.
    - On the first photo, we prompt the user and show a
      "✅ Done adding photos" button.
    - When the user taps that button, a separate callback decides
      between single-photo and multi-photo processing.
    """

    try:
        user_id = message.from_user.id
        data = await state.get_data()

        collected_photos = data.get("collected_photos", [])
        media_group_id = message.media_group_id

        # Get the largest photo in this message
        photo = message.photo[-1]
        timestamp = int(time.time() * 1000)

        # Determine file extension from Telegram file_path
        file = await message.bot.get_file(photo.file_id)
        file_extension = os.path.splitext(file.file_path)[1] if file.file_path else ".jpg"
        if not file_extension:
            file_extension = ".jpg"

        file_name = f"{user_id}_{timestamp}_{photo.file_id}{file_extension}"
        file_path = os.path.join(app_config.MEDIA_DIR, file_name)

        os.makedirs(app_config.MEDIA_DIR, exist_ok=True)
        await message.bot.download_file(file.file_path, file_path)

        # If this message is part of an album (media_group_id is set),
        # buffer it in memory keyed by the group id. After a short delay,
        # we'll process the whole album at once and send a single prompt.
        if media_group_id:
            group_id = str(media_group_id)
            if group_id not in album_buffer:
                album_buffer[group_id] = []
            album_buffer[group_id].append(
                {
                    "message": message,
                    "original_path": file_path,
                    "file_id": photo.file_id,
                }
            )

            # Schedule album processing only once per group id.
            if group_id not in album_tasks_scheduled:
                album_tasks_scheduled.add(group_id)
                asyncio.create_task(_process_album_later(group_id, state))
            return

        # For non-album photos, record directly into collected_photos
        collected_photos.append(
            {
                "original_path": file_path,
                "file_id": photo.file_id,
                "media_group_id": None,
            }
        )
        await state.update_data(collected_photos=collected_photos)

        # Compute remaining capacity (max 8 photos total)
        remaining = max(0, 8 - len(collected_photos))

        # For standalone photos (no media_group_id), send confirmations
        if len(collected_photos) == 1:
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="✅ Done adding photos",
                            callback_data="photos_done",
                        )
                    ],
                    [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_fsm")],
                ]
            )

            await message.answer(
                "✅ Photo received!\n\n"
                f"You can send up to {remaining} more photo{'s' if remaining != 1 else ''} for this product.\n"
                "When you're finished, tap *Done adding photos*.",
                reply_markup=keyboard,
            )
        else:
            # For additional standalone photos, send a light confirmation
            await message.answer(
                "📸 Additional photo received. Send more or tap *Done adding photos* when finished.",
                reply_markup=create_cancel_keyboard(),
            )

    except Exception as e:
        logger.error(f"Error processing photo: {e}")
        await message.answer("❌ Error processing photo. Please try again.", reply_markup=create_cancel_keyboard())


async def _process_album_later(group_id: str, state: FSMContext):
    """After a small delay, process a buffered album and send one prompt.

    This matches the common media_group pattern: buffer all parts keyed by
    media_group_id, wait briefly so all items arrive, then treat them as a
    single batch.
    """
    try:
        await asyncio.sleep(0.4)

        photos = album_buffer.get(group_id)
        if not photos:
            # Nothing buffered; also clear any scheduled flag
            if group_id in album_tasks_scheduled:
                album_tasks_scheduled.discard(group_id)
            return

        # Use the last message in the album as the context for replies
        last_message = photos[-1]["message"]

        # Merge album photos into FSM collected_photos
        data = await state.get_data()
        collected_photos = data.get("collected_photos", [])

        for item in photos:
            collected_photos.append(
                {
                    "original_path": item["original_path"],
                    "file_id": item["file_id"],
                    "media_group_id": group_id,
                }
            )

        await state.update_data(collected_photos=collected_photos)

        # Clear buffer and scheduled flag for this album id
        del album_buffer[group_id]
        if group_id in album_tasks_scheduled:
            album_tasks_scheduled.discard(group_id)

        # Recompute remaining capacity (max 8 photos total) now that the
        # album photos have been merged into state
        remaining = max(0, 8 - len(collected_photos))

        # Send a single "Photo received" prompt with Done button
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Done adding photos",
                        callback_data="photos_done",
                    )
                ],
                [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_fsm")],
            ]
        )

        await last_message.answer(
            "✅ Photo received!\n\n"
            f"You can send up to {remaining} more photo{'s' if remaining != 1 else ''} for this product.\n"
            "When you're finished, tap *Done adding photos*.",
            reply_markup=keyboard,
        )

    except Exception as e:
        logger.error(f"Error processing album for group {group_id}: {e}")

async def process_multiple_photos(message: Message, state: FSMContext, collected_photos: list):
    """Process multiple photos: watermark each and ask for main image selection"""
    try:
        user_id = message.from_user.id
        user = await db.get_user(user_id)
        if user:
            store_name = user.store_name or user.username or ""
        else:
            store_name = ""
        
        # Watermark all photos separately
        watermarked_paths = []
        original_paths = []
        
        for i, photo_data in enumerate(collected_photos):
            original_path = photo_data['original_path']
            # Create watermarked version - save to separate file to preserve original
            base, ext = os.path.splitext(original_path)
            watermarked_path = f"{base}_watermarked{ext}"
            
            # Watermark the image (preserves original, creates new watermarked file)
            watermarked_path = await add_watermark(original_path, store_name, watermarked_path)
            
            if watermarked_path and os.path.exists(watermarked_path):
                watermarked_paths.append(watermarked_path)
                original_paths.append(original_path)
                logger.info(f"Watermarked image {i+1}/{len(collected_photos)}: {watermarked_path}")
        
        if not watermarked_paths:
            await message.answer("❌ Failed to process photos. Please try again.", reply_markup=create_cancel_keyboard())
            return
        
        # Store all images in state
        await state.update_data(
            all_images=watermarked_paths,
            all_original_images=original_paths
        )
        
        # Send all watermarked images as media group with selection buttons
        media_group = []
        for i, img_path in enumerate(watermarked_paths):
            photo = FSInputFile(img_path)
            media_group.append(InputMediaPhoto(media=photo))
        
        # Send media group
        await message.answer_media_group(media=media_group)
        
        # Create selection buttons - one button per image
        buttons = []
        for i in range(len(watermarked_paths)):
            buttons.append([InlineKeyboardButton(
                text=f"🖼️ Image {i+1} (Select as Main)",
                callback_data=f"select_main_{i}"
            )])
        buttons.append([InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_fsm")])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await message.answer(
            "📸 **Select Main Image**\n\n"
            f"You uploaded {len(watermarked_paths)} images. "
            "Please select which one should be the **main product image**.\n\n"
            "The main image will be shown with the product description and buttons. "
            "Other images will be shown in a gallery.",
            reply_markup=keyboard
        )
        
        await state.set_state(ProductStates.waiting_main_image)
        
    except Exception as e:
        logger.error(f"Error processing multiple photos: {e}")
        await message.answer("❌ Error processing photos. Please try again.", reply_markup=create_cancel_keyboard())

@router.callback_query(F.data == "photos_done", ProductStates.waiting_photo)
async def handle_photos_done(callback: CallbackQuery, state: FSMContext):
    """User indicates they are done sending photos; decide single vs multi flow."""
    try:
        data = await state.get_data()
        collected_photos = data.get("collected_photos", [])

        if not collected_photos:
            await callback.answer("You haven't sent any photos yet.", show_alert=True)
            return

        # Build a fake message-like object using the callback's message
        # so we can reuse process_single_photo/process_multiple_photos.
        message = callback.message

        if len(collected_photos) == 1:
            await process_single_photo(message, state)
        else:
            await process_multiple_photos(message, state, collected_photos)

        await callback.answer()

    except Exception as e:
        logger.error(f"Error finalizing photos: {e}")
        try:
            await callback.answer("❌ Error processing photos", show_alert=True)
        except:
            pass

@router.callback_query(F.data.startswith("select_main_"), ProductStates.waiting_main_image)
async def handle_main_image_selection(callback: CallbackQuery, state: FSMContext):
    """Handle main image selection from multiple photos"""
    try:
        main_index = int(callback.data.split("_")[-1])
        data = await state.get_data()
        all_images = data.get("all_images", [])
        all_original_images = data.get("all_original_images", [])
        
        if main_index < 0 or main_index >= len(all_images):
            await callback.answer("❌ Invalid selection", show_alert=True)
            return
        
        # Store main image index and paths
        main_image_path = all_images[main_index]
        main_original_path = all_original_images[main_index]
        
        await state.update_data(
            photo_path=main_image_path,
            original_photo_path=main_original_path,
            main_image_index=main_index,
            all_images=all_images,
            all_original_images=all_original_images
        )
        
        await callback.answer(f"✅ Image {main_index + 1} selected as main image")
        
        # Get product type from state
        product_type = data.get("product_type", "standard")
        
        if product_type == "custom_description":
            await callback.message.answer(
                "✅ Main image selected!\n\n"
                "Now, write your **custom description** for this product.\n"
                "You can include any details you want to share.",
                reply_markup=create_cancel_keyboard()
            )
            await state.set_state(ProductStates.waiting_description)
        else:
            await callback.message.answer(
                "✅ Main image selected!\n\n"
                "Now, what's the **product title**?\n"
                "(Keep it short and descriptive, e.g., 'iPhone 15 Pro Max')",
                reply_markup=create_cancel_keyboard()
            )
            await state.set_state(ProductStates.waiting_title)
            
    except Exception as e:
        logger.error(f"Error handling main image selection: {e}")
        await callback.answer("❌ Error selecting main image", show_alert=True)

@router.message(ProductStates.waiting_photo)
async def product_photo_invalid(message: Message):
    """Handle invalid photo input"""
    await message.answer(
        "❌ Please send a photo of the product.\n"
        "Use the attachment button to send an image.\n\n"
        "You can send multiple images at once by selecting them together."
    )

@router.message(ProductStates.waiting_title)
async def product_title_received(message: Message, state: FSMContext):
    """Receive product title"""
    title = message.text.strip()
    
    if len(title) < 3:
        await message.answer("❌ Title must be at least 3 characters. Please try again:")
        return
    
    if len(title) > 200:
        await message.answer("❌ Title is too long (max 200 characters). Please shorten it:")
        return
    
    await state.update_data(title=title)
    
    # Get product type from state
    data = await state.get_data()
    product_type = data.get("product_type", "standard")
    
    if product_type == "custom_description":
        # For custom description, ask for price
        await message.answer(
            f"✅ **Name: {title}**\n\n"
            "Now, what's the **price** in Birr?\n"
            "(Just enter the number, e.g., 2500)",
            reply_markup=create_cancel_keyboard()
        )
        await state.set_state(ProductStates.waiting_price)
    else:
        # For standard products, ask for description
        await message.answer(
            f"✅ Title: **{title}**\n\n"
            "Great! Now add a **description**.\n"
            "(Tell buyers about the product - features, condition, size, etc.)\n\n"
            "Or type 'skip' if you don't want to add a description.",
            reply_markup=create_cancel_keyboard()
        )
        await state.set_state(ProductStates.waiting_description)

@router.message(ProductStates.waiting_description)
async def product_description_received(message: Message, state: FSMContext):
    """Receive product description"""
    description = message.text.strip()
    
    if len(description) > 1000:
        await message.answer("❌ Description is too long (max 1000 characters). Please shorten it:")
        return
    
    await state.update_data(description=description)
    
    # Get product type from state
    data = await state.get_data()
    product_type = data.get("product_type", "standard")
    
    if product_type == "custom_description":
        # For custom description, ask for name and price
        await message.answer(
            "✅ **Description saved!**\n\n"
            "Now, what's the **product name**?\n"
            "(Keep it short and descriptive)",
            reply_markup=create_cancel_keyboard()
        )
        await state.set_state(ProductStates.waiting_title)
    else:
        # For standard products, ask for price
        await message.answer(
            "✅ Description saved!\n\n"
            "What's the **price** in Birr?\n"
            "(Just enter the number, e.g., 2500)",
            reply_markup=create_cancel_keyboard()
        )
        await state.set_state(ProductStates.waiting_price)

async def show_custom_description_preview(message: Message, state: FSMContext):
    """Show preview for custom description product"""
    try:
        data = await state.get_data()
        photo_path = data["photo_path"]  # Main image
        all_images = data.get("all_images", [])
        main_image_index = data.get("main_image_index", 0)
        description = data["description"]
        title = data.get("title", "")
        price = data.get("price", 0)
        
        # Create preview caption
        caption = f"📝 **Custom Description Preview**\n\n"
        caption += f"**Name:** {escape_markdown(title)}\n"
        caption += f"**Price:** {escape_markdown(format_price(price))}\n\n"
        caption += f"{escape_markdown(description)}"
        
        # Create confirmation keyboard
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Create Product", callback_data="confirm_product")],
            [InlineKeyboardButton(text="✏️ Edit Description", callback_data="edit_description")],
            [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_fsm")]
        ])
        
        # If we have multiple images, send media group (all except main) first, then main image
        if len(all_images) > 1:
            # Create media group with all images EXCEPT the main image
            media_group = []
            for i, img_path in enumerate(all_images):
                if i != main_image_index:  # Skip main image
                    photo = FSInputFile(img_path)
                    media_group.append(InputMediaPhoto(media=photo))
            
            # Send media group if there are other images
            if media_group:
                await message.answer_media_group(media=media_group)
            
            # Now send the main image with caption and buttons
            main_photo = FSInputFile(photo_path)
            await message.answer_photo(
                photo=main_photo,
                caption=caption,
                reply_markup=keyboard
            )
        else:
            # Single image - just send it with caption and buttons
            photo = FSInputFile(photo_path)
            await message.answer_photo(
                photo=photo,
                caption=caption,
                reply_markup=keyboard
            )
        
        await state.set_state(ProductStates.confirming)
        
    except Exception as e:
        logger.error(f"Error showing custom description preview: {e}")
        await message.answer("❌ Error creating preview")

@router.message(ProductStates.waiting_price)
async def product_price_received(message: Message, state: FSMContext):
    """Receive product price"""
    try:
        price = float(message.text.strip().replace(',', ''))
        
        if price <= 0:
            await message.answer("❌ Price must be greater than 0. Please try again:")
            return
        
        if price > 10000000:
            await message.answer("❌ Price seems too high. Please check and try again:")
            return
        
    except ValueError:
        await message.answer("❌ Invalid price. Please enter a number (e.g., 2500):")
        return
    
    await state.update_data(price=price)
    
    # Get product type from state
    data = await state.get_data()
    product_type = data.get("product_type", "standard")
    
    if product_type == "custom_description":
        # For custom description, show preview
        await show_custom_description_preview(message, state)
    else:
        # For standard products, check category
        category = data.get("category")
        
        if category:
            # Show category-specific fields
            await show_category_fields(message, state, category)
        else:
            # This shouldn't happen for standard products, but handle it
            await message.answer(
                f"✅ Price: **{format_price(price)}**\n\n"
                "Finally, what **category** is this product?\n"
                "(e.g., Electronics, Clothing, Home & Garden)\n\n"
                "Or type 'skip' to leave it uncategorized.",
                reply_markup=create_cancel_keyboard()
            )
            await state.set_state(ProductStates.waiting_category)

def get_category_fields(category: str) -> dict:
    """Get category-specific fields based on category"""
    fields = {
        "laptops": {
            "brand": "Brand (e.g., HP, Dell, MacBook)",
            "model": "Model",
            "processor": "Processor (e.g., Intel i7, AMD Ryzen 7)",
            "ram": "RAM (e.g., 8GB, 16GB)",
            "storage": "Storage (e.g., 256GB SSD, 1TB HDD)",
            "condition": "Condition (e.g., Excellent, Good, Fair)"
        },
        "phones": {
            "brand": "Brand (e.g., iPhone, Samsung, Huawei)",
            "model": "Model (e.g., iPhone 15 Pro, Galaxy S24)",
            "storage": "Storage (e.g., 128GB, 256GB)",
            "condition": "Condition (e.g., Excellent, Good, Fair)",
            "battery": "Battery Health (e.g., 95%, 87%)"
        },
        "cars": {
            "brand": "Brand (e.g., Toyota, Honda, BMW)",
            "model": "Model (e.g., Corolla, Civic, X5)",
            "year": "Year (e.g., 2020, 2019)",
            "mileage": "Mileage (e.g., 50,000 km)",
            "fuel_type": "Fuel Type (e.g., Gasoline, Diesel, Electric)",
            "condition": "Condition (e.g., Excellent, Good, Fair)"
        },
        "houses": {
            "type": "Type (e.g., Apartment, House, Villa)",
            "bedrooms": "Bedrooms (e.g., 2, 3, 4+)",
            "location": "Location/Area",
            "size": "Size (e.g., 120 sqm, 200 sqm)",
            "condition": "Condition (e.g., Excellent, Good, Needs Renovation)"
        }
    }
    return fields.get(category, {})

async def show_category_fields(message: Message, state: FSMContext, category: str):
    """Show category-specific fields to fill"""
    fields = get_category_fields(category)
    
    if not fields:
        # No specific fields for this category, show preview
        await show_product_preview(message, state)
        return
    
    # Store fields info and start with first field
    await state.update_data(
        category_fields=fields,
        current_field_index=0,
        field_values={}
    )
    
    field_names = list(fields.keys())
    first_field = field_names[0]
    field_label = fields[first_field]
    
    await message.answer(
        f"📋 **{category.title()} Details**\n\n"
        f"**{field_label}**\n"
        f"Please enter the value for this field:",
        reply_markup=create_cancel_keyboard()
    )
    
    await state.set_state(ProductStates.waiting_category_fields)

@router.message(ProductStates.waiting_category_fields)
async def category_field_received(message: Message, state: FSMContext):
    """Receive category-specific field value"""
    try:
        data = await state.get_data()
        fields = data["category_fields"]
        current_index = data["current_field_index"]
        field_values = data.get("field_values", {})
        
        field_names = list(fields.keys())
        current_field = field_names[current_index]
        field_value = message.text.strip()
        
        # Store the field value
        field_values[current_field] = field_value
        
        # Move to next field
        next_index = current_index + 1
        
        if next_index < len(field_names):
            # More fields to fill
            next_field = field_names[next_index]
            next_field_label = fields[next_field]
            
            await state.update_data(
                field_values=field_values,
                current_field_index=next_index
            )
            
            await message.answer(
                f"✅ **{fields[current_field]}** saved!\n\n"
                f"**{next_field_label}**\n"
                f"Please enter the value for this field:",
                reply_markup=create_cancel_keyboard()
            )
        else:
            # All fields filled, show preview
            await state.update_data(field_values=field_values)
            await show_product_preview(message, state)
            
    except Exception as e:
        logger.error(f"Error handling category field: {e}")
        await message.answer("❌ Error processing field value")

async def show_product_preview(message: Message, state: FSMContext):
    """Show product preview before creation"""
    try:
        data = await state.get_data()
        photo_path = data["photo_path"]  # Main image
        all_images = data.get("all_images", [])
        main_image_index = data.get("main_image_index", 0)
        product_type = data.get("product_type", "standard")
        
        if product_type == "custom_description":
            # Custom description preview
            description = data["description"]
            caption = f"📝 **Custom Description Preview**\n\n{escape_markdown(description)}"
        else:
            # Standard product preview
            title = data["title"]
            description = data.get("description", "")
            price = data["price"]
            category = data.get("category", "")
            field_values = data.get("field_values", {})
            
            # Build caption with category fields
            caption = f"🛍️ **{escape_markdown(title)}**\n"
            caption += "━━━━━━━━━━━━━━━━━━━━\n\n"
            
            if description:
                caption += f"{escape_markdown(description)}\n\n"
            
            # Add category-specific fields
            if field_values:
                for field, value in field_values.items():
                    field_label = get_category_fields(category).get(field, field).replace(" (e.g., ", "").replace(")", "")
                    caption += f"• **{field_label}**: {escape_markdown(value)}\n"
                caption += "\n"
            
            caption += f"💰 **{escape_markdown(format_price(price))}**\n"
            
            if category:
                caption += f"📂 {escape_markdown(category.title())}\n"
        
        # Create confirmation keyboard
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Create Product", callback_data="confirm_product")],
            [InlineKeyboardButton(text="✏️ Edit Details", callback_data="edit_product")],
            [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_fsm")]
        ])
        
        # If we have multiple images, send media group (all except main) first, then main image
        if len(all_images) > 1:
            # Create media group with all images EXCEPT the main image
            media_group = []
            for i, img_path in enumerate(all_images):
                if i != main_image_index:  # Skip main image
                    photo = FSInputFile(img_path)
                    # Add caption only to first image in the group
                    if len(media_group) == 0:
                        media_group.append(InputMediaPhoto(
                            media=photo,
                            caption="📸 **Product Gallery**"
                        ))
                    else:
                        media_group.append(InputMediaPhoto(media=photo))
            
            # Send media group if there are other images
            if media_group:
                await message.answer_media_group(media=media_group)
            
            # Now send the main image with caption and buttons
            main_photo = FSInputFile(photo_path)
            await message.answer_photo(
                photo=main_photo,
                caption=caption,
                reply_markup=keyboard
            )
        else:
            # Single image - just send it with caption and buttons
            photo = FSInputFile(photo_path)
            await message.answer_photo(
                photo=photo,
                caption=caption,
                reply_markup=keyboard
            )
        
        await state.set_state(ProductStates.confirming)
        
    except Exception as e:
        logger.error(f"Error showing product preview: {e}")
        await message.answer("❌ Error creating preview")

# Product creation confirmation handlers
@router.callback_query(F.data == "confirm_product")
async def handle_confirm_product(callback: CallbackQuery, state: FSMContext):
    """Handle product creation confirmation"""
    try:
        data = await state.get_data()
        user_id = callback.from_user.id
        product_type = data.get("product_type", "standard")
        
        # Use the already watermarked main image saved in state.
        # photo_path points to the watermarked file created earlier in the flow,
        # and original_photo_path (if present) points to the original.
        photo_path = data["photo_path"]              # watermarked main image
        original_photo_path = data.get("original_photo_path", photo_path)
        watermarked_path = photo_path

        # If multiple images were used, collect non-main images as gallery_paths
        gallery_paths = None
        all_images = data.get("all_images")
        main_index = data.get("main_image_index")
        if isinstance(all_images, list) and all_images and main_index is not None:
            try:
                gallery_paths = [
                    img
                    for i, img in enumerate(all_images)
                    if i != int(main_index)
                ] or None
            except Exception:
                gallery_paths = None
        
        if product_type == "custom_description":
            # Create custom description product
            product = await create_custom_description_product(
                user_id=user_id,
                title=data["title"],
                description=data["description"],
                price=data["price"],
                image_path=watermarked_path,
                original_image_path=original_photo_path,
                gallery_images=gallery_paths,
            )
        else:
            # Merge gallery images into category_fields under a private key
            field_values = data.get("field_values", {}) or {}
            if gallery_paths:
                field_values = {**field_values, "_gallery_images": gallery_paths}

            # Create standard product
            product = await create_standard_product(
                user_id=user_id,
                title=data["title"],
                description=data.get("description"),
                price=data["price"],
                category=data.get("category"),
                field_values=field_values,
                image_path=watermarked_path,
                original_image_path=original_photo_path,
            )
        
        await state.clear()
        
        # Send success message
        await callback.message.edit_caption(
            f"✅ **Product Created Successfully\\!**\n\n"
            f"Your product has been added to your store\\.\n\n"
            f"Use /myproducts to manage your products\\.",
            parse_mode="MarkdownV2"
        )
        
        # Ask if user wants to post to channel
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Post to Channel", callback_data=f"post_channel_{product.id}")],
            [InlineKeyboardButton(text="✅ Done", callback_data="done")]
        ])
        await callback.message.answer(
            "🎉 **Product Created\\!**\n\n"
            "Would you like to post this product to your channel\\?",
            reply_markup=keyboard,
            parse_mode="MarkdownV2"
        )
        
        await callback.answer("✅ Product created successfully!")
        logger.info(f"User {user_id} created product {product.id}")
    except Exception as e:
        logger.error(f"Error confirming product creation: {e}")
        await callback.answer("❌ Error creating product", show_alert=True)

@sync_to_async
def create_custom_description_product(
    user_id: int,
    title: str,
    description: str,
    price: float,
    image_path: str,
    original_image_path: str,
    gallery_images: list[str] | None = None,
) -> Product:
    """Create a custom-description product (sync ORM wrapped with sync_to_async).

    Any additional gallery image paths are stored in category_fields["_gallery_images"].
    """
    from telegram_bot.models import User

    seller, _ = User.objects.get_or_create(id=user_id)
    category_fields = {}
    if gallery_images:
        category_fields["_gallery_images"] = gallery_images

    product = Product(
        seller=seller,
        title=title,
        description=description,
        price=price,
        category=None,
        product_type="custom_description",
        category_fields=category_fields or None,
        image_path=image_path,
        original_image_path=original_image_path,
    )
    product.save()
    return product

@sync_to_async
def create_standard_product(user_id: int, title: str, description: str, price: float, 
                            category: str, field_values: dict, image_path: str, original_image_path: str) -> Product:
    """Create a standard product with category-specific fields (runs in thread via sync_to_async)."""
    from telegram_bot.models import User

    seller = User.objects.filter(id=user_id).first()
    if seller is None:
        seller = User.objects.create(id=user_id)

    product = Product(
        seller=seller,
        title=title,
        description=description,
        price=price,
        category=category,
        product_type="standard",
        category_fields=field_values,
        image_path=image_path,
        original_image_path=original_image_path
    )
    product.save()
    return product

@sync_to_async
def toggle_product_button(product_id: int, button_type: str) -> Product:
    """Toggle like/save/order flags on a product and return the updated instance."""
    from telegram_bot.models import Product as TgProduct

    product = TgProduct.objects.get(id=product_id)
    if button_type == "like":
        product.like_enabled = not product.like_enabled
    elif button_type == "save":
        product.save_enabled = not product.save_enabled
    elif button_type == "order":
        product.order_enabled = not product.order_enabled
    product.save()
    return product

@router.message(ProductStates.waiting_category)
async def product_category_received(message: Message, state: FSMContext):
    """Receive product category and show preview"""
    category = message.text.strip()
    
    if category.lower() == 'skip':
        category = None
    
    await state.update_data(category=category)
    
    # Get all data
    data = await state.get_data()
    user = await db.get_user(message.from_user.id)
    
    # Apply watermark using shop name (or username as fallback)
    store_name = None
    if user:
        store_name = user.store_name or user.username or "Shop"
    else:
        store_name = "Shop"

    watermarked_path = data['photo_path'].replace('.jpg', '_watermarked.jpg')
    await add_watermark(data['photo_path'], store_name, watermarked_path)
    
    await state.update_data(watermarked_path=watermarked_path)
    
    # Create preview caption
    caption = format_product_caption(
        title=data['title'],
        description=data.get('description'),
        price=data['price'],
        category=category,
        product_type=data.get('product_type', 'standard'),
        category_fields=data.get('field_values', None)
    )
    
    # Send preview
    photo = FSInputFile(watermarked_path)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Save Product", callback_data="product_save"),
            InlineKeyboardButton(text="❌ Cancel", callback_data="product_cancel")
        ]
    ])
    
    await message.answer_photo(
        photo=photo,
        caption=f"📦 **Product Preview**\n\n{caption}\n\n"
                "Does everything look good?",
        reply_markup=keyboard
    )
    
    await state.set_state(ProductStates.confirming)

@router.callback_query(F.data == "product_save", ProductStates.confirming)
async def product_save_confirmed(callback: CallbackQuery, state: FSMContext):
    """Save product to database"""
    await callback.answer()
    
    data = await state.get_data()
    user = await db.get_user(callback.from_user.id)
    
    # Create product in database
    product = await db.create_product(
        seller_id=user.id,
        title=data['title'],
        description=data.get('description'),
        price=data['price'],
        category=data.get('category'),
        image_path=data['watermarked_path'],
        original_image_path=data['photo_path']
    )
    
    logger.info(f"Product created: {product.id} by seller {user.id}")
    
    # Ask what to do next
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Post to Channel Now", callback_data=f"post_now_{product.id}")],
        [InlineKeyboardButton(text="⏰ Scheduled Autoposting", callback_data=f"schedule_{product.id}")],
        [InlineKeyboardButton(text="✅ Just Save (Post Later)", callback_data="post_later")]
    ])
    
    await callback.message.edit_caption(
        caption=f"✅ **Product Saved Successfully!**\n\n"
                f"Product ID: #{product.id}\n\n"
                "What would you like to do next?",
        reply_markup=keyboard
    )
    
    await state.set_state(ProductStates.post_action)

@router.callback_query(F.data == "product_cancel")
async def product_cancel(callback: CallbackQuery, state: FSMContext):
    """Cancel product creation"""
    await callback.answer()
    
    # Clean up uploaded files
    data = await state.get_data()
    try:
        if 'photo_path' in data and os.path.exists(data['photo_path']):
            os.remove(data['photo_path'])
        if 'watermarked_path' in data and os.path.exists(data['watermarked_path']):
            os.remove(data['watermarked_path'])
    except:
        pass
    
    await callback.message.edit_caption(
        caption="❌ Product creation cancelled."
    )
    
    await state.clear()

@router.callback_query(F.data.startswith("post_now_"))
async def post_product_now(callback: CallbackQuery, state: FSMContext):
    """Post product to channel immediately"""
    await callback.answer()
    
    product_id = int(callback.data.split('_')[2])
    product = await db.get_product(product_id)
    user = await db.get_user(callback.from_user.id)
    
    if not user.channel_username:
        await callback.message.edit_caption(
            caption="❌ You haven't set up a channel yet.\n"
                    "Use /settings to add your channel."
        )
        await state.clear()
        return
    
    try:
        # Create post caption and keyboard
        caption = format_product_caption(
            title=product.title,
            description=product.description,
            price=product.price,
            category=product.category,
            product_type=getattr(product, 'product_type', 'standard'),
            category_fields=getattr(product, 'category_fields', None)
        )
        
        # Create custom button if exists
        custom_button = None
        if product.custom_button_text and product.custom_button_url:
            custom_button = (product.custom_button_text, product.custom_button_url)
        
        keyboard = create_product_keyboard(
            product_id=product.id,
            seller_phone=user.phone,
            custom_button=custom_button,
            likes_count=product.likes_count,
            saves_count=product.saves_count,
            like_enabled=product.like_enabled,
            save_enabled=product.save_enabled,
            order_enabled=product.order_enabled
        )
        
        # Post to channel
        photo = FSInputFile(product.image_path)
        sent = await callback.bot.send_photo(
            chat_id=user.channel_username,
            photo=photo,
            caption=caption,
            reply_markup=keyboard
        )
        # Record message id for later edits
        try:
            await db.record_channel_post(product.id, user.channel_username, sent.message_id)
        except Exception as _:
            pass
        
        await callback.message.edit_caption(
            caption=f"✅ **Product posted to {user.channel_username}!**\n\n"
                    "Your product is now live. Good luck with sales! 🎉"
        )
        
        logger.info(f"Product {product_id} posted to {user.channel_username}")
        
    except Exception as e:
        await callback.message.edit_caption(
            caption=f"❌ Failed to post to channel.\n\n"
                    f"Error: {str(e)}\n\n"
                    "Make sure:\n"
                    "1. I'm added as admin to your channel\n"
                    "2. Channel username is correct"
        )
        logger.error(f"Failed to post product {product_id}: {e}")
    
    await state.clear()

@router.callback_query(F.data == "post_later")
async def post_product_later(callback: CallbackQuery, state: FSMContext):
    """Just save product without posting"""
    await callback.answer()
    
    await callback.message.edit_caption(
        caption="✅ **Product saved!**\n\n"
                "You can view and manage it with:\n"
                "📋 /myproducts"
    )
    
    await state.clear()

@router.message(Command("myproducts"))
async def cmd_my_products(message: Message, state: FSMContext):
    """Show seller's products in carousel view"""
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    
    if not user or user.role != "seller":
        await message.answer("❌ This command is only for sellers.")
        return
    
    products = await db.get_seller_products(user_id, active_only=False)
    
    if not products:
        await message.answer(
            "📦 **No products yet!**\n\n"
            "Add your first product with /addproduct"
        )
        return
    
    # Store products in state for navigation
    product_ids = [p.id for p in products]
    await state.update_data(myproducts_ids=product_ids, myproducts_user_id=user_id)
    
    # Show first product in carousel view
    await show_my_product_carousel(message, user_id, products, 0)

@router.callback_query(F.data.startswith("myproducts_nav_"))
async def handle_myproducts_navigation(callback: CallbackQuery, state: FSMContext):
    """Handle navigation between products in carousel view"""
    try:
        # Extract the target index from callback data
        index = int(callback.data.split("_")[-1])
        
        # Get products from state
        data = await state.get_data()
        product_ids = data.get("myproducts_ids", [])
        user_id = data.get("myproducts_user_id")
        
        if not product_ids or not user_id:
            await callback.answer("❌ Session expired. Please use /myproducts again.", show_alert=True)
            return
        
        # Get all products
        products = []
        for product_id in product_ids:
            product = await db.get_product(product_id)
            if product:
                products.append(product)
        
        if not products or index < 0 or index >= len(products):
            await callback.answer("❌ Invalid product index", show_alert=True)
            return
        
        # Show the selected product
        await show_my_product_carousel(callback, user_id, products, index, edit_mode=True)
        
        # Answer callback
        try:
            await callback.answer()
        except:
            pass  # Ignore timeout errors
            
    except Exception as e:
        logger.error(f"Error handling product navigation: {e}")
        try:
            await callback.answer("❌ Error navigating products", show_alert=True)
        except:
            pass

@router.message(F.text.regexp(r'^/edit_buttons_(\d+)$'))
async def cmd_edit_buttons(message: Message):
    """Show product with edit buttons interface"""
    import re
    match = re.match(r'^/edit_buttons_(\d+)$', message.text)
    if not match:
        return
    
    product_id = int(match.group(1))
    product = await db.get_product(product_id)
    
    if not product:
        await message.answer("❌ Product not found.")
        return
    
    # Check if user is the owner
    user_id = message.from_user.id
    if product.seller_id != user_id:
        await message.answer("❌ You can only edit your own products.")
        return
    
    # Create detailed caption
    caption = format_product_caption(
        title=product.title,
        description=product.description,
        price=product.price,
        category=product.category,
        product_type=getattr(product, 'product_type', 'standard'),
        category_fields=getattr(product, 'category_fields', None)
    )
    
    # Add owner stats
    status_emoji = "✅" if product.is_active else "❌"
    caption += f"\n\n📊 **Your Product Stats:**\n"
    caption += f"Status: {status_emoji} {'Active' if product.is_active else 'Inactive'}\n"
    caption += f"Views: {product.views_count}\n"
    caption += f"Created: {escape_markdown(product.created_at.strftime('%b %d, %Y'))}"
    
    # Create edit buttons keyboard
    keyboard = create_edit_buttons_keyboard(product)
    
    # Send product with image
    try:
        photo = FSInputFile(product.image_path)
        await message.answer_photo(
            photo=photo,
            caption=caption,
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Error showing edit buttons view: {e}")
        await message.answer("❌ Error loading product")

@router.message(F.text.regexp(r'^/view_(\d+)$'))
async def cmd_view_product(message: Message):
    """View individual product details"""
    import re
    match = re.match(r'^/view_(\d+)$', message.text)
    if not match:
        return
    
    product_id = int(match.group(1))
    product = await db.get_product(product_id)
    
    if not product:
        await message.answer("❌ Product not found.")
        return
    
    # Check if user is the owner
    user_id = message.from_user.id
    is_owner = (product.seller_id == user_id)
    
    # Get seller info
    seller = await db.get_user(product.seller_id)
    seller_name = None
    if seller:
        seller_name = getattr(seller, "store_name", None) or seller.username or "Your Store"
    
    # Create detailed caption
    caption = format_product_caption(
        title=product.title,
        description=product.description,
        price=product.price,
        category=product.category,
        engagement_stats={
            'likes_count': product.likes_count,
            'saves_count': product.saves_count,
            'orders_count': product.orders_count
        },
        seller_name=seller_name if (seller and not is_owner) else None,
        seller_phone=seller.phone if (seller and not is_owner) else None,
        product_type=getattr(product, 'product_type', 'standard'),
        category_fields=getattr(product, 'category_fields', None)
    )
    
    if is_owner:
        caption += f"\n\n📊 **Your Product Stats:**\n"
        caption += f"Status: {'✅ Active' if product.is_active else '❌ Inactive'}\n"
        caption += f"Views: {product.views_count}\n"
        caption += f"Created: {escape_markdown(product.created_at.strftime('%b %d, %Y'))}\n\n"
        caption += f"🔧 /edit\\_buttons\\_{product.id}"
    
    # Create keyboard
    custom_button = None
    if product.custom_button_text and product.custom_button_url:
        custom_button = (product.custom_button_text, product.custom_button_url)
    
    keyboard = create_product_keyboard(
        product_id=product.id,
        seller_phone=seller.phone if not is_owner else None,
        custom_button=custom_button,
        show_admin_buttons=is_owner,
        show_post_button=is_owner,  # Show "Post to Channel" for owners
        likes_count=product.likes_count,
        saves_count=product.saves_count,
        like_enabled=product.like_enabled,
        save_enabled=product.save_enabled,
        order_enabled=product.order_enabled
    )
    
    # Send product with image
    try:
        from aiogram.types import FSInputFile
        photo = FSInputFile(product.image_path)
        await message.answer_photo(
            photo=photo,
            caption=caption,
            reply_markup=keyboard
        )
    except Exception as e:
        await message.answer(
            f"{caption}\n\n❌ Could not load image: {str(e)}"
        )

@router.callback_query(F.data.startswith("post_channel_"))
async def handle_post_to_channel(callback: CallbackQuery):
    """Handle posting product to channel"""
    try:
        product_id = int(callback.data.split('_')[2])
        user_id = callback.from_user.id
        
        # Get product and verify ownership
        product = await db.get_product(product_id)
        if not product or product.seller_id != user_id:
            await callback.answer("❌ You don't own this product", show_alert=True)
            return
        
        # Get seller info
        seller = await db.get_user(user_id)
        
        if not seller.channel_username:
            await callback.answer(
                "❌ You haven't set up a channel yet. Use /settings to add your channel.",
                show_alert=True
            )
            return
        
        await callback.answer("📤 Posting to your channel...", show_alert=False)
        
        # Prepare seller display name with safe fallbacks
        seller_name = None
        if seller:
            seller_name = getattr(seller, "store_name", None) or seller.username or "Your Store"

        # Create post caption with seller info
        caption = format_product_caption(
            title=product.title,
            description=product.description,
            price=product.price,
            category=product.category,
            engagement_stats={
                'likes_count': product.likes_count,
                'saves_count': product.saves_count,
                'orders_count': product.orders_count
            },
            seller_name=seller_name,
            seller_phone=seller.phone if seller else None,
            product_type=getattr(product, 'product_type', 'standard'),
            category_fields=getattr(product, 'category_fields', None),
            for_channel=True
        )
        
        # Create custom button if exists
        custom_button = None
        if product.custom_button_text and product.custom_button_url:
            custom_button = (product.custom_button_text, product.custom_button_url)
        
        # Create keyboard for channel post
        keyboard = create_product_keyboard(
            product_id=product.id,
            seller_phone=seller.phone,
            custom_button=custom_button,
            likes_count=product.likes_count,
            saves_count=product.saves_count,
            like_enabled=product.like_enabled,
            save_enabled=product.save_enabled,
            order_enabled=product.order_enabled,
        )

        # If we stored gallery images in category_fields, send them as a media group first
        try:
            gallery_images = None
            if getattr(product, "category_fields", None):
                gallery_images = product.category_fields.get("_gallery_images")

            from aiogram.types import FSInputFile, InputMediaPhoto

            if isinstance(gallery_images, list) and gallery_images:
                media_group = []
                for path in gallery_images:
                    try:
                        media_group.append(InputMediaPhoto(media=FSInputFile(path)))
                    except Exception:
                        continue
                if media_group:
                    await callback.bot.send_media_group(
                        chat_id=seller.channel_username,
                        media=media_group,
                    )

            # Now send the main image with caption and inline buttons
            photo = FSInputFile(product.image_path)
            sent = await callback.bot.send_photo(
                chat_id=seller.channel_username,
                photo=photo,
                caption=caption,
                reply_markup=keyboard,
            )
            # Record message id for later edits
            try:
                await db.record_channel_post(product.id, seller.channel_username, sent.message_id)
            except Exception:
                pass
            
            # Update message to show success
            await callback.message.answer(
                f"✅ **Product posted to {seller.channel_username}!**\n\n"
                "Your product is now live in your channel! 🎉"
            )
            
            logger.info(f"Product {product_id} posted to {seller.channel_username} by user {user_id}")
            
        except Exception as e:
            error_msg = str(e)
            if "bot is not a member" in error_msg or "Forbidden" in error_msg:
                await callback.message.answer(
                    "❌ **Failed to post to channel**\n\n"
                    f"Channel: {seller.channel_username}\n\n"
                    "**Please make sure:**\n"
                    "1. The bot (@ethiostorebot) is added to your channel\n"
                    "2. The bot has admin rights\n"
                    "3. The bot can post messages\n\n"
                    "**How to fix:**\n"
                    f"• Go to {seller.channel_username}\n"
                    "• Settings → Administrators\n"
                    "• Add @ethiostorebot\n"
                    "• Give it 'Post Messages' permission"
                )
            else:
                await callback.message.answer(
                    f"❌ **Failed to post to channel**\n\n"
                    f"Error: {error_msg}\n\n"
                    "Please check:\n"
                    "• Channel username is correct\n"
                    "• Bot has necessary permissions"
                )
            
            logger.error(f"Failed to post product {product_id} to channel: {e}")
    
    except Exception as e:
        logger.error(f"Error in post_to_channel handler: {e}")
        await callback.answer(f"❌ Error: {str(e)}", show_alert=True)

@router.callback_query(F.data.startswith("mark_sold_"))
async def handle_mark_sold(callback: CallbackQuery):
    """Mark a product as sold by editing all channel posts to show "[title] -> Sold"."""
    try:
        product_id = int(callback.data.split('_')[2])
        user_id = callback.from_user.id
        product = await db.get_product(product_id)
        if not product or product.seller_id != user_id:
            try:
                await callback.answer("❌ You don't own this product", show_alert=True)
            except:
                pass
            return
        # Fetch seller and channel posts
        seller = await db.get_user(user_id)
        posts = await db.get_channel_posts(product_id)
        if not posts:
            try:
                await callback.answer("No channel posts to update yet.")
            except:
                pass
            return
        # Build new caption
        new_title = f"{escape_markdown(product.title)} ⚠️ Sold ⚠️"
        new_caption = format_product_caption(
            title=new_title,
            description=product.description,
            price=product.price,
            category=product.category,
            seller_name=seller.store_name,
            seller_phone=seller.phone,
            product_type=getattr(product, 'product_type', 'standard'),
            category_fields=getattr(product, 'category_fields', None),
            for_channel=True
        )
        # Update all posts
        for p in posts:
            try:
                await callback.bot.edit_message_caption(
                    chat_id=p.channel_username,
                    message_id=p.message_id,
                    caption=new_caption,
                    parse_mode="MarkdownV2"
                )
            except Exception as e:
                logger.error(f"Failed to edit post {p.message_id} in {p.channel_username}: {e}")
        try:
            await callback.answer("✅ Marked as sold in channel posts")
        except:
            pass
    except Exception as e:
        logger.error(f"Error marking sold: {e}")
        try:
            await callback.answer("❌ Error marking sold", show_alert=True)
        except:
            pass
@router.callback_query(F.data.startswith("stats_"))
async def handle_product_stats(callback: CallbackQuery):
    """Show detailed stats for a product"""
    try:
        product_id = int(callback.data.split('_')[1])
        user_id = callback.from_user.id
        
        # Get product and verify ownership
        product = await db.get_product(product_id)
        if not product:
            await callback.answer("❌ Product not found", show_alert=True)
            return
        
        if product.seller_id != user_id:
            await callback.answer("❌ You don't own this product", show_alert=True)
            return
        
        await callback.answer()
        
        # Calculate engagement rate
        total_engagement = product.likes_count + product.saves_count + product.orders_count
        views = max(product.views_count, 1)  # Avoid division by zero
        engagement_rate = (total_engagement / views) * 100 if views > 0 else 0
        
        # Get order details using Django ORM
        from telegram_bot.models import Order
        from django.db.models import Sum, Count
        
        # Total revenue
        total_quantity = Order.objects.filter(product_id=product_id).aggregate(
            total=Sum('quantity')
        )['total'] or 0
        total_revenue = total_quantity * product.price
        
        # Pending orders
        pending_orders = Order.objects.filter(
            product_id=product_id,
            status='pending'
        ).count()
        
        # Create stats message
        # Escape markdown in product title
        safe_title = product.title.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace('`', '\\`')
        stats_msg = (
            f"📊 **Product Statistics**\n\n"
            f"**{safe_title}**\n"
            f"{'─' * 30}\n\n"
            f"💰 **Sales Performance:**\n"
            f"• Total Orders: {product.orders_count}\n"
            f"• Items Sold: {total_quantity}\n"
            f"• Revenue: {format_price(total_revenue)}\n"
            f"• Pending Orders: {pending_orders}\n\n"
            f"📈 **Engagement:**\n"
            f"• Views: {product.views_count}\n"
            f"• Likes: {product.likes_count} ❤️\n"
            f"• Saves: {product.saves_count} 💾\n"
            f"• Engagement Rate: {engagement_rate:.1f}%\n\n"
            f"📅 **Timeline:**\n"
            f"• Created: {product.created_at.strftime('%b %d, %Y at %I:%M %p')}\n"
            f"• Status: {'✅ Active' if product.is_active else '❌ Inactive'}\n"
            f"• Visibility: {'🌍 Public' if product.is_public else '🔒 Private'}\n\n"
            f"💵 **Pricing:**\n"
            f"• Current Price: {format_price(product.price)}\n"
            f"• Category: {product.category or 'Uncategorized'}"
        )
        
        await callback.message.answer(stats_msg)
        
        logger.info(f"Stats viewed for product {product_id} by user {user_id}")
        
    except Exception as e:
        logger.error(f"Error showing product stats: {e}")
        await callback.answer(f"❌ Error loading stats", show_alert=True)

@router.message(Command("stats"))
async def cmd_stats(message: Message):
    """Show overall seller statistics"""
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    
    if not user or user.role != "seller":
        await message.answer("❌ This command is only for sellers.")
        return
    
    # Get all seller's products
    products = await db.get_seller_products(user_id, active_only=False)
    
    if not products:
        await message.answer(
            "📊 **Your Statistics**\n\n"
            "No products yet! Add your first product with /addproduct"
        )
        return
    
    # Calculate overall stats
    total_products = len(products)
    active_products = sum(1 for p in products if p.is_active)
    total_likes = sum(p.likes_count for p in products)
    total_saves = sum(p.saves_count for p in products)
    total_orders = sum(p.orders_count for p in products)
    total_views = sum(p.views_count for p in products)
    
    # Get detailed order stats using Django ORM
    from telegram_bot.models import Order
    
    # Calculate revenue manually by iterating through orders
    orders = Order.objects.filter(seller_id=user_id).select_related('product')
    total_revenue = 0
    for order in orders:
        if order.product:
            total_revenue += order.quantity * order.product.price
    
    # Pending orders
    pending_orders = Order.objects.filter(
        seller_id=user_id,
        status='pending'
    ).count()
    
    # Completed orders
    completed_orders = Order.objects.filter(
        seller_id=user_id,
        status='completed'
    ).count()
    
    # Calculate engagement rate
    total_engagement = total_likes + total_saves + total_orders
    engagement_rate = (total_engagement / max(total_views, 1)) * 100
    
    # Find best performing product
    best_product = max(products, key=lambda p: p.orders_count) if products else None
    
    # Escape markdown in store name
    safe_store_name = (user.store_name or "Your Store").replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace('`', '\\`')
    
    # Create stats message
    stats_msg = (
        f"📊 **Your Store Statistics**\n\n"
        f"🏪 **{safe_store_name}**\n"
        f"{'═' * 30}\n\n"
        f"📦 **Products:**\n"
        f"• Total Products: {total_products}\n"
        f"• Active: {active_products}\n"
        f"• Inactive: {total_products - active_products}\n\n"
        f"💰 **Sales Performance:**\n"
        f"• Total Orders: {total_orders}\n"
        f"• Pending: {pending_orders}\n"
        f"• Completed: {completed_orders}\n"
        f"• Total Revenue: {format_price(total_revenue)}\n\n"
        f"📈 **Engagement:**\n"
        f"• Total Views: {total_views}\n"
        f"• Total Likes: {total_likes} ❤️\n"
        f"• Total Saves: {total_saves} 💾\n"
        f"• Engagement Rate: {engagement_rate:.1f}%\n\n"
    )
    
    if best_product and best_product.orders_count > 0:
        # Escape product title
        safe_title = best_product.title.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace('`', '\\`')
        stats_msg += (
            f"🏆 **Best Seller:**\n"
            f"• {safe_title}\n"
            f"• {best_product.orders_count} orders\n"
            f"• {format_price(best_product.price)}\n\n"
        )
    
    stats_msg += (
        f"👥 **Customers:**\n"
        f"• Use /buyers to view customer list\n\n"
        f"📅 **Account:**\n"
        f"• Member since: {user.created_at.strftime('%b %d, %Y')}\n"
        f"• Status: {'💎 Premium' if user.is_premium else '🆓 Free'}\n"
    )
    
    if not user.is_premium and total_products >= app_config.MAX_FREE_PRODUCTS:
        stats_msg += f"\n⚠️ You've reached the free limit ({app_config.MAX_FREE_PRODUCTS} products)\n💎 /upgrade to add unlimited products!"
    
    await message.answer(stats_msg)
    
    logger.info(f"Overall stats viewed by seller {user_id}")

@router.callback_query(F.data.regexp(r'^edit_\d+$'))
async def handle_edit_product(callback: CallbackQuery):
    """Handle edit product button - show product details with edit options"""
    try:
        product_id = int(callback.data.split('_')[1])
        user_id = callback.from_user.id
        
        product = await db.get_product(product_id)
        if not product or product.seller_id != user_id:
            try:
                await callback.answer("❌ You don't own this product", show_alert=True)
            except Exception:
                pass  # Ignore callback answer errors
            return
        
        try:
            await callback.answer()
        except Exception:
            pass  # Ignore callback answer errors (query too old, etc.)
        
        # Get seller info
        seller = await db.get_user(product.seller_id)
        
        # Format product details
        caption = f"✏️ **Edit Product**\n\n"
        caption += f"🛍️ **{escape_markdown(product.title)}**\n\n"
        
        if product.description:
            caption += f"{escape_markdown(product.description)}\n\n"
        
        caption += f"💰 **Price:** {escape_markdown(format_price(product.price))}\n"
        
        if product.category:
            caption += f"📁 **Category:** {escape_markdown(product.category)}\n"
        
        caption += f"🏪 **Store:** {escape_markdown(seller.store_name)}\n"
        caption += f"📊 **Stats:** ❤️ {product.likes_count} • 💾 {product.saves_count} • 🛒 {product.orders_count}\n"
        caption += f"📅 **Created:** {escape_markdown(product.created_at.strftime('%B %d, %Y'))}"
        
        # Send product with edit keyboard
        if product.image_path and os.path.exists(product.image_path):
            photo = FSInputFile(product.image_path)
            await callback.message.answer_photo(
                photo=photo,
                caption=caption,
                parse_mode="MarkdownV2",
                reply_markup=create_edit_keyboard(product_id)
            )
        else:
            await callback.message.answer(
                text=caption,
                parse_mode="MarkdownV2",
                reply_markup=create_edit_keyboard(product_id)
            )
        
        logger.info(f"Edit mode shown for product {product_id} by user {user_id}")
        
    except Exception as e:
        logger.error(f"Error handling edit product: {e}")
        try:
            await callback.answer("❌ Error loading edit form", show_alert=True)
        except Exception:
            pass  # Ignore callback answer errors

# Edit field button handlers
@router.callback_query(F.data.startswith("edit_title_"))
async def handle_edit_title_button(callback: CallbackQuery, state: FSMContext):
    """Handle edit title button"""
    try:
        product_id = int(callback.data.split('_')[2])
        user_id = callback.from_user.id
        
        product = await db.get_product(product_id)
        if not product or product.seller_id != user_id:
            await callback.answer("❌ You don't own this product", show_alert=True)
            return
        
        await callback.answer()
        
        # Store product ID and current title
        await state.update_data(product_id=product_id, current_title=product.title)
        await state.set_state(EditStates.waiting_title)
        
        await callback.message.answer(
            f"✏️ **Edit Title**\n\n"
            f"**Current Title:** {escape_markdown(product.title)}\n\n"
            f"**What do you want to change the title to?**\n\n"
            f"Send me the new title:",
            parse_mode="MarkdownV2",
            reply_markup=create_cancel_keyboard()
        )
        
        logger.info(f"User {user_id} started editing title for product {product_id}")
        
    except Exception as e:
        logger.error(f"Error starting title edit: {e}")
        await callback.answer("❌ Error starting edit", show_alert=True)

@router.callback_query(F.data.startswith("edit_desc_"))
async def handle_edit_description_button(callback: CallbackQuery, state: FSMContext):
    """Handle edit description button"""
    try:
        product_id = int(callback.data.split('_')[2])
        user_id = callback.from_user.id
        
        product = await db.get_product(product_id)
        if not product or product.seller_id != user_id:
            await callback.answer("❌ You don't own this product", show_alert=True)
            return
        
        await callback.answer()
        
        # Store product ID and current description
        await state.update_data(product_id=product_id, current_description=product.description)
        await state.set_state(EditStates.waiting_description)
        
        current_desc = product.description or "No description"
        await callback.message.answer(
            f"📝 **Edit Description**\n\n"
            f"**Current Description:** {escape_markdown(current_desc)}\n\n"
            f"**What do you want to change the description to?**\n\n"
            f"Send me the new description:",
            parse_mode="MarkdownV2",
            reply_markup=create_cancel_keyboard()
        )
        
        logger.info(f"User {user_id} started editing description for product {product_id}")
        
    except Exception as e:
        logger.error(f"Error starting description edit: {e}")
        await callback.answer("❌ Error starting edit", show_alert=True)

@router.callback_query(F.data.startswith("edit_price_"))
async def handle_edit_price_button(callback: CallbackQuery, state: FSMContext):
    """Handle edit price button"""
    try:
        product_id = int(callback.data.split('_')[2])
        user_id = callback.from_user.id
        
        product = await db.get_product(product_id)
        if not product or product.seller_id != user_id:
            await callback.answer("❌ You don't own this product", show_alert=True)
            return
        
        await callback.answer()
        
        # Store product ID and current price
        await state.update_data(product_id=product_id, current_price=product.price)
        await state.set_state(EditStates.waiting_price)
        
        await callback.message.answer(
            f"💰 **Edit Price**\n\n"
            f"**Current Price:** {format_price(product.price)}\n\n"
            f"**What do you want to change the price to?**\n\n"
            f"Send me the new price \\(number only\\):\n"
            f"Example: `500000`",
            parse_mode="MarkdownV2",
            reply_markup=create_cancel_keyboard()
        )
        
        logger.info(f"User {user_id} started editing price for product {product_id}")
        
    except Exception as e:
        logger.error(f"Error starting price edit: {e}")
        await callback.answer("❌ Error starting edit", show_alert=True)

@router.callback_query(F.data.startswith("edit_category_"))
async def handle_edit_category_button(callback: CallbackQuery, state: FSMContext):
    """Handle edit category button"""
    try:
        product_id = int(callback.data.split('_')[2])
        user_id = callback.from_user.id
        
        product = await db.get_product(product_id)
        if not product or product.seller_id != user_id:
            await callback.answer("❌ You don't own this product", show_alert=True)
            return
        
        await callback.answer()
        
        # Store product ID and current category
        await state.update_data(product_id=product_id, current_category=product.category)
        await state.set_state(EditStates.waiting_category)
        
        current_cat = product.category or "No category"
        await callback.message.answer(
            f"📁 **Edit Category**\n\n"
            f"**Current Category:** {escape_markdown(current_cat)}\n\n"
            f"**What do you want to change the category to?**\n\n"
            f"Send me the new category:",
            parse_mode="MarkdownV2",
            reply_markup=create_cancel_keyboard()
        )
        
        logger.info(f"User {user_id} started editing category for product {product_id}")
        
    except Exception as e:
        logger.error(f"Error starting category edit: {e}")
        await callback.answer("❌ Error starting edit", show_alert=True)

@router.callback_query(F.data.startswith("edit_photo_"))
async def handle_edit_photo_button(callback: CallbackQuery, state: FSMContext):
    """Handle edit photo button"""
    try:
        product_id = int(callback.data.split('_')[2])
        user_id = callback.from_user.id
        
        product = await db.get_product(product_id)
        if not product or product.seller_id != user_id:
            await callback.answer("❌ You don't own this product", show_alert=True)
            return
        
        await callback.answer()
        
        await callback.message.answer(
            f"🖼️ **Edit Photo**\n\n"
            f"**To change the product photo:**\n\n"
            f"1\\. Send me a new photo\n"
            f"2\\. I'll add the watermark automatically\n"
            f"3\\. The old photo will be replaced\n\n"
            f"**Send your new photo now:**",
            parse_mode="MarkdownV2",
            reply_markup=create_cancel_keyboard()
        )
        
        # Store product ID for photo update
        await state.update_data(product_id=product_id)
        await state.set_state(EditStates.waiting_photo)
        
        logger.info(f"User {user_id} started editing photo for product {product_id}")
        
    except Exception as e:
        logger.error(f"Error starting photo edit: {e}")
        await callback.answer("❌ Error starting edit", show_alert=True)

@router.callback_query(F.data.startswith("delete_product_"))
async def handle_delete_product_button(callback: CallbackQuery, state: FSMContext):
    """Handle delete product button"""
    try:
        product_id = int(callback.data.split('_')[2])
        user_id = callback.from_user.id
        
        product = await db.get_product(product_id)
        if not product or product.seller_id != user_id:
            await callback.answer("❌ You don't own this product", show_alert=True)
            return
        
        await callback.answer()
        
        # Store product ID for deletion
        await state.update_data(product_id=product_id, product_title=product.title)
        await state.set_state(EditStates.confirming_delete)
        
        await callback.message.answer(
            f"🗑️ **Delete Product**\n\n"
            f"**Are you sure you want to delete:**\n"
            f"**{escape_markdown(product.title)}**\n\n"
            f"⚠️ **This action cannot be undone\\!**\n\n"
            f"Type `DELETE` to confirm deletion:",
            parse_mode="MarkdownV2"
        )
        
        logger.info(f"User {user_id} started deletion for product {product_id}")
        
    except Exception as e:
        logger.error(f"Error starting deletion: {e}")
        await callback.answer("❌ Error starting deletion", show_alert=True)

@router.callback_query(F.data.startswith("view_"))
async def handle_back_to_product(callback: CallbackQuery):
    """Handle back to product button"""
    try:
        product_id = int(callback.data.split('_')[1])
        user_id = callback.from_user.id
        
        product = await db.get_product(product_id)
        if not product:
            await callback.answer("❌ Product not found", show_alert=True)
            return
        
        await callback.answer()
        
        # Check if user is owner (show admin buttons) or regular viewer
        is_owner = product.seller_id == user_id
        
        # Get seller info
        seller = await db.get_user(product.seller_id)
        
        # Create keyboard
        custom_button = None
        if product.custom_button_text and product.custom_button_url:
            custom_button = (product.custom_button_text, product.custom_button_url)
        
        keyboard = create_product_keyboard(
            product_id=product_id,
            seller_phone=seller.phone if not is_owner else None,
            custom_button=custom_button,
            show_admin_buttons=is_owner,
            show_post_button=is_owner,
            likes_count=product.likes_count,
            saves_count=product.saves_count,
            like_enabled=product.like_enabled,
            save_enabled=product.save_enabled,
            order_enabled=product.order_enabled
        )
        
        # Format caption
        caption = format_product_caption(
            title=product.title,
            description=product.description,
            price=product.price,
            category=product.category,
            engagement_stats={
                'likes_count': product.likes_count,
                'saves_count': product.saves_count,
                'orders_count': product.orders_count
            },
            seller_name=seller.store_name if not is_owner else None,
            seller_phone=seller.phone if not is_owner else None,
            product_type=getattr(product, 'product_type', 'standard'),
            category_fields=getattr(product, 'category_fields', None)
        )
        
        # Add owner stats and edit button link if user is owner
        if is_owner:
            caption += f"\n\n📊 **Your Product Stats:**\n"
            caption += f"Status: {'✅ Active' if product.is_active else '❌ Inactive'}\n"
            caption += f"Views: {product.views_count}\n"
            caption += f"Created: {escape_markdown(product.created_at.strftime('%b %d, %Y'))}\n\n"
            caption += f"🔧 /edit\\_buttons\\_{product.id}"
        
        # Send product
        if product.image_path and os.path.exists(product.image_path):
            photo = FSInputFile(product.image_path)
            await callback.message.answer_photo(
                photo=photo,
                caption=caption,
                parse_mode="MarkdownV2",
                reply_markup=keyboard
            )
        else:
            await callback.message.answer(
                text=caption,
                parse_mode="MarkdownV2",
                reply_markup=keyboard
            )
        
        logger.info(f"User {user_id} viewed product {product_id}")
        
    except Exception as e:
        logger.error(f"Error viewing product: {e}")
        await callback.answer("❌ Error loading product", show_alert=True)

# FSM message handlers for editing
@router.message(EditStates.waiting_title)
async def handle_edit_title_input(message: Message, state: FSMContext):
    """Handle title input for editing"""
    try:
        data = await state.get_data()
        product_id = data['product_id']
        new_title = message.text.strip()
        
        if not new_title:
            await message.answer("❌ Title cannot be empty. Please send a valid title:")
            return
        
        # Update title in database
        product = await db.get_product(product_id)
        if product:
            product.title = new_title
            product.save()
        
        await state.clear()
        
        await message.answer(
            f"✅ **Title Updated Successfully\\!**\n\n"
            f"**New Title:** {escape_markdown(new_title)}\n\n"
            f"Use /myproducts to see your updated products\\.",
            parse_mode="MarkdownV2"
        )
        
        logger.info(f"User {message.from_user.id} updated title for product {product_id} to: {new_title}")
        
    except Exception as e:
        logger.error(f"Error updating title: {e}")
        await message.answer("❌ Error updating title. Please try again.")
        await state.clear()

@router.message(EditStates.waiting_description)
async def handle_edit_description_input(message: Message, state: FSMContext):
    """Handle description input for editing"""
    try:
        data = await state.get_data()
        product_id = data['product_id']
        new_description = message.text.strip()
        
        # Update description in database
        product = await db.get_product(product_id)
        if product:
            product.description = new_description
            product.save()
        
        await state.clear()
        
        await message.answer(
            f"✅ **Description Updated Successfully\\!**\n\n"
            f"**New Description:** {escape_markdown(new_description)}\n\n"
            f"Use /myproducts to see your updated products\\.",
            parse_mode="MarkdownV2"
        )
        
        logger.info(f"User {message.from_user.id} updated description for product {product_id}")
        
    except Exception as e:
        logger.error(f"Error updating description: {e}")
        await message.answer("❌ Error updating description. Please try again.")
        await state.clear()

@router.message(EditStates.waiting_price)
async def handle_edit_price_input(message: Message, state: FSMContext):
    """Handle price input for editing"""
    try:
        data = await state.get_data()
        product_id = data['product_id']
        
        try:
            new_price = float(message.text.strip())
        except ValueError:
            await message.answer("❌ Invalid price format. Please send a number:\nExample: `500000`")
            return
        
        if new_price <= 0:
            await message.answer("❌ Price must be greater than 0. Please send a valid price:")
            return
        
        # Update price in database
        product = await db.get_product(product_id)
        if product:
            product.price = new_price
            product.save()
        
        await state.clear()
        
        await message.answer(
            f"✅ **Price Updated Successfully\\!**\n\n"
            f"**New Price:** {format_price(new_price)}\n\n"
            f"Use /myproducts to see your updated products\\.",
            parse_mode="MarkdownV2"
        )
        
        logger.info(f"User {message.from_user.id} updated price for product {product_id} to: {new_price}")
        
    except Exception as e:
        logger.error(f"Error updating price: {e}")
        await message.answer("❌ Error updating price. Please try again.")
        await state.clear()

@router.message(EditStates.waiting_category)
async def handle_edit_category_input(message: Message, state: FSMContext):
    """Handle category input for editing"""
    try:
        data = await state.get_data()
        product_id = data['product_id']
        new_category = message.text.strip()
        
        if not new_category:
            await message.answer("❌ Category cannot be empty. Please send a valid category:")
            return
        
        # Update category in database
        product = await db.get_product(product_id)
        if product:
            product.category = new_category
            product.save()
        
        await state.clear()
        
        await message.answer(
            f"✅ **Category Updated Successfully\\!**\n\n"
            f"**New Category:** {escape_markdown(new_category)}\n\n"
            f"Use /myproducts to see your updated products\\.",
            parse_mode="MarkdownV2"
        )
        
        logger.info(f"User {message.from_user.id} updated category for product {product_id} to: {new_category}")
        
    except Exception as e:
        logger.error(f"Error updating category: {e}")
        await message.answer("❌ Error updating category. Please try again.")
        await state.clear()

@router.message(EditStates.waiting_photo)
async def handle_edit_photo_input(message: Message, state: FSMContext):
    """Handle photo input for editing"""
    try:
        if not message.photo:
            await message.answer("❌ Please send a photo. Send your new product photo:")
            return
        
        data = await state.get_data()
        product_id = data['product_id']
        
        # Get the highest quality photo
        photo = message.photo[-1]
        
        # Download and save photo
        file = await message.bot.get_file(photo.file_id)
        file_path = f"{app_config.MEDIA_DIR}/product_{product_id}_{int(time.time())}.jpg"
        
        # Ensure directory exists
        os.makedirs(app_config.MEDIA_DIR, exist_ok=True)
        
        # Download photo
        await message.bot.download_file(file.file_path, file_path)
        
        # Get seller info for watermark
        user = await db.get_user(message.from_user.id)
        if user:
            store_name = user.store_name or user.username or "Shop"
        else:
            store_name = "Shop"
        
        # Add watermark
        watermarked_path = await add_watermark(file_path, store_name)
        
        # Update product photo in database
        product = await db.get_product(product_id)
        if product:
            # Delete old photo if it exists
            if product.image_path and os.path.exists(product.image_path):
                os.remove(product.image_path)
            
            product.image_path = watermarked_path
            product.save()
        
        await state.clear()
        
        await message.answer(
            f"✅ **Photo Updated Successfully\\!**\n\n"
            f"Your product photo has been updated with watermark\\.\n\n"
            f"Use /myproducts to see your updated products\\.",
            parse_mode="MarkdownV2"
        )
        
        logger.info(f"User {message.from_user.id} updated photo for product {product_id}")
        
    except Exception as e:
        logger.error(f"Error updating photo: {e}")
        await message.answer("❌ Error updating photo. Please try again.")
        await state.clear()

@router.message(EditStates.confirming_delete)
async def handle_delete_confirmation(message: Message, state: FSMContext):
    """Handle delete confirmation"""
    try:
        if message.text.strip().upper() != "DELETE":
            await message.answer(
                f"❌ Deletion not confirmed\\.\n\n"
                f"Type `DELETE` exactly to confirm deletion\\.",
                parse_mode="MarkdownV2"
            )
            return
        
        data = await state.get_data()
        product_id = data['product_id']
        product_title = data['product_title']
        
        # Delete product from database
        product = await db.get_product(product_id)
        if product:
            # Delete photo file if it exists
            if product.image_path and os.path.exists(product.image_path):
                os.remove(product.image_path)
            
            # Delete from database
            product.delete()
        
        await state.clear()
        
        await message.answer(
            f"✅ **Product Deleted Successfully\\!**\n\n"
            f"**Deleted:** {escape_markdown(product_title)}\n\n"
            f"Use /myproducts to see your remaining products\\.",
            parse_mode="MarkdownV2"
        )
        
        logger.info(f"User {message.from_user.id} deleted product {product_id}: {product_title}")
        
    except Exception as e:
        logger.error(f"Error deleting product: {e}")
        await message.answer("❌ Error deleting product. Please try again.")
        await state.clear()

# Toggle button handlers
@router.callback_query(F.data.startswith("toggle_like_"))
async def handle_toggle_like(callback: CallbackQuery):
    """Toggle like button enabled/disabled"""
    try:
        product_id = int(callback.data.split("_")[-1])
        product = await db.get_product(product_id)
        
        if not product or product.seller_id != callback.from_user.id:
            await callback.answer("❌ Product not found or access denied", show_alert=True)
            return
        
        # Toggle like_enabled via sync_to_async helper
        updated_product = await toggle_product_button(product_id, "like")

        # Update the message with new keyboard
        keyboard = create_edit_buttons_keyboard(updated_product)
        await callback.message.edit_reply_markup(reply_markup=keyboard)
        
        status = "enabled" if updated_product.like_enabled else "disabled"
        await callback.answer(f"✅ Like button {status}")
                
    except Exception as e:
        logger.error(f"Error toggling like button: {e}")
        await callback.answer("❌ Error updating button settings", show_alert=True)

@router.callback_query(F.data.startswith("toggle_save_"))
async def handle_toggle_save(callback: CallbackQuery):
    """Toggle save button enabled/disabled"""
    try:
        product_id = int(callback.data.split("_")[-1])
        product = await db.get_product(product_id)
        
        if not product or product.seller_id != callback.from_user.id:
            await callback.answer("❌ Product not found or access denied", show_alert=True)
            return
        
        # Toggle save_enabled via sync_to_async helper
        updated_product = await toggle_product_button(product_id, "save")

        # Update the message with new keyboard
        keyboard = create_edit_buttons_keyboard(updated_product)
        await callback.message.edit_reply_markup(reply_markup=keyboard)
        
        status = "enabled" if updated_product.save_enabled else "disabled"
        await callback.answer(f"✅ Save button {status}")
                
    except Exception as e:
        logger.error(f"Error toggling save button: {e}")
        await callback.answer("❌ Error updating button settings", show_alert=True)

@router.callback_query(F.data.startswith("toggle_order_"))
async def handle_toggle_order(callback: CallbackQuery):
    """Toggle order button enabled/disabled"""
    try:
        product_id = int(callback.data.split("_")[-1])
        product = await db.get_product(product_id)
        
        if not product or product.seller_id != callback.from_user.id:
            await callback.answer("❌ Product not found or access denied", show_alert=True)
            return
        
        # Toggle order_enabled via sync_to_async helper
        updated_product = await toggle_product_button(product_id, "order")

        # Update the message with new keyboard
        keyboard = create_edit_buttons_keyboard(updated_product)
        await callback.message.edit_reply_markup(reply_markup=keyboard)
        
        status = "enabled" if updated_product.order_enabled else "disabled"
        await callback.answer(f"✅ Order button {status}")
                
    except Exception as e:
        logger.error(f"Error toggling order button: {e}")
        await callback.answer("❌ Error updating button settings", show_alert=True)

@router.callback_query(F.data.startswith("add_custom_"))
async def handle_add_custom_button(callback: CallbackQuery, state: FSMContext):
    """Start custom button creation process"""
    try:
        product_id = int(callback.data.split("_")[-1])
        product = await db.get_product(product_id)
        
        if not product or product.seller_id != callback.from_user.id:
            await callback.answer("❌ Product not found or access denied", show_alert=True)
            return
        
        # Check if there's already a custom button (premium feature)
        if product.custom_button_text and product.custom_button_url:
            await callback.answer("💎 This is a premium feature!", show_alert=True)
            return
        
        await state.set_state(CustomButtonStates.waiting_button_text)
        await state.update_data(product_id=product_id)
        
        await callback.message.answer(
            "📝 **Add Custom Button**\n\n"
            "Please send the text for your custom button:\n"
            "Example: `Visit Website` or `Call Now`",
            reply_markup=create_cancel_keyboard()
        )
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error starting custom button creation: {e}")
        await callback.answer("❌ Error starting button creation", show_alert=True)

@router.callback_query(F.data.startswith("edit_custom_"))
async def handle_edit_custom_button(callback: CallbackQuery, state: FSMContext):
    """Edit existing custom button"""
    try:
        product_id = int(callback.data.split("_")[-1])
        product = await db.get_product(product_id)
        
        if not product or product.seller_id != callback.from_user.id:
            await callback.answer("❌ Product not found or access denied", show_alert=True)
            return
        
        await state.set_state(CustomButtonStates.waiting_button_text)
        await state.update_data(product_id=product_id)
        
        await callback.message.answer(
            "✏️ **Edit Custom Button**\n\n"
            f"Current button: `{product.custom_button_text}`\n"
            f"Current URL: `{product.custom_button_url}`\n\n"
            "Please send the new text for your custom button:",
            reply_markup=create_cancel_keyboard()
        )
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error starting custom button edit: {e}")
        await callback.answer("❌ Error starting button edit", show_alert=True)

@router.callback_query(F.data.startswith("delete_custom_"))
async def handle_delete_custom_button(callback: CallbackQuery):
    """Handle delete custom button callback"""
    try:
        product_id = int(callback.data.split('_')[2])
        user_id = callback.from_user.id
        
        # Verify ownership
        product = await db.get_product(product_id)
        if not product or product.seller_id != user_id:
            try:
                await callback.answer("❌ Product not found or access denied", show_alert=True)
            except:
                pass
            return
        
        # Remove custom button via helper
        updated_product = await set_custom_button(product_id, None, None)
        keyboard = create_edit_buttons_keyboard(updated_product)
        
        # Edit the message with updated keyboard
        try:
            await callback.message.edit_reply_markup(reply_markup=keyboard)
        except:
            pass  # Message might be too old to edit
        
        try:
            await callback.answer("✅ Custom button deleted successfully!", show_alert=True)
        except:
            pass  # Callback might be too old
        logger.info(f"User {user_id} deleted custom button for product {product_id}")
        
    except Exception as e:
        logger.error(f"Error deleting custom button: {e}")
        try:
            await callback.answer("❌ Error deleting custom button", show_alert=True)
        except:
            pass

@router.message(CustomButtonStates.waiting_button_text)
async def handle_custom_button_text(message: Message, state: FSMContext):
    """Handle custom button text input"""
    try:
        button_text = message.text.strip()
        
        if len(button_text) > 100:
            await message.answer("❌ Button text is too long. Maximum 100 characters.")
            return
        
        await state.set_state(CustomButtonStates.waiting_button_url)
        await state.update_data(button_text=button_text)
        
        await message.answer(
            "🔗 **Button URL**\n\n"
            "Now please send the URL for your button:\n"
            "Example: `https://example.com` or `https://t.me/yourchannel`",
            reply_markup=create_cancel_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error handling button text: {e}")
        await message.answer("❌ Error processing button text. Please try again.")
        await state.clear()

@router.message(CustomButtonStates.waiting_button_url)
async def handle_custom_button_url(message: Message, state: FSMContext):
    """Handle custom button URL input"""
    try:
        data = await state.get_data()
        product_id = data['product_id']
        button_text = data['button_text']
        
        url = message.text.strip()
        
        # Basic URL validation
        if not (url.startswith('http://') or url.startswith('https://') or url.startswith('tg://')):
            await message.answer("❌ Invalid URL format. Please include http:// or https://")
            return
        
        # Update custom button in database via helper
        await set_custom_button(product_id, button_text, url)
        
        await state.clear()
        
        await message.answer(
            f"✅ **Custom Button Added Successfully\\!**\n\n"
            f"**Button Text:** {escape_markdown(button_text)}\n"
            f"**Button URL:** {escape_markdown(url)}\n\n"
            f"Use /edit\\_buttons\\_{product_id} to manage your buttons\\.",
            parse_mode="MarkdownV2"
        )
        
        logger.info(f"User {message.from_user.id} added custom button for product {product_id}")
        
    except Exception as e:
        logger.error(f"Error handling button URL: {e}")
        await message.answer("❌ Error processing button URL. Please try again.")
        await state.clear()


