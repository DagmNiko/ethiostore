"""
Helper utilities for the bot
Common functions used across features
"""
from datetime import datetime, timedelta
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import Optional

def format_price(price: float) -> str:
    """Format price with currency"""
    return f"{price:,.2f} Birr"

def format_datetime(dt: datetime) -> str:
    """Format datetime for display"""
    return dt.strftime("%B %d, %Y at %I:%M %p")

def format_relative_time(dt: datetime) -> str:
    """Format datetime as relative time (e.g., '2 hours ago')"""
    now = datetime.now()
    diff = now - dt
    
    if diff.days > 365:
        years = diff.days // 365
        return f"{years} year{'s' if years > 1 else ''} ago"
    elif diff.days > 30:
        months = diff.days // 30
        return f"{months} month{'s' if months > 1 else ''} ago"
    elif diff.days > 0:
        return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    else:
        return "just now"

def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to max length with ellipsis"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."

def create_product_keyboard(product_id: int, seller_phone: Optional[str] = None,
                           custom_button: Optional[tuple] = None,
                           show_admin_buttons: bool = False,
                           show_post_button: bool = False,
                           likes_count: int = 0, saves_count: int = 0,
                           like_enabled: bool = True, save_enabled: bool = True, 
                           order_enabled: bool = True) -> InlineKeyboardMarkup:
    """
    Create engagement keyboard for product posts
    
    Args:
        product_id: Product ID
        seller_phone: Seller phone number
        custom_button: Optional tuple of (text, url)
        show_admin_buttons: Whether to show admin/edit buttons
        show_post_button: Whether to show "Post to Channel" button
        likes_count: Number of likes
        saves_count: Number of saves
        like_enabled: Whether like button is enabled
        save_enabled: Whether save button is enabled
        order_enabled: Whether order button is enabled
    
    Returns:
        InlineKeyboardMarkup
    """
    buttons = []
    
    # First row: Like and Save with counts (only if enabled)
    if like_enabled or save_enabled:
        row1 = []
        if like_enabled:
            row1.append(InlineKeyboardButton(text=f"❤️ Like - {likes_count}", callback_data=f"like_{product_id}"))
        if save_enabled:
            row1.append(InlineKeyboardButton(text=f"💾 Save - {saves_count}", callback_data=f"save_{product_id}"))
        if row1:  # Only add row if there are buttons
            buttons.append(row1)
    
    # Second row: Order (only if enabled)
    if order_enabled:
        row2 = [
            InlineKeyboardButton(text="🛒 Order", callback_data=f"order_{product_id}")
        ]
        buttons.append(row2)
    
    # Third row: Custom button (if provided)
    if custom_button:
        custom_text, custom_url = custom_button
        buttons.append([
            InlineKeyboardButton(text=f"⚙️ {custom_text}", url=custom_url)
        ])
    
    # Post to Channel button (for sellers)
    if show_post_button:
        buttons.append([
            InlineKeyboardButton(text="📢 Post to Channel", callback_data=f"post_channel_{product_id}")
        ])
    
    # Admin buttons (if enabled)
    if show_admin_buttons:
        buttons.append([
            InlineKeyboardButton(text="📊 Stats", callback_data=f"stats_{product_id}"),
            InlineKeyboardButton(text="✏️ Edit", callback_data=f"edit_{product_id}")
        ])
        # Add mark sold for owners in admin row below
        buttons.append([
            InlineKeyboardButton(text="✅ Mark Sold", callback_data=f"mark_sold_{product_id}")
        ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def create_pagination_keyboard(current_page: int, total_pages: int, 
                              callback_prefix: str) -> InlineKeyboardMarkup:
    """Create pagination keyboard"""
    buttons = []
    
    if total_pages > 1:
        row = []
        
        if current_page > 1:
            row.append(InlineKeyboardButton(
                text="◀️ Previous",
                callback_data=f"{callback_prefix}_page_{current_page-1}"
            ))
        
        row.append(InlineKeyboardButton(
            text=f"📄 {current_page}/{total_pages}",
            callback_data="noop"
        ))
        
        if current_page < total_pages:
            row.append(InlineKeyboardButton(
                text="Next ▶️",
                callback_data=f"{callback_prefix}_page_{current_page+1}"
            ))
        
        buttons.append(row)
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def create_product_carousel_keyboard(product_id: int, current_index: int, total_count: int,
                                     seller_phone: Optional[str] = None,
                                     custom_button: Optional[tuple] = None,
                                     show_admin_buttons: bool = False,
                                     show_post_button: bool = False,
                                     likes_count: int = 0, saves_count: int = 0,
                                     like_enabled: bool = True, save_enabled: bool = True, 
                                     order_enabled: bool = True) -> InlineKeyboardMarkup:
    """
    Create product keyboard with carousel navigation
    
    Args:
        product_id: Product ID
        current_index: Current product index (0-based)
        total_count: Total number of products
        seller_phone: Optional seller phone
        custom_button: Optional tuple of (text, url)
        show_admin_buttons: Show admin buttons
        show_post_button: Show post to channel button
        likes_count: Number of likes
        saves_count: Number of saves
        like_enabled: Whether like button is enabled
        save_enabled: Whether save button is enabled
        order_enabled: Whether order button is enabled
    
    Returns:
        InlineKeyboardMarkup with product buttons and navigation
    """
    buttons = []
    
    # Engagement buttons row (only if enabled)
    if like_enabled or save_enabled:
        row1 = []
        if like_enabled:
            row1.append(InlineKeyboardButton(text=f"❤️ Like - {likes_count}", callback_data=f"like_{product_id}"))
        if save_enabled:
            row1.append(InlineKeyboardButton(text=f"💾 Save - {saves_count}", callback_data=f"save_{product_id}"))
        if row1:  # Only add row if there are buttons
            buttons.append(row1)
    
    # Order button row (only if enabled)
    if order_enabled:
        row2 = [
            InlineKeyboardButton(text="🛒 Order", callback_data=f"order_{product_id}")
        ]
        buttons.append(row2)
    
    # Custom button (if provided)
    if custom_button:
        custom_text, custom_url = custom_button
        buttons.append([
            InlineKeyboardButton(text=f"⚙️ {custom_text}", url=custom_url)
        ])
    
    # Post to Channel button (for sellers)
    if show_post_button:
        buttons.append([
            InlineKeyboardButton(text="📢 Post to Channel", callback_data=f"post_channel_{product_id}")
        ])
    
    # Admin buttons (if enabled)
    if show_admin_buttons:
        buttons.append([
            InlineKeyboardButton(text="📊 Stats", callback_data=f"stats_{product_id}"),
            InlineKeyboardButton(text="✏️ Edit", callback_data=f"edit_{product_id}")
        ])
    
    # Navigation buttons (if multiple products)
    if total_count > 1:
        nav_row = []
        
        if current_index > 0:
            nav_row.append(InlineKeyboardButton(
                text="◀️ Previous",
                callback_data=f"myproducts_nav_{current_index - 1}"
            ))
        
        nav_row.append(InlineKeyboardButton(
            text=f"📦 {current_index + 1}/{total_count}",
            callback_data="noop"
        ))
        
        if current_index < total_count - 1:
            nav_row.append(InlineKeyboardButton(
                text="Next ▶️",
                callback_data=f"myproducts_nav_{current_index + 1}"
            ))
        
        buttons.append(nav_row)
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def calculate_next_post_time(interval_days: int, post_time_str: str) -> datetime:
    """
    Calculate next posting time based on interval and time
    
    Args:
        interval_days: Number of days between posts
        post_time_str: Time in HH:MM format
    
    Returns:
        Next post datetime
    """
    now = datetime.now()
    
    # Parse time
    try:
        hour, minute = map(int, post_time_str.split(':'))
    except:
        hour, minute = 9, 0  # Default to 9:00 AM
    
    # Calculate next post time
    next_post = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    # If time has passed today, start from tomorrow
    if next_post <= now:
        next_post += timedelta(days=1)
    
    # Add interval
    next_post += timedelta(days=interval_days)
    
    return next_post

def validate_phone(phone: str) -> bool:
    """Basic phone number validation"""
    # Remove common separators
    cleaned = phone.replace('-', '').replace(' ', '').replace('(', '').replace(')', '')
    
    # Check if it's mostly digits and has reasonable length
    return cleaned.replace('+', '').isdigit() and 7 <= len(cleaned) <= 15

def format_product_caption(title: Optional[str], description: Optional[str], price: Optional[float],
                          category: Optional[str] = None,
                          engagement_stats: Optional[dict] = None,
                          seller_name: Optional[str] = None,
                          seller_phone: Optional[str] = None,
                          product_type: str = "standard",
                          category_fields: Optional[dict] = None,
                          for_channel: bool = False) -> str:
    """
    Format product caption for Telegram posts
    
    Args:
        title: Product title (optional for custom descriptions)
        description: Product description
        price: Product price (optional for custom descriptions)
        category: Optional category
        engagement_stats: Optional dict with likes_count, saves_count, orders_count
        seller_name: Optional seller/store name
        seller_phone: Optional seller phone number
        product_type: Type of product (standard or custom_description)
        category_fields: Optional dict with category-specific fields
        for_channel: Whether this is for channel posting (custom descriptions show only description)
    
    Returns:
        Formatted caption string
    """
    if product_type == "custom_description":
        if for_channel:
            # For channel posts, custom descriptions show ONLY the description text
            caption = f"{escape_markdown(description)}"
        else:
            # For regular viewing, show title, price, and description
            if title:
                caption = f"🛍️ **{escape_markdown(title)}**\n"
                caption += "━━━━━━━━━━━━━━━━━━━━\n\n"
            else:
                caption = ""
            
            if price:
                caption += f"💰 **{escape_markdown(format_price(price))}**\n\n"
            
            caption += f"{escape_markdown(description)}"
            
            # Add seller info at the end
            if seller_name or seller_phone:
                caption += "\n\n"
                if seller_name:
                    caption += f"👤 **{escape_markdown(seller_name)}**\n"
                if seller_phone:
                    caption += f"📞 {escape_markdown(seller_phone)}\n"
        
        return caption
    
    # Standard product format
    # Main product title with nice formatting
    caption = f"🛍️ **{escape_markdown(title)}**\n"
    caption += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # Description without label - just the content
    if description:
        caption += f"{escape_markdown(description)}\n\n"
    
    # Add category-specific fields
    if category_fields:
        for field, value in category_fields.items():
            # Clean up field labels
            field_label = field.replace("_", " ").title()
            caption += f"• **{field_label}**: {escape_markdown(value)}\n"
        caption += "\n"
    
    # Price with prominent formatting
    if price:
        caption += f"💰 **{escape_markdown(format_price(price))}**\n"
    
    # Category with nice icon
    if category:
        caption += f"📂 {escape_markdown(category)}\n"
    
    # Seller information with clean layout
    if seller_name or seller_phone:
        caption += "\n"
        if seller_name:
            caption += f"👤 **{escape_markdown(seller_name)}**\n"
        if seller_phone:
            caption += f"📞 {escape_markdown(seller_phone)}\n"
    
    return caption

def escape_markdown(text: str) -> str:
    """Escape markdown special characters"""
    if text is None:
        return ""
    # We only escape core MarkdownV2 control characters.
    # Normal punctuation like hyphens, dots and parentheses are left as-is
    # so user-entered descriptions don't get cluttered with backslashes.
    special_chars = ['_', '*', '[', ']', '~', '`', '>', '#', '+', '=', '|', '{', '}', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text

def create_cancel_keyboard() -> InlineKeyboardMarkup:
    """Create a cancel button keyboard for FSM states"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_fsm")]
    ])


