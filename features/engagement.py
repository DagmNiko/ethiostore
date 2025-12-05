"""
Engagement feature
Handles user interactions with products (likes, saves, orders)
"""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database.db import db
from utils.helpers import format_price, create_product_keyboard, format_product_caption
from utils.logger import logger

router = Router()

# FSM States for order process (not used anymore - simplified to immediate orders)
class OrderStates(StatesGroup):
    waiting_quantity = State()  # Keep for compatibility but not used
    waiting_phone = State()     # Keep for compatibility but not used  
    waiting_location = State()  # Keep for compatibility but not used
    confirming = State()        # Keep for compatibility but not used

@router.callback_query(F.data.startswith("like_"))
async def handle_like(callback: CallbackQuery):
    """Handle product like button"""
    try:
        product_id = int(callback.data.split('_')[1])
        user_id = callback.from_user.id
        
        # Toggle like
        is_liked, product = await db.toggle_like(user_id, product_id)
        
        # Get seller info
        seller = await db.get_user(product.seller_id)
        
        # Update keyboard to reflect new state
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
        
        # Update message
        try:
            await callback.message.edit_reply_markup(reply_markup=keyboard)
        except:
            pass  # Message might be too old to edit
        
        # Show feedback
        if is_liked:
            await callback.answer("❤️ Liked!", show_alert=False)
        else:
            await callback.answer("💔 Like removed", show_alert=False)
        
        logger.info(f"User {user_id} {'liked' if is_liked else 'unliked'} product {product_id}")
        
    except Exception as e:
        logger.error(f"Error handling like: {e}")
        await callback.answer("❌ Error processing like", show_alert=True)

@router.callback_query(F.data.startswith("save_"))
async def handle_save(callback: CallbackQuery):
    """Handle product save button"""
    try:
        product_id = int(callback.data.split('_')[1])
        user_id = callback.from_user.id
        
        # Toggle save
        is_saved, product = await db.toggle_save(user_id, product_id)
        
        # Get seller info
        seller = await db.get_user(product.seller_id)
        
        # Update keyboard
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
        
        # Update message
        try:
            await callback.message.edit_reply_markup(reply_markup=keyboard)
        except:
            pass
        
        # Show feedback
        if is_saved:
            await callback.answer("💾 Saved for later!", show_alert=False)
        else:
            await callback.answer("🗑️ Removed from saved", show_alert=False)
        
        logger.info(f"User {user_id} {'saved' if is_saved else 'unsaved'} product {product_id}")
        
    except Exception as e:
        logger.error(f"Error handling save: {e}")
        await callback.answer("❌ Error processing save", show_alert=True)

@router.callback_query(F.data.startswith("order_"))
async def handle_order_start(callback: CallbackQuery):
    """Process order immediately - confirm to buyer and notify seller"""
    try:
        product_id = int(callback.data.split('_')[1])
        user_id = callback.from_user.id
        
        # Get product and seller
        product = await db.get_product(product_id)
        seller = await db.get_user(product.seller_id)
        
        if not product or not product.is_active:
            await callback.answer("❌ This product is no longer available", show_alert=True)
            return
        
        # Check if user exists, if not create as buyer
        user = await db.get_user(user_id)
        if not user:
            user = await db.create_user(
                user_id=user_id,
                username=callback.from_user.username,
                first_name=callback.from_user.first_name,
                last_name=callback.from_user.last_name,
                role="buyer"
            )
        
        # Create order record
        order = await db.create_order(
            product_id=product_id,
            seller_id=seller.id,
            buyer_id=user_id,
            quantity=1,  # Default quantity of 1
            status='pending'
        )
        
        # Escape markdown in product title and store name
        from utils.helpers import escape_markdown, format_price
        safe_title = escape_markdown(product.title)
        safe_store_name = escape_markdown(seller.store_name)
        safe_price = escape_markdown(format_price(product.price))
        
        # Check if this is a channel callback (from channel post)
        is_channel = callback.message.chat.type in ['channel', 'group']
        
        # Try to answer callback first (but don't fail if it's too old)
        try:
            await callback.answer("✅ Order confirmed!", show_alert=True)
        except Exception:
            pass  # Ignore callback answer errors (query too old, etc.)
        
        # Send confirmation to buyer
        buyer_message = (
            f"✅ **Order Confirmed\\!**\n\n"
            f"🛒 **Product:** {safe_title}\n"
            f"💰 **Price:** {safe_price}\n"
            f"🏪 **Seller:** {safe_store_name}\n"
            f"📦 **Quantity:** 1\n\n"
            f"The seller will contact you soon with delivery details\\!"
        )
        
        if is_channel:
            # If from channel, send confirmation to user's private chat
            try:
                await callback.bot.send_message(
                    chat_id=user_id,
                    text=buyer_message,
                    parse_mode="MarkdownV2"
                )
            except Exception:
                # If can't send to private chat, fall back to channel
                await callback.message.answer(buyer_message, parse_mode="MarkdownV2")
        else:
            # If already in private chat, respond normally
            await callback.message.answer(buyer_message, parse_mode="MarkdownV2")
        
        # Notify seller about the order
        seller_message = (
            f"🛒 **New Order Received\\!**\n\n"
            f"📦 **Product:** {safe_title}\n"
            f"💰 **Price:** {safe_price}\n"
            f"📦 **Quantity:** 1\n\n"
            f"👤 **Customer Details:**\n"
            f"• Name: {escape_markdown(user.first_name or 'Unknown')}\n"
            f"• Username: @{escape_markdown(user.username or 'no_username')}\n"
            f"• Telegram ID: `{user_id}`\n\n"
            f"📞 **Contact the buyer to arrange delivery\\!**"
        )
        
        try:
            await callback.bot.send_message(
                chat_id=seller.id,
                text=seller_message,
                parse_mode="MarkdownV2"
            )
        except Exception as e:
            logger.error(f"Failed to notify seller {seller.id} about order: {e}")
        
        # Update product engagement stats
        await db.update_product_engagement(product_id, orders_count=1)
        
        logger.info(f"Order {order.id} created: User {user_id} ordered product {product_id} from seller {seller.id}")
        
    except Exception as e:
        logger.error(f"Error processing order: {e}")
        try:
            await callback.answer("❌ Error processing order", show_alert=True)
        except Exception:
            pass  # Ignore callback answer errors

