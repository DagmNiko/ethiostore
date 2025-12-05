from django.contrib import admin
from .models import User, Product, Engagement, Order, PostSchedule, ChannelPost


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['id', 'username', 'first_name', 'role', 'is_premium', 'created_at']
    list_filter = ['role', 'is_premium']
    search_fields = ['id', 'username', 'first_name', 'store_name']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'seller', 'price', 'category', 'is_active', 'created_at']
    list_filter = ['product_type', 'category', 'is_active', 'is_public']
    search_fields = ['title', 'description']


@admin.register(Engagement)
class EngagementAdmin(admin.ModelAdmin):
    list_display = ['id', 'user_id', 'product', 'liked', 'saved', 'created_at']
    list_filter = ['liked', 'saved']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'buyer', 'seller', 'product', 'quantity', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['buyer_phone', 'buyer_location']


@admin.register(PostSchedule)
class PostScheduleAdmin(admin.ModelAdmin):
    list_display = ['id', 'seller', 'product', 'channel_username', 'interval_days', 'is_active', 'next_post_at']
    list_filter = ['is_active']


@admin.register(ChannelPost)
class ChannelPostAdmin(admin.ModelAdmin):
    list_display = ['id', 'product', 'channel_username', 'message_id', 'posted_at']
    list_filter = ['channel_username']

