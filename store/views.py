import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum
from django.core.mail import send_mail
from .models import Product, Order
# from flask import Flask, render_template
# app= Flask(__Glow_Cart__)
# @app.route('/Glow_cart')
# def home():
#   return render_template('home.html')
def home(request):
    products = Product.objects.all()
    return render(request, 'home.html', {'products': products})


def cart(request):
    return render(request, 'cart.html')


def product_detail(request, id):
    product = get_object_or_404(Product, id=id)
    return render(request, 'product.html', {'product': product})


@login_required
def checkout(request):
    if request.method == 'POST':
        name    = request.POST.get('name')
        street  = request.POST.get('street', '').strip()
        city    = request.POST.get('city', '').strip()
        state   = request.POST.get('state', '').strip()
        pincode = request.POST.get('pincode', '').strip()
        address  = f"{street}, {city}, {state} - {pincode}"
        phone    = request.POST.get('phone')
        items    = request.POST.get('items')
        total    = request.POST.get('total', 0)
        discount = request.POST.get('discount', 0)
        shipping = request.POST.get('shipping', 0)
        promo    = request.POST.get('promo', '')
        email    = request.POST.get('email', '').strip()

        if email and not request.user.email:
            request.user.email = email
            request.user.save(update_fields=['email'])

        order = Order.objects.create(
            user=request.user,
            name=name,
            address=address,
            phone=phone,
            items=items,
            total=int(float(total))
        )

        try:
            parsed_items = json.loads(items)
            item_lines = '\n'.join(
                f"  - {i.get('name')} x{i.get('qty', 1)}  \u20b9{i.get('price')}"
                for i in parsed_items
            )
        except (ValueError, TypeError):
            item_lines = items

        promo_line    = f"  Promo Code  : {promo}\n" if promo else ""
        discount_line = f"  Discount    : -\u20b9{float(discount):.2f}\n" if float(discount) > 0 else ""
        shipping_line = f"  Shipping    : \u20b9{float(shipping):.2f}\n" if float(shipping) > 0 else "  Shipping    : FREE \u2713\n"

        email_body = (
            f"Dear {name},\n\n"
            f"Thank you for shopping with Glow Cart! \U0001f6cd\ufe0f\n"
            f"Your order has been confirmed and is being processed.\n\n"
            f"{'=' * 40}\n"
            f"  ORDER DETAILS  (Order #{order.id})\n"
            f"{'=' * 40}\n"
            f"{item_lines}\n"
            f"{'─' * 40}\n"
            f"{promo_line}"
            f"{discount_line}"
            f"{shipping_line}"
            f"  Total Payable : \u20b9{order.total}\n"
            f"  Payment Mode  : Cash on Delivery (COD)\n"
            f"{'=' * 40}\n\n"
            f"  Delivery Address : {address}\n"
            f"  Phone            : {phone}\n\n"
            f"We will deliver your order soon. \U0001f69a\n\n"
            f"{'─' * 40}\n"
            f"Thank you for shopping with Glow Cart\n"
            f"\u2728 Where Trends Light Up Your Life \u2728\n"
            f"{'─' * 40}\n"
            f"Support: glowcart0811@gmail.com\n"
        )

        recipient = request.user.email or request.POST.get('email', '')
        if recipient:
            send_mail(
                subject=f"Your Order is Confirmed \u2013 Glow Cart \u2726 (Order #{order.id})",
                message=email_body,
                from_email=None,
                recipient_list=[recipient],
                fail_silently=False,
            )

        return redirect('/success/')

    return render(request, 'checkout.html', {
        'is_first_order': not Order.objects.filter(user=request.user).exists()
    })


def success(request):
    return render(request, 'success.html')


def signup(request):
    if request.method == 'POST':
        username  = request.POST.get('username', '').strip()
        password  = request.POST.get('password')
        password2 = request.POST.get('password2')
        email     = request.POST.get('email', '').strip()

        if not username or not password or not email:
            return render(request, 'signup.html', {'error': 'All fields are required.'})

        if password != password2:
            return render(request, 'signup.html', {'error': 'Passwords do not match.'})

        if User.objects.filter(username=username).exists():
            return render(request, 'signup.html', {'error': 'Username already taken.'})

        if User.objects.filter(email=email).exists():
            return render(request, 'signup.html', {'error': 'Email already registered.'})

        user = User.objects.create_user(username=username, password=password, email=email)
        login(request, user)
        return redirect('/')

    return render(request, 'signup.html')


@login_required
def my_orders(request):
    raw_orders = Order.objects.filter(user=request.user).order_by('-id')
    orders = []
    for order in raw_orders:
        try:
            items = json.loads(order.items)
        except (ValueError, TypeError):
            items = []
        orders.append({
            'id':      order.id,
            'items':   items,
            'address': order.address,
            'phone':   order.phone,
            'total':   order.total,
            'status':  order.status,
        })
    return render(request, 'orders.html', {'orders': orders})


@user_passes_test(lambda u: u.is_staff, login_url='/login/')
def dashboard(request):
    total_orders  = Order.objects.count()
    total_revenue = Order.objects.aggregate(rev=Sum('total'))['rev'] or 0
    total_users   = User.objects.count()
    total_products = Product.objects.count()
    status_counts = {
        'Pending':   Order.objects.filter(status='Pending').count(),
        'Confirmed': Order.objects.filter(status='Confirmed').count(),
        'Shipped':   Order.objects.filter(status='Shipped').count(),
        'Delivered': Order.objects.filter(status='Delivered').count(),
    }
    latest_orders = Order.objects.select_related('user').order_by('-id')[:10]
    return render(request, 'dashboard.html', {
        'total_orders':   total_orders,
        'total_revenue':  total_revenue,
        'total_users':    total_users,
        'total_products': total_products,
        'status_counts':  status_counts,
        'latest_orders':  latest_orders,
    })


@user_passes_test(lambda u: u.is_staff, login_url='/login/')
def manage_orders(request):
    all_orders = Order.objects.select_related('user').order_by('-id')
    return render(request, 'manage_orders.html', {'orders': all_orders})


@user_passes_test(lambda u: u.is_staff, login_url='/login/')
def update_order_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in ['Pending', 'Confirmed', 'Shipped', 'Delivered']:
            order.status = new_status
            order.save()
    return redirect('manage_orders')


@user_passes_test(lambda u: u.is_staff, login_url='/login/')
def manage_products(request):
    products = Product.objects.all().order_by('-id')
    return render(request, 'manage_products.html', {'products': products})


@user_passes_test(lambda u: u.is_staff, login_url='/login/')
def delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        product.delete()
    return redirect('manage_products')


@user_passes_test(lambda u: u.is_staff, login_url='/login/')
def manage_customers(request):
    customers = User.objects.filter(is_staff=False).order_by('-date_joined')
    customer_data = []
    for c in customers:
        customer_data.append({
            'username':    c.username,
            'email':       c.email,
            'joined':      c.date_joined.strftime('%d %b %Y'),
            'order_count': Order.objects.filter(user=c).count(),
            'total_spent': Order.objects.filter(user=c).aggregate(t=Sum('total'))['t'] or 0,
        })
    return render(request, 'manage_customers.html', {'customers': customer_data})