@router.message(OrderStates.waiting_quantity)
async def order_quantity_received(message: Message, state: FSMContext):
    """Receive order quantity"""
    try:
        quantity = int(message.text.strip())
        
        if quantity <= 0:
            await message.answer("❌ Quantity must be greater than 0. Please try again:")
            return
        
        if quantity > 1000:
            await message.answer("❌ Quantity seems too high. Please check and try again:")
            return
        
    except ValueError:
        await message.answer("❌ Please enter a valid number (e.g., 1, 2, 3):")
        return
    
    await state.update_data(quantity=quantity)
    
    # Get product to show total
    data = await state.get_data()
    product = await db.get_product(data['product_id'])
    total = product.price * quantity
    
    await message.answer(
        f"✅ Quantity: {quantity}\n"
        f"💰 Total: {format_price(total)}\n\n"
        "Please share your **phone number** so the seller can contact you.\n"
        "(You can type it or use the button below)",
        reply_markup={
            "keyboard": [[{"text": "📱 Share Phone", "request_contact": True}]],
            "resize_keyboard": True,
            "one_time_keyboard": True
        }
    )
    
    await state.set_state(OrderStates.waiting_phone)

@router.message(OrderStates.waiting_phone, F.contact)
async def order_phone_contact_received(message: Message, state: FSMContext):
    """Receive phone via contact share"""
    phone = message.contact.phone_number
    await state.update_data(phone=phone)
    
    await message.answer(
        f"✅ Phone: {phone}\n\n"
        "Optional: Share your **location** or delivery address?\n\n"
        "You can:\n"
        "• Type your address\n"
        "• Share location using 📍 button\n"
        "• Type 'skip' to skip",
        reply_markup={"remove_keyboard": True}
    )
    
    await state.set_state(OrderStates.waiting_location)

@router.message(OrderStates.waiting_phone)
async def order_phone_text_received(message: Message, state: FSMContext):
    """Receive phone as text"""
    phone = message.text.strip()
    
    if len(phone) < 7:
        await message.answer("❌ Please enter a valid phone number:")
        return
    
    await state.update_data(phone=phone)
    
    await message.answer(
        f"✅ Phone: {phone}\n\n"
        "Optional: Share your **location** or delivery address?\n\n"
        "You can:\n"
        "• Type your address\n"
        "• Share location using 📍 button\n"
        "• Type 'skip' to skip",
        reply_markup={"remove_keyboard": True}
    )
    
    await state.set_state(OrderStates.waiting_location)

@router.message(OrderStates.waiting_location, F.location)
async def order_location_received(message: Message, state: FSMContext):
    """Receive location"""
    location = f"Lat: {message.location.latitude}, Lon: {message.location.longitude}"
    await state.update_data(location=location)
    await finalize_order(message, state)

@router.message(OrderStates.waiting_location)
async def order_location_text_received(message: Message, state: FSMContext):
    """Receive location as text"""
    location = message.text.strip()
    
    if location.lower() != 'skip':
        await state.update_data(location=location)
    else:
        await state.update_data(location=None)
    
    await finalize_order(message, state)

