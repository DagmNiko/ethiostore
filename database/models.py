"""
Database models for SF Telegram Bot
All models use SQLAlchemy ORM with async support
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import BigInteger, String, Integer, Boolean, DateTime, Text, Float, ForeignKey, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func

class Base(DeclarativeBase):
    """Base class for all models"""
    pass

class User(Base):
    """User model - stores both sellers and buyers"""
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # Telegram user ID
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # User type and role
    role: Mapped[str] = mapped_column(String(20), default="buyer")  # seller or buyer
    
    # Seller-specific fields
    store_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    channel_username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Premium status
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    premium_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Registration state (for FSM)
    state: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    state_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    products: Mapped[list["Product"]] = relationship("Product", back_populates="seller", cascade="all, delete-orphan")
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="buyer", foreign_keys="Order.buyer_id")
    received_orders: Mapped[list["Order"]] = relationship("Order", back_populates="seller", foreign_keys="Order.seller_id")
    schedules: Mapped[list["PostSchedule"]] = relationship("PostSchedule", back_populates="seller", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User {self.id} - {self.role}: {self.store_name or self.first_name}>"

class Product(Base):
    """Product model - stores product information"""
    __tablename__ = "products"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    seller_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    
    # Product details
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Optional for custom descriptions
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Optional for custom descriptions
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Product type
    product_type: Mapped[str] = mapped_column(String(20), default="standard")  # standard, custom_description
    
    # Category-specific fields (stored as JSON)
    category_fields: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Image storage
    image_path: Mapped[str] = mapped_column(String(500))  # Path to watermarked image
    original_image_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # Original without watermark
    
    # Visibility and status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)  # For inline search
    
    # Engagement counters
    likes_count: Mapped[int] = mapped_column(Integer, default=0)
    saves_count: Mapped[int] = mapped_column(Integer, default=0)
    orders_count: Mapped[int] = mapped_column(Integer, default=0)
    views_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Custom button (optional)
    custom_button_text: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    custom_button_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Button settings
    like_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    save_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    order_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    seller: Mapped["User"] = relationship("User", back_populates="products")
    engagements: Mapped[list["Engagement"]] = relationship("Engagement", back_populates="product", cascade="all, delete-orphan")
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="product", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Product {self.id}: {self.title} - {self.price} birr>"

class Engagement(Base):
    """Track user engagement (likes, saves) with products"""
    __tablename__ = "engagements"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger)  # User who engaged
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id", ondelete="CASCADE"))
    
    # Engagement type
    liked: Mapped[bool] = mapped_column(Boolean, default=False)
    saved: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    product: Mapped["Product"] = relationship("Product", back_populates="engagements")
    
    def __repr__(self):
        return f"<Engagement user={self.user_id} product={self.product_id}>"

class Order(Base):
    """Order model - stores order information"""
    __tablename__ = "orders"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    buyer_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    seller_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id", ondelete="CASCADE"))
    
    # Order details
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    buyer_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    buyer_location: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Order status
    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending, confirmed, completed, cancelled
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    buyer: Mapped["User"] = relationship("User", back_populates="orders", foreign_keys=[buyer_id])
    seller: Mapped["User"] = relationship("User", back_populates="received_orders", foreign_keys=[seller_id])
    product: Mapped["Product"] = relationship("Product", back_populates="orders")
    
    def __repr__(self):
        return f"<Order {self.id}: {self.quantity}x Product {self.product_id}>"

class PostSchedule(Base):
    """Schedule model - stores auto-posting schedules"""
    __tablename__ = "schedules"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    seller_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id", ondelete="CASCADE"))
    
    # Schedule settings
    channel_username: Mapped[str] = mapped_column(String(255))
    interval_days: Mapped[int] = mapped_column(Integer, default=2)  # Repost every X days
    post_time: Mapped[str] = mapped_column(String(10), default="09:00")  # Time in HH:MM format
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_posted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    next_post_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    seller: Mapped["User"] = relationship("User", back_populates="schedules")
    
    def __repr__(self):
        return f"<Schedule {self.id}: Product {self.product_id} every {self.interval_days} days>"

# New table to track channel posts per product so we can edit them later
class ChannelPost(Base):
    __tablename__ = "channel_posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id", ondelete="CASCADE"), index=True)
    channel_username: Mapped[str] = mapped_column(String(255), nullable=False)
    message_id: Mapped[int] = mapped_column(Integer, nullable=False)
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<ChannelPost product={self.product_id} channel={self.channel_username} message_id={self.message_id}>"



