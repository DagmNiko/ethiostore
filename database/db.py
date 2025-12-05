"""
Database connection and operations using Django ORM
Replaces SQLAlchemy with Django ORM
"""
from datetime import datetime
from typing import Optional
from asgiref.sync import sync_to_async
from django.db import transaction
from telegram_bot.models import User, Product, Engagement, Order, PostSchedule, ChannelPost


async def init_db():
    """Initialize database - Django migrations handle this"""
    # Django migrations handle table creation
    pass


# Database helper functions using Django ORM
class Database:
    """Database operations helper class using Django ORM"""
    
    @staticmethod
    @sync_to_async
    def get_user(user_id: int) -> Optional[User]:
        """Get user by Telegram ID"""
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None
    
    @staticmethod
    @sync_to_async
    def create_user(user_id: int, username: str = None, first_name: str = None, 
                   last_name: str = None, role: str = "buyer") -> User:
        """Create new user"""
        user, created = User.objects.get_or_create(
            id=user_id,
            defaults={
                'username': username,
                'first_name': first_name,
                'last_name': last_name,
                'role': role
            }
        )
        if not created:
            # Update existing user
            if username:
                user.username = username
            if first_name:
                user.first_name = first_name
            if last_name:
                user.last_name = last_name
            user.save()
        return user
    
    @staticmethod
    @sync_to_async
    def update_user(user_id: int, **kwargs) -> Optional[User]:
        """Update user fields"""
        try:
            user = User.objects.get(id=user_id)
            for key, value in kwargs.items():
                setattr(user, key, value)
            user.save()
            return user
        except User.DoesNotExist:
            return None
    
    @staticmethod
    @sync_to_async
    def get_product(product_id: int) -> Optional[Product]:
        """Get product by ID"""
        try:
            return Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return None
    
    @staticmethod
    @sync_to_async
    def get_seller_products(seller_id: int, active_only: bool = True) -> list[Product]:
        """Get all products for a seller"""
        queryset = Product.objects.filter(seller_id=seller_id)
        if active_only:
            queryset = queryset.filter(is_active=True)
        return list(queryset.order_by('-created_at'))
    
    @staticmethod
    @sync_to_async
    def create_product(seller_id: int, title: str, price: float, image_path: str,
                      description: str = None, category: str = None, **kwargs) -> Product:
        """Create new product"""
        seller = User.objects.get(id=seller_id)
        product = Product(
            seller=seller,
            title=title,
            description=description,
            price=price,
            category=category,
            image_path=image_path,
            **kwargs
        )
        product.save()
        return product
    
    @staticmethod
    @sync_to_async
    def search_products(query: str, limit: int = 20) -> list[Product]:
        """Search public products by title or description"""
        from django.db.models import Q
        queryset = Product.objects.filter(
            is_public=True,
            is_active=True
        ).filter(
            Q(title__icontains=query) | Q(description__icontains=query)
        ).order_by('-created_at')[:limit]
        return list(queryset)
    
    @staticmethod
    @sync_to_async
    def get_or_create_engagement(user_id: int, product_id: int) -> Engagement:
        """Get or create engagement record"""
        engagement, created = Engagement.objects.get_or_create(
            user_id=user_id,
            product_id=product_id
        )
        return engagement
    
    @staticmethod
    @sync_to_async
    def toggle_like(user_id: int, product_id: int) -> tuple[bool, Product]:
        """Toggle like on a product and update counter"""
        with transaction.atomic():
            engagement, _ = Engagement.objects.get_or_create(
                user_id=user_id,
                product_id=product_id
            )
            
            # Toggle like
            was_liked = engagement.liked
            engagement.liked = not engagement.liked
            engagement.save()
            
            # Update counter
            product = Product.objects.select_for_update().get(id=product_id)
            if engagement.liked:
                product.likes_count += 1
            else:
                product.likes_count = max(0, product.likes_count - 1)
            product.save()
            
            return engagement.liked, product
    
    @staticmethod
    @sync_to_async
    def toggle_save(user_id: int, product_id: int) -> tuple[bool, Product]:
        """Toggle save on a product and update counter"""
        with transaction.atomic():
            engagement, _ = Engagement.objects.get_or_create(
                user_id=user_id,
                product_id=product_id
            )
            
            # Toggle save
            engagement.saved = not engagement.saved
            engagement.save()
            
            # Update counter
            product = Product.objects.select_for_update().get(id=product_id)
            if engagement.saved:
                product.saves_count += 1
            else:
                product.saves_count = max(0, product.saves_count - 1)
            product.save()
            
            return engagement.saved, product
    
    @staticmethod
    @sync_to_async
    def create_order(buyer_id: int, seller_id: int, product_id: int, 
                    quantity: int = 1, **kwargs) -> Order:
        """Create new order"""
        with transaction.atomic():
            buyer = User.objects.get(id=buyer_id)
            seller = User.objects.get(id=seller_id)
            product = Product.objects.select_for_update().get(id=product_id)
            
            order = Order(
                buyer=buyer,
                seller=seller,
                product=product,
                quantity=quantity,
                **kwargs
            )
            order.save()
            
            # Update product order count
            product.orders_count += 1
            product.save()
            
            return order
    
    @staticmethod
    @sync_to_async
    def update_product_engagement(product_id: int, **kwargs) -> None:
        """Update product engagement counters"""
        try:
            product = Product.objects.get(id=product_id)
            for key, value in kwargs.items():
                if hasattr(product, key):
                    setattr(product, key, getattr(product, key) + value)
            product.save()
        except Product.DoesNotExist:
            pass

    @staticmethod
    @sync_to_async
    def record_channel_post(product_id: int, channel_username: str, message_id: int) -> None:
        """Record a channel post message id for later bulk edits."""
        product = Product.objects.get(id=product_id)
        ChannelPost.objects.create(
            product=product,
            channel_username=channel_username,
            message_id=message_id
        )

    @staticmethod
    @sync_to_async
    def get_channel_posts(product_id: int) -> list[ChannelPost]:
        """Get channel posts for a product"""
        return list(ChannelPost.objects.filter(product_id=product_id))
    
    @staticmethod
    @sync_to_async
    def get_seller_buyers(seller_id: int) -> list[User]:
        """Get all buyers who ordered from this seller"""
        buyer_ids = Order.objects.filter(seller_id=seller_id).values_list('buyer_id', flat=True).distinct()
        return list(User.objects.filter(id__in=buyer_ids))
    
    @staticmethod
    @sync_to_async
    def create_schedule(seller_id: int, product_id: int, channel_username: str,
                      interval_days: int = 2, post_time: str = "09:00") -> PostSchedule:
        """Create posting schedule"""
        seller = User.objects.get(id=seller_id)
        product = Product.objects.get(id=product_id)
        schedule = PostSchedule(
            seller=seller,
            product=product,
            channel_username=channel_username,
            interval_days=interval_days,
            post_time=post_time
        )
        schedule.save()
        return schedule
    
    @staticmethod
    @sync_to_async
    def get_active_schedules() -> list[PostSchedule]:
        """Get all active schedules"""
        return list(PostSchedule.objects.filter(is_active=True).order_by('next_post_at'))
    
    @staticmethod
    @sync_to_async
    def count_seller_active_schedules(seller_id: int) -> int:
        """Get number of active schedules for a specific seller"""
        return PostSchedule.objects.filter(seller_id=seller_id, is_active=True).count()
    
    @staticmethod
    @sync_to_async
    def update_schedule_post_time(schedule_id: int, last_posted: datetime, 
                                 next_post: datetime) -> Optional[PostSchedule]:
        """Update schedule after posting"""
        try:
            schedule = PostSchedule.objects.get(id=schedule_id)
            schedule.last_posted_at = last_posted
            schedule.next_post_at = next_post
            schedule.save()
            return schedule
        except PostSchedule.DoesNotExist:
            return None

# Export database instance
db = Database()