async def finalize_order(message: Message, state: FSMContext):
    """Finalize and save order"""
    data = await state.get_data()
    
    # Get product and seller
    product = await db.get_product(data['product_id'])
    seller = await db.get_user(data['seller_id'])
    
    # Create order
    order = await db.create_order(
        buyer_id=message.from_user.id,
        seller_id=seller.id,
        product_id=product.id,
        quantity=data['quantity'],
        buyer_phone=data['phone'],
        buyer_location=data.get('location')
    )
    
    # Calculate total
    total = product.price * data['quantity']
    
    # Send confirmation to buyer
    buyer_message = (
        "✅ **Order Placed Successfully!**\n\n"
        f"📦 Product: {product.title}\n"
        f"🔢 Quantity: {data['quantity']}\n"
        f"💰 Total: {format_price(total)}\n"
        f"📱 Your phone: {data['phone']}\n"
    )
    
    if data.get('location'):
        buyer_message += f"📍 Location: {data['location']}\n"
    
    buyer_message += (
        f"\n🏪 **Seller:** {seller.store_name}\n"
        f"📞 Contact: {seller.phone}\n\n"
        "The seller will contact you shortly to confirm the order.\n"
        "Order ID: #{order.id}"
    )
    
    await message.answer(buyer_message)
    
    # Notify seller
    seller_message = (
        "🔔 **New Order Received!**\n\n"
        f"📦 Product: {product.title}\n"
        f"🔢 Quantity: {data['quantity']}\n"
        f"💰 Total: {format_price(total)}\n\n"
        f"👤 **Buyer:** {message.from_user.first_name or 'Customer'}\n"
    )
    
    if message.from_user.username:
        seller_message += f"📱 Telegram: @{message.from_user.username}\n"
    
    seller_message += f"📞 Phone: {data['phone']}\n"
    
    if data.get('location'):
        seller_message += f"📍 Location: {data['location']}\n"
    
    seller_message += f"\nOrder ID: #{order.id}"
    
    try:
        await message.bot.send_message(
            chat_id=seller.id,
            text=seller_message
        )
    except Exception as e:
        logger.error(f"Failed to notify seller {seller.id}: {e}")
    
    await state.clear()
    logger.info(f"Order {order.id} created successfully")

@router.message(Command("saved"))
async def cmd_saved_products(message: Message):
    """Show user's saved products"""
    user_id = message.from_user.id
    
    # Get saved products using Django ORM
    from telegram_bot.models import Product, Engagement
    
    saved_products = list(Product.objects.filter(
        engagements__user_id=user_id,
        engagements__saved=True,
        is_active=True
    ).order_by('-engagements__updated_at').distinct())
    
    if not saved_products:
        await message.answer(
            "💾 **No saved products yet!**\n\n"
            "Browse products and click the 💾 Save button to save them for later."
        )
        return
    
    await message.answer(
        f"💾 **Your Saved Products** ({len(saved_products)})\n\n"
        "Here are your saved items:"
    )
    
    # Send each saved product
    for product in saved_products[:10]:  # Limit to 10
        seller = await db.get_user(product.seller_id)
        
        caption = format_product_caption(
            title=product.title,
            description=product.description,
            price=product.price,
            category=product.category
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
        
        try:
            from aiogram.types import FSInputFile
            photo = FSInputFile(product.image_path)
            await message.answer_photo(
                photo=photo,
                caption=caption,
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Error sending saved product {product.id}: {e}")
    
    if len(saved_products) > 10:
        await message.answer(f"... and {len(saved_products) - 10} more saved items")

@router.message(Command("browse"))
async def cmd_browse_products(message: Message):
    """Browse latest products"""
    from telegram_bot.models import Product
    
    products = list(Product.objects.filter(
        is_public=True,
        is_active=True
    ).order_by('-created_at')[:10])
    
    if not products:
        await message.answer("📦 No products available yet.")
        return
    
    await message.answer("🛍️ **Latest Products:**\n\nBrowsing top 10 products...")
    
    for product in products:
        seller = await db.get_user(product.seller_id)
        
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
        
        try:
            from aiogram.types import FSInputFile
            photo = FSInputFile(product.image_path)
            await message.answer_photo(
                photo=photo,
                caption=caption,
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Error sending product {product.id}: {e}")

@router.message(Command("buyers"))
async def cmd_view_buyers(message: Message):
    """View customers who ordered from this seller"""
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    
    if not user or user.role != "seller":
        await message.answer("❌ This command is only for sellers.")
        return
    
    buyers = await db.get_seller_buyers(user_id)
    
    if not buyers:
        await message.answer(
            "👥 **No customers yet!**\n\n"
            "Once someone places an order, they'll appear here."
        )
        return
    
    response = f"👥 **Your Customers** ({len(buyers)} total)\n\n"
    
    for i, buyer in enumerate(buyers[:20], 1):
        # Escape markdown special characters
        name = (buyer.first_name or "Customer").replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace('`', '\\`')
        if buyer.username:
            # Escape username separately (can't use backslash in f-string)
            safe_username = buyer.username.replace('_', '\\_')
            username = f"@{safe_username}"
        else:
            username = "No username"
        phone = buyer.phone or "No phone"
        
        response += f"{i}\\. {name}\n   {username} • {phone}\n\n"
    
    if len(buyers) > 20:
        response += f"\\.\\.\\. and {len(buyers) - 20} more customers"
    
    await message.answer(response)


