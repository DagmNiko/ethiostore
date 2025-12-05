"""
Django models for Telegram Bot
Converted from SQLAlchemy models
"""
from django.db import models
from django.utils import timezone


class PassthroughJSONField(models.JSONField):
    """
    JSONField that gracefully handles backends which already return native
    Python objects (dict/list) for JSON columns. Prevents double-decoding
    errors like:
        TypeError: the JSON object must be str, bytes or bytearray, not dict
    """

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        if isinstance(value, (dict, list)):
            return value
        return super().from_db_value(value, expression, connection)

    def deconstruct(self):
        """
        Make Django treat this field the same as the built-in JSONField for
        migration purposes (no schema changes required).
        """
        name, path, args, kwargs = super().deconstruct()
        return name, 'django.db.models.JSONField', args, kwargs


class User(models.Model):
    """User model - stores both sellers and buyers"""
    id = models.BigIntegerField(primary_key=True)  # Telegram user ID
    username = models.CharField(max_length=255, null=True, blank=True)
    first_name = models.CharField(max_length=255, null=True, blank=True)
    last_name = models.CharField(max_length=255, null=True, blank=True)
    
    # User type and role
    role = models.CharField(max_length=20, default="buyer")  # seller or buyer
    
    # Seller-specific fields
    store_name = models.CharField(max_length=255, null=True, blank=True)
    phone = models.CharField(max_length=50, null=True, blank=True)
    channel_username = models.CharField(max_length=255, null=True, blank=True)
    
    # Premium status
    is_premium = models.BooleanField(default=False)
    premium_until = models.DateTimeField(null=True, blank=True)
    
    # Registration state (for FSM)
    state = models.CharField(max_length=50, null=True, blank=True)
    state_data = PassthroughJSONField(null=True, blank=True, default=dict)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"User {self.id} - {self.role}: {self.store_name or self.first_name}"
    
    class Meta:
        db_table = 'users'
        ordering = ['-created_at']


class Product(models.Model):
    """Product model - stores product information"""
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='products')
    
    # Product details
    title = models.CharField(max_length=255, null=True, blank=True)  # Optional for custom descriptions
    description = models.TextField(null=True, blank=True)
    price = models.FloatField(null=True, blank=True)  # Optional for custom descriptions
    category = models.CharField(max_length=100, null=True, blank=True)
    
    # Product type
    product_type = models.CharField(max_length=20, default="standard")  # standard, custom_description
    
    # Category-specific fields (stored as JSON)
    category_fields = PassthroughJSONField(null=True, blank=True, default=dict)
    
    # Image storage
    image_path = models.CharField(max_length=500)  # Path to watermarked image
    original_image_path = models.CharField(max_length=500, null=True, blank=True)  # Original without watermark
    
    # Visibility and status
    is_active = models.BooleanField(default=True)
    is_public = models.BooleanField(default=True)  # For inline search
    
    # Engagement counters
    likes_count = models.IntegerField(default=0)
    saves_count = models.IntegerField(default=0)
    orders_count = models.IntegerField(default=0)
    views_count = models.IntegerField(default=0)
    
    # Custom button (optional)
    custom_button_text = models.CharField(max_length=100, null=True, blank=True)
    custom_button_url = models.CharField(max_length=500, null=True, blank=True)
    
    # Button settings
    like_enabled = models.BooleanField(default=True)
    save_enabled = models.BooleanField(default=True)
    order_enabled = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Product {self.id}: {self.title} - {self.price} birr"
    
    class Meta:
        db_table = 'products'
        ordering = ['-created_at']


class Engagement(models.Model):
    """Track user engagement (likes, saves) with products"""
    user_id = models.BigIntegerField()  # User who engaged
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='engagements')
    
    # Engagement type
    liked = models.BooleanField(default=False)
    saved = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Engagement user={self.user_id} product={self.product_id}"
    
    class Meta:
        db_table = 'engagements'
        unique_together = ['user_id', 'product']
        ordering = ['-created_at']


class Order(models.Model):
    """Order model - stores order information"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_orders')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='orders')
    
    # Order details
    quantity = models.IntegerField(default=1)
    buyer_phone = models.CharField(max_length=50, null=True, blank=True)
    buyer_location = models.TextField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    
    # Order status
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default="pending")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Order {self.id}: {self.quantity}x Product {self.product_id}"
    
    class Meta:
        db_table = 'orders'
        ordering = ['-created_at']


class PostSchedule(models.Model):
    """Schedule model - stores auto-posting schedules"""
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='schedules')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='schedules')
    
    # Schedule settings
    channel_username = models.CharField(max_length=255)
    interval_days = models.IntegerField(default=2)  # Repost every X days
    post_time = models.CharField(max_length=10, default="09:00")  # Time in HH:MM format
    
    # Status
    is_active = models.BooleanField(default=True)
    last_posted_at = models.DateTimeField(null=True, blank=True)
    next_post_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Schedule {self.id}: Product {self.product_id} every {self.interval_days} days"
    
    class Meta:
        db_table = 'schedules'
        ordering = ['-created_at']


class ChannelPost(models.Model):
    """Track channel posts per product so we can edit them later"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='channel_posts')
    channel_username = models.CharField(max_length=255)
    message_id = models.IntegerField()
    posted_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"ChannelPost product={self.product_id} channel={self.channel_username} message_id={self.message_id}"
    
    class Meta:
        db_table = 'channel_posts'
        ordering = ['-posted_at']

