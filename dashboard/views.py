from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages

# --- Public / Marketing Pages ---
def home(request):
    return render(request, 'dashboard/marketing/home.html')

def product_detail(request):
    return render(request, 'dashboard/marketing/product_detail.html')

def features(request):
    return render(request, 'dashboard/marketing/features.html')

def pricing(request):
    return render(request, 'dashboard/marketing/pricing.html')

def about(request):
    return render(request, 'dashboard/marketing/about.html')

def contact(request):
    return render(request, 'dashboard/marketing/contact.html')

def blog_hub(request):
    return render(request, 'dashboard/marketing/blog_hub.html')

def blog_detail(request, slug):
    return render(request, 'dashboard/marketing/blog_detail.html')

def faq(request):
    return render(request, 'dashboard/marketing/faq.html')

def terms(request):
    return render(request, 'dashboard/marketing/terms.html')

def privacy(request):
    return render(request, 'dashboard/marketing/privacy.html')

# --- Auth Pages ---
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:overview')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard:overview')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'dashboard/auth/login.html')

def register_view(request):
    return render(request, 'dashboard/auth/register.html')

def verify_view(request):
    return render(request, 'dashboard/auth/verify.html')

# --- Dashboard Pages ---
def dashboard_overview(request):
    return render(request, 'dashboard/app/overview.html')

def products_list(request):
    return render(request, 'dashboard/app/products.html')

def product_add(request):
    return render(request, 'dashboard/app/product_add.html')

def orders_list(request):
    return render(request, 'dashboard/app/orders.html')

def order_detail(request, order_id):
    return render(request, 'dashboard/app/order_detail.html')

def customers_list(request):
    return render(request, 'dashboard/app/customers.html')

def customer_profile(request, customer_id):
    return render(request, 'dashboard/app/customer_profile.html')

def scheduling(request):
    return render(request, 'dashboard/app/scheduling.html')

def billing(request):
    return render(request, 'dashboard/app/billing.html')

def affiliates(request):
    return render(request, 'dashboard/app/affiliates.html')

def settings_view(request):
    return render(request, 'dashboard/app/settings.html')
