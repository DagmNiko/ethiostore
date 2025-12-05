"""
Inline search feature
Allows users to search and share products using inline mode
"""
from aiogram import Router
from aiogram.types import InlineQuery, InlineQueryResultPhoto, InlineQueryResultArticle, InputTextMessageContent
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database.db import db
from utils.helpers import format_price, create_product_keyboard, truncate_text, escape_markdown
from utils.logger import logger

router = Router()

@router.inline_query()
async def inline_search(inline_query: InlineQuery):
    """
    Handle inline queries for product search
    Usage: @ethiostorebot <search term>
    """
    query = inline_query.query.strip()
    user_id = inline_query.from_user.id
    
    # Log inline query
    logger.info(f"Inline query from {user_id}: '{query}'")
    
    # If query is empty, show popular/recent products
    if not query or len(query) < 2:
        # Get recent products (limit 20) using Django ORM
        from telegram_bot.models import Product
        
        products = list(Product.objects.filter(
            is_public=True,
            is_active=True
        ).order_by('-created_at')[:20])
    else:
        # Search products
        products = await db.search_products(query, limit=50)
    
    if not products:
        # No results found
        await inline_query.answer(
            results=[],
            switch_pm_text="No products found. Try different keywords.",
            switch_pm_parameter="search",
            cache_time=10
        )
        return
    
    # Build results
    results = []
    
    for product in products:
        # Get seller info
        seller = await db.get_user(product.seller_id)
        
        # Create caption
        caption = (
            f"🛍️ **{product.title}**\n\n"
            f"{truncate_text(product.description or '', 150)}\n\n"
            f"💰 **Price:** {format_price(product.price)}\n"
            f"🏪 **Seller:** {seller.store_name}\n"
        )
        
        if product.category:
            caption += f"📁 **Category:** {product.category}\n"
        
        # Add engagement stats if any
        if product.likes_count > 0 or product.saves_count > 0:
            stats = []
            if product.likes_count > 0:
                stats.append(f"❤️ {product.likes_count}")
            if product.saves_count > 0:
                stats.append(f"💾 {product.saves_count}")
            if product.orders_count > 0:
                stats.append(f"🛒 {product.orders_count}")
            
            caption += f"\n📊 {' • '.join(stats)}"
        
        # Create inline keyboard
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
        
        # Create result - using text result since we can't use file:// URLs for inline queries
        result = InlineQueryResultArticle(
            id=str(product.id),
            title=f"🛍️ {product.title}",
            description=f"{format_price(product.price)} - {seller.store_name}",
            input_message_content=InputTextMessageContent(
                message_text=f"🛍️ **{escape_markdown(product.title)}**\n\n{escape_markdown(product.description)}\n\n💰 **Price:** {escape_markdown(format_price(product.price))}\n\n🏪 **Seller:** {escape_markdown(seller.store_name)}\n\nUse /view\\_{product.id} to see full product details with image\\.",
                parse_mode="MarkdownV2"
            ),
            reply_markup=keyboard
        )
        
        results.append(result)
    
    # Answer inline query
    await inline_query.answer(
        results=results,
        cache_time=30,  # Cache for 30 seconds
        is_personal=False  # Results are the same for everyone
    )
    
    logger.info(f"Inline query answered with {len(results)} results")

# Note: For production, you'll need to serve images via a web server
# and use actual HTTP URLs instead of file:// URLs
# You can use a simple HTTP server or upload images to a CDN


