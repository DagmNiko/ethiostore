from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # Marketing / Public Pages
    path('', views.home, name='home'),
    path('product/', views.product_detail, name='product_detail'),
    path('features/', views.features, name='features'),
    path('pricing/', views.pricing, name='pricing'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('blog/', views.blog_hub, name='blog_hub'),
    path('blog/<slug:slug>/', views.blog_detail, name='blog_detail'),
    path('faq/', views.faq, name='faq'),
    path('terms/', views.terms, name='terms'),
    path('privacy/', views.privacy, name='privacy'),
    
    # Auth Pages
    path('auth/login/', views.login_view, name='login'),
    path('auth/register/', views.register_view, name='register'),
    path('auth/verify/', views.verify_view, name='verify'),

    # Dashboard Pages
    path('dashboard/', views.dashboard_overview, name='overview'),
    path('dashboard/products/', views.products_list, name='products'),
    path('dashboard/products/add/', views.product_add, name='product_add'),
    path('dashboard/orders/', views.orders_list, name='orders'),
    path('dashboard/orders/<int:order_id>/', views.order_detail, name='order_detail'),
    path('dashboard/customers/', views.customers_list, name='customers'),
    path('dashboard/customers/<int:customer_id>/', views.customer_profile, name='customer_profile'),
    path('dashboard/scheduling/', views.scheduling, name='scheduling'),
    path('dashboard/billing/', views.billing, name='billing'),
    path('dashboard/affiliates/', views.affiliates, name='affiliates'),
    path('dashboard/settings/', views.settings_view, name='settings'),
]
