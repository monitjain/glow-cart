
import json
import logging
import re
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum, Avg, Count, F
from django.db import models, transaction
from django.core.mail import send_mail
from django.http import JsonResponse
from django.utils import timezone

from .models import (
    Product,
    Order,
    SiteVisitor,
    ReturnRequest,
    Review,
    BankDetails,
)
from .bank_security import (
    encrypt_bank_value,
    decrypt_bank_value,
)


logger = logging.getLogger(__name__)


# ── Email helper ──────────────────────────────────────────────

def send_order_email(order, recipient, event='confirmed', tracking_id=''):
    """Send order status email. event: confirmed | pending | shipped | delivered"""

    try:
        parsed_items = json.loads(order.items)
        item_lines = '\n'.join(
            f"  • {i.get('name')} x{i.get('qty', 1)}  ₹{i.get('price')}"
            for i in parsed_items
        )
    except (ValueError, TypeError):
        item_lines = order.items

    divider = '─' * 42

    if event == 'confirmed':
        subject = f"✅ Order Confirmed – Glow Cart (Order #{order.id})"
        body = (
            f"Dear {order.name},\n\n"
            f"Thank you for shopping with Glow Cart! 🛍️\n"
            f"Your order has been confirmed and is being processed.\n\n"
            f"{'=' * 42}\n"
            f"  ORDER #{order.id} — CONFIRMED\n"
            f"{'=' * 42}\n"
            f"{item_lines}\n"
            f"{divider}\n"
            f"  Total Payable : ₹{order.total}\n"
            f"  Payment Mode  : Cash on Delivery (COD)\n"
            f"{'=' * 42}\n\n"
            f"  Delivery Address : {order.address}\n"
            f"  Phone            : {order.phone}\n\n"
            f"We will notify you once your order is shipped. 🚚\n\n"
        )

    elif event == 'pending':
        subject = f"⏳ Order Received – Glow Cart (Order #{order.id})"
        body = (
            f"Dear {order.name},\n\n"
            f"We have received your order and it is currently pending review.\n\n"
            f"  Order ID : #{order.id}\n"
            f"  Total    : ₹{order.total}\n"
            f"  Status   : Pending\n\n"
            f"You will receive another email once your order is confirmed.\n\n"
        )

    elif event == 'shipped':
        subject = f"🚚 Your Order is Shipped – Glow Cart (Order #{order.id})"
        xpressbees_url = (
            f"https://www.xpressbees.com/shipment/tracking?awb={tracking_id}"
            if tracking_id else ""
        )
        tracking_section = (
            f"\n  Courier Partner : Xpressbees\n"
            f"  Tracking ID     : {tracking_id}\n"
            f"  Track Here      : {xpressbees_url}\n"
        ) if tracking_id else "\n  Tracking details will be updated shortly.\n"

        body = (
            f"Dear {order.name},\n\n"
            f"Great news! Your order has been shipped. 🎉\n\n"
            f"{'=' * 42}\n"
            f"  ORDER #{order.id} — SHIPPED\n"
            f"{'=' * 42}\n"
            f"{item_lines}\n"
            f"{divider}\n"
            f"  Total : ₹{order.total}\n"
            f"{'=' * 42}\n"
            f"{tracking_section}\n"
            f"  Delivery Address : {order.address}\n\n"
            f"Expected delivery in 3–5 business days.\n\n"
        )

    elif event == 'delivered':
        subject = f"🎉 Order Delivered – Glow Cart (Order #{order.id})"
        body = (
            f"Dear {order.name},\n\n"
            f"Your order has been delivered successfully! 🎊\n\n"
            f"  Order ID : #{order.id}\n"
            f"  Total    : ₹{order.total}\n\n"
            f"We hope you love your purchase!\n"
            f"Please leave a review — it helps us grow. ⭐\n\n"
        )
    else:
        return

    footer = (
        f"{divider}\n"
        f"Thank you for shopping with Glow Cart\n"
        f"✨ Where Trends Light Up Your Life ✨\n"
        f"{divider}\n"
        f"Support: glowcart0811@gmail.com\n"
    )

    try:
        send_mail(
            subject=subject,
            message=body + footer,
            from_email=None,
            recipient_list=[recipient],
            fail_silently=False,
        )
        logger.info(
            'Email sent to %s for order #%s event=%s',
            recipient, order.id, event
        )
    except Exception as e:
        logger.error(
            'Email failed for order #%s event=%s: %s',
            order.id, event, str(e)
        )


# ── Visitor tracking helper ───────────────────────────────────

def track_visitor(request):
    if not request.session.session_key:
        request.session.create()

    SiteVisitor.objects.update_or_create(
        session_key=request.session.session_key,
        defaults={
            'page': request.path,
            'is_logged_in': request.user.is_authenticated,
        }
    )


# ── Public views ──────────────────────────────────────────────

def home(request):
    track_visitor(request)
    products = Product.objects.filter(is_active=True)
    return render(request, 'home.html', {'products': products})


def cart(request):
    track_visitor(request)
    return render(request, 'cart.html')


def product_detail(request, id):
    track_visitor(request)
    product = get_object_or_404(Product, id=id, is_active=True)

    product_reviews = Review.objects.filter(
        product=product,
        is_visible=True
    ).select_related('user').order_by('-created_at')

    rating_stats = product_reviews.aggregate(
        average=Avg('rating'),
        count=Count('id')
    )

    return render(request, 'product.html', {
        'product': product,
        'product_reviews': product_reviews,
        'average_rating': rating_stats['average'],
        'review_count': rating_stats['count'],
    })


@login_required
def checkout(request):
    track_visitor(request)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        street = request.POST.get('street', '').strip()
        city = request.POST.get('city', '').strip()
        state = request.POST.get('state', '').strip()
        pincode = request.POST.get('pincode', '').strip()
        phone = request.POST.get('phone', '').strip()
        email = request.POST.get('email', '').strip()
        promo = request.POST.get('promo', '').strip().upper()

        def checkout_error(message):
            return render(request, 'checkout.html', {
                'is_first_order': not Order.objects.filter(
                    user=request.user
                ).exists(),
                'error': message,
            })

        if promo:
            return checkout_error(
                'Promo codes are no longer available.'
            )

        if not all([name, street, city, state, pincode, phone]):
            return checkout_error(
                'Please complete all required delivery details.'
            )

        try:
            cart_items = json.loads(request.POST.get('items', ''))
            if not isinstance(cart_items, list) or not cart_items:
                raise ValueError
        except (ValueError, TypeError):
            return checkout_error(
                'Your cart is invalid. Please refresh it and try again.'
            )

        quantities = {}

        try:
            for item in cart_items:
                product_id = int(item['id'])
                qty = int(item['qty'])

                if product_id <= 0 or qty <= 0 or qty > 100:
                    raise ValueError

                quantities[product_id] = (
                    quantities.get(product_id, 0) + qty
                )

            if not quantities:
                raise ValueError

        except (KeyError, TypeError, ValueError):
            return checkout_error(
                'Your cart contains invalid items. Please update your cart.'
            )

        try:
            with transaction.atomic():
                products = list(
                    Product.objects.select_for_update()
                    .filter(
                        id__in=quantities.keys(),
                        is_active=True
                    )
                    .order_by('id')
                )

                if len(products) != len(quantities):
                    raise ValueError(
                        'A product in your cart is no longer available.'
                    )

                order_items = []
                subtotal = Decimal('0')

                for product in products:
                    qty = quantities[product.id]

                    if product.stock is None:
                        raise ValueError(
                            f'{product.name} has availability on request '
                            f'and cannot be ordered yet.'
                        )

                    if product.stock < qty:
                        raise ValueError(
                            f'Only {product.stock} unit(s) of '
                            f'{product.name} are currently available.'
                        )

                    price = Decimal(str(product.price))
                    subtotal += price * qty

                    order_items.append({
                        'id': product.id,
                        'name': product.name,
                        'price': product.price,
                        'qty': qty,
                    })

                discount = Decimal('0')
                shipping = Decimal('0')

                total = int(
                    subtotal.quantize(
                        Decimal('1'),
                        rounding=ROUND_HALF_UP
                    )
                )

                address = f'{street}, {city}, {state} - {pincode}'

                if email and not request.user.email:
                    request.user.email = email
                    request.user.save(update_fields=['email'])

                order = Order.objects.create(
                    user=request.user,
                    name=name,
                    address=address,
                    street=street,
                    city=city,
                    state=state,
                    pincode=pincode,
                    phone=phone,
                    email=email or request.user.email,
                    items=json.dumps(order_items),
                    total=total,
                    status='Confirmed',
                )

                for product in products:
                    product.stock -= quantities[product.id]
                    product.save(update_fields=['stock'])

            recipient = request.user.email or email
            if recipient:
                send_order_email(order, recipient, event='confirmed')

            return redirect('/review/order/')

        except ValueError as error:
            return checkout_error(str(error))

    return render(request, 'checkout.html', {
        'is_first_order': not Order.objects.filter(
            user=request.user
        ).exists()
    })


def success(request):
    return render(request, 'success.html')


def policy(request):
    return render(request, 'policy.html')


def faq(request):
    return render(request, 'faq.html')


def signup(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        email = request.POST.get('email', '').strip()

        if not username or not password or not email:
            return render(request, 'signup.html', {
                'error': 'All fields are required.'
            })

        if password != password2:
            return render(request, 'signup.html', {
                'error': 'Passwords do not match.'
            })

        if User.objects.filter(username=username).exists():
            return render(request, 'signup.html', {
                'error': 'Username already taken.'
            })

        if User.objects.filter(email=email).exists():
            return render(request, 'signup.html', {
                'error': 'Email already registered.'
            })

        user = User.objects.create_user(
            username=username,
            password=password,
            email=email
        )
        login(request, user)
        return redirect('/')

    return render(request, 'signup.html')


@login_required
def my_orders(request):
    raw_orders = Order.objects.filter(
        user=request.user
    ).order_by('-id')

    orders = []

    for order in raw_orders:
        try:
            items = json.loads(order.items)
        except (ValueError, TypeError):
            items = []

        orders.append({
            'id': order.id,
            'items': items,
            'address': order.address,
            'phone': order.phone,
            'total': order.total,
            'status': order.status,
            'tracking_id': order.tracking_id,
        })

    return render(request, 'orders.html', {'orders': orders})


# ── Admin views ───────────────────────────────────────────────

@user_passes_test(lambda u: u.is_staff, login_url='/login/')
def dashboard(request):
    cutoff = timezone.now() - timedelta(minutes=5)
    SiteVisitor.objects.filter(last_seen__lt=cutoff).delete()

    live_count = SiteVisitor.objects.count()
    live_visitors = SiteVisitor.objects.order_by('-last_seen')[:20]

    total_orders = Order.objects.count()
    total_revenue = Order.objects.aggregate(
        rev=Sum('total')
    )['rev'] or 0

    total_users = User.objects.count()
    total_products = Product.objects.count()

    status_counts = {
        'Pending': Order.objects.filter(status='Pending').count(),
        'Confirmed': Order.objects.filter(status='Confirmed').count(),
        'Shipped': Order.objects.filter(status='Shipped').count(),
        'Delivered': Order.objects.filter(status='Delivered').count(),
    }

    latest_orders = Order.objects.select_related(
        'user'
    ).order_by('-id')[:10]

    pending_returns = ReturnRequest.objects.filter(
        status='Pending'
    ).count()
    pending_refunds = ReturnRequest.objects.filter(
    request_type='Return',
    status__in=['Approved', 'Completed'],
    refund_status='Pending'
).exclude(
    refund_account_number_encrypted=''
).count()
    return_counts = {
        'Return': ReturnRequest.objects.filter(
            request_type='Return',
            status='Pending'
        ).count(),
        'Exchange': ReturnRequest.objects.filter(
            request_type='Exchange',
            status='Pending'
        ).count(),
        'Replace': ReturnRequest.objects.filter(
            request_type='Replace',
            status='Pending'
        ).count(),
    }

    latest_returns = ReturnRequest.objects.select_related(
        'order', 'user'
    ).order_by('-created_at')[:5]

    return render(request, 'dashboard.html', {
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'total_users': total_users,
        'total_products': total_products,
        'pending_refunds': pending_refunds,
        'status_counts': status_counts,
        'latest_orders': latest_orders,
        'live_count': live_count,
        'live_visitors': live_visitors,
        'pending_returns': pending_returns,
        'return_counts': return_counts,
        'latest_returns': latest_returns,
    })


@user_passes_test(lambda u: u.is_staff, login_url='/login/')
def live_visitors_api(request):
    """JSON endpoint polled every 30s by dashboard JS."""
    cutoff = timezone.now() - timedelta(minutes=5)
    SiteVisitor.objects.filter(last_seen__lt=cutoff).delete()

    visitors = list(
        SiteVisitor.objects.values(
            'page', 'is_logged_in', 'last_seen'
        )
    )

    for visitor in visitors:
        visitor['last_seen'] = visitor['last_seen'].strftime('%H:%M:%S')

    return JsonResponse({
        'count': len(visitors),
        'visitors': visitors
    })


@user_passes_test(lambda u: u.is_staff, login_url='/login/')
def manage_orders(request):
    all_orders = Order.objects.select_related(
        'user'
    ).order_by('-created_at', '-id')

    search_query = request.GET.get('q', '').strip()

    if search_query:
        all_orders = all_orders.filter(
            models.Q(name__icontains=search_query) |
            models.Q(phone__icontains=search_query) |
            models.Q(email__icontains=search_query) |
            models.Q(user__username__icontains=search_query) |
            models.Q(id__icontains=search_query)
        )

    status_filter = request.GET.get('status', '').strip()
    valid_statuses = [
        'Pending', 'Confirmed', 'Shipped', 'Delivered'
    ]

    if status_filter in valid_statuses:
        all_orders = all_orders.filter(status=status_filter)

    total_orders = Order.objects.count()
    pending_orders = Order.objects.filter(status='Pending').count()
    confirmed_orders = Order.objects.filter(status='Confirmed').count()
    shipped_orders = Order.objects.filter(status='Shipped').count()
    delivered_orders = Order.objects.filter(status='Delivered').count()

    return render(request, 'manage_orders.html', {
        'orders': all_orders,
        'search_query': search_query,
        'status_filter': status_filter,
        'status_choices': Order.STATUS_CHOICES,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'confirmed_orders': confirmed_orders,
        'shipped_orders': shipped_orders,
        'delivered_orders': delivered_orders,
    })


@user_passes_test(lambda u: u.is_staff, login_url='/login/')
def order_details(request, order_id):
    order = get_object_or_404(
        Order.objects.select_related('user'),
        id=order_id
    )

    try:
        order_items = json.loads(order.items)
    except (ValueError, TypeError):
        order_items = []

    return render(request, 'order_details.html', {
        'order': order,
        'order_items': order_items,
    })


@user_passes_test(lambda u: u.is_staff, login_url='/login/')
def update_order_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    if request.method == 'POST':
        new_status = request.POST.get('status')
        tracking_id = request.POST.get('tracking_id', '').strip()

        if new_status in [
            'Pending', 'Confirmed', 'Shipped', 'Delivered'
        ]:
            old_status = order.status
            order.status = new_status

            if tracking_id:
                order.tracking_id = tracking_id

            order.save()

            if new_status != old_status:
                recipient = order.user.email if order.user else ''

                if recipient:
                    send_order_email(
                        order,
                        recipient,
                        event=new_status.lower(),
                        tracking_id=order.tracking_id
                    )

    return redirect('manage_orders')


@user_passes_test(lambda u: u.is_staff, login_url='/login/')
def manage_products(request):
    products = Product.objects.all().order_by('-id')
    error = ''
    editing_product = None

    if request.method == 'POST':
        product_id = request.POST.get('product_id', '').strip()

        if product_id:
            editing_product = get_object_or_404(
                Product,
                id=product_id
            )

        name = request.POST.get('name', '').strip()
        price = request.POST.get('price', '').strip()
        sku = request.POST.get('sku', '').strip() or None
        stock_value = request.POST.get('stock', '').strip()
        description = request.POST.get('description', '').strip()
        is_active = request.POST.get('is_active') == 'on'
        image = request.FILES.get('image')

        if not name or not price:
            error = 'Product name and price are required.'
        else:
            try:
                price = int(price)
                stock = int(stock_value) if stock_value else None

                if price < 0 or (stock is not None and stock < 0):
                    raise ValueError

                duplicate_sku = (
                    Product.objects.filter(sku=sku).exclude(
                        id=editing_product.id if editing_product else None
                    ).exists()
                    if sku else False
                )

                if duplicate_sku:
                    error = 'This SKU is already assigned to another product.'

                elif not editing_product and not image:
                    error = 'Please upload a product image.'

                else:
                    product = editing_product or Product()

                    product.name = name
                    product.price = price
                    product.sku = sku
                    product.stock = stock
                    product.description = description
                    product.is_active = is_active

                    if image:
                        product.image = image

                    product.save()
                    return redirect('manage_products')

            except ValueError:
                error = 'Enter a valid price and stock quantity.'

    products = Product.objects.all().order_by('-id')

    return render(request, 'manage_products.html', {
        'products': products,
        'error': error,
        'editing_product': editing_product,
    })


@user_passes_test(lambda u: u.is_staff, login_url='/login/')
def delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        product.delete()

    return redirect('manage_products')


@user_passes_test(lambda u: u.is_staff, login_url='/login/')
def manage_customers(request):
    customers = User.objects.filter(
        is_staff=False
    ).order_by('-date_joined')

    customer_data = []

    for customer in customers:
        customer_data.append({
            'username': customer.username,
            'email': customer.email,
            'joined': customer.date_joined.strftime('%d %b %Y'),
            'order_count': Order.objects.filter(user=customer).count(),
            'total_spent': Order.objects.filter(
                user=customer
            ).aggregate(t=Sum('total'))['t'] or 0,
        })

    return render(
        request,
        'manage_customers.html',
        {'customers': customer_data}
    )


# ── Return / Exchange / Replace ───────────────────────────────

@login_required
def submit_return_request(request, order_id):
    order = get_object_or_404(
        Order,
        id=order_id,
        user=request.user
    )

    if order.status != 'Delivered':
        return redirect('orders')

    existing = ReturnRequest.objects.filter(
        order=order,
        user=request.user
    ).first()

    bank_details = BankDetails.objects.filter(
        user=request.user
    ).first()

    if request.method == 'POST':

        request_type = request.POST.get('request_type')
        reason = request.POST.get('reason', '').strip()

        if existing:
            return redirect('orders')

        if request_type not in ['Return', 'Exchange', 'Replace']:
            return render(request, 'return_request.html', {
                'order': order,
                'existing': existing,
                'bank_details': bank_details,
                'error': 'Please select a valid request type.'
            })

        if not reason:
            return render(request, 'return_request.html', {
                'order': order,
                'existing': existing,
                'bank_details': bank_details,
                'error': 'Please enter a reason for your request.'
            })

        refund_values = {}

        # Bank details are required only for Return requests
        if request_type == 'Return':

            account_choice = request.POST.get(
                'refund_account_choice',
                'saved' if bank_details else 'new'
            )

            if account_choice == 'saved' and bank_details:

                # Copy encrypted saved details into this return request
                refund_values = {
                    'refund_account_holder_encrypted':
                        bank_details.account_holder_encrypted,

                    'refund_account_number_encrypted':
                        bank_details.account_number_encrypted,

                    'refund_ifsc_encrypted':
                        bank_details.ifsc_encrypted,

                    'refund_bank_name_encrypted':
                        bank_details.bank_name_encrypted,

                    'refund_account_last4':
                        bank_details.account_last4,
                }

            elif account_choice == 'new':

                account_holder = request.POST.get(
                    'refund_account_holder', ''
                ).strip()

                account_number = request.POST.get(
                    'refund_account_number', ''
                ).strip().replace(' ', '').replace('-', '')

                confirm_account_number = request.POST.get(
                    'confirm_refund_account_number', ''
                ).strip().replace(' ', '').replace('-', '')

                ifsc = request.POST.get(
                    'refund_ifsc', ''
                ).strip().upper()

                bank_name = request.POST.get(
                    'refund_bank_name', ''
                ).strip()

                error = None

                if not 2 <= len(account_holder) <= 100:
                    error = 'Please enter a valid account holder name.'

                elif not re.fullmatch(r'[0-9]{6,18}', account_number):
                    error = 'Account number must contain 6 to 18 digits.'

                elif account_number != confirm_account_number:
                    error = 'Account numbers do not match.'

                elif not re.fullmatch(r'[A-Z]{4}0[A-Z0-9]{6}', ifsc):
                    error = 'Please enter a valid 11-character IFSC code.'

                elif len(bank_name) > 100:
                    error = 'Bank name must be 100 characters or fewer.'

                if error:
                    return render(request, 'return_request.html', {
                        'order': order,
                        'existing': existing,
                        'bank_details': bank_details,
                        'error': error
                    })

                # Encrypt refund details before saving the request
                refund_values = {
                    'refund_account_holder_encrypted':
                        encrypt_bank_value(account_holder),

                    'refund_account_number_encrypted':
                        encrypt_bank_value(account_number),

                    'refund_ifsc_encrypted':
                        encrypt_bank_value(ifsc),

                    'refund_bank_name_encrypted':
                        encrypt_bank_value(bank_name),

                    'refund_account_last4':
                        account_number[-4:],
                }
                

                # Save first-time bank details to the customer's profile.
                # Never overwrite an existing saved account.
                if not bank_details:
                    BankDetails.objects.get_or_create(
                        user=request.user,
                        defaults={
                            'account_holder_encrypted':
                                refund_values['refund_account_holder_encrypted'],
                            'account_number_encrypted':
                                refund_values['refund_account_number_encrypted'],
                            'ifsc_encrypted':
                                refund_values['refund_ifsc_encrypted'],
                            'bank_name_encrypted':
                                refund_values['refund_bank_name_encrypted'],
                            'account_last4':
                                refund_values['refund_account_last4'],
                        }
                    )

            else:
                return render(request, 'return_request.html', {
                    'order': order,
                    'existing': existing,
                    'bank_details': bank_details,
                    'error': 'Please select a valid refund account.'
                })

                return render(request, 'return_request.html', {
                    'order': order,
                    'existing': existing,
                    'bank_details': bank_details,
                    'error': 'Please select a valid refund account.'
                })

        # Create the request with its own encrypted refund snapshot
        rr = ReturnRequest.objects.create(
            order=order,
            user=request.user,
            request_type=request_type,
            reason=reason,
            **refund_values
        )

        recipient = request.user.email

        if recipient:
            send_return_email(
                rr,
                recipient,
                event='submitted'
            )

        return redirect('orders')

    return render(request, 'return_request.html', {
        'order': order,
        'existing': existing,
        'bank_details': bank_details
    })


@user_passes_test(lambda u: u.is_staff, login_url='/login/')
def manage_returns(request):
    requests = ReturnRequest.objects.select_related(
        'order', 'user'
    ).order_by('-created_at')

    return render(request, 'manage_returns.html', {
        'requests': requests
    })

@user_passes_test(lambda u: u.is_staff, login_url='/login/')
def manage_refunds(request):
    refunds = ReturnRequest.objects.filter(
        request_type='Return',
        status__in=['Approved', 'Completed'],
    ).exclude(
        refund_account_number_encrypted=''
    ).select_related(
        'order', 'user'
    ).order_by('-created_at')

    pending_refunds = refunds.filter(
        refund_status='Pending'
    ).count()

    return render(request, 'manage_refunds.html', {
        'refunds': refunds,
        'pending_refunds': pending_refunds,
    })


@user_passes_test(lambda u: u.is_staff, login_url='/login/')
def refund_details(request, rr_id):
    rr = get_object_or_404(
        ReturnRequest.objects.select_related('order', 'user'),
        id=rr_id,
        request_type='Return',
        status__in=['Approved', 'Completed'],
    )

    if not rr.refund_account_number_encrypted:
        messages.error(request, 'Bank details are not available for this request.')
        return redirect('manage_refunds')

    # Record access without logging any sensitive bank information.
    logger.info(
        'Refund bank details accessed by staff user_id=%s for return_request_id=%s',
        request.user.id,
        rr.id,
    )

    try:
        bank_details = {
            'account_holder': decrypt_bank_value(
                rr.refund_account_holder_encrypted
            ),
            'account_number': decrypt_bank_value(
                rr.refund_account_number_encrypted
            ),
            'ifsc': decrypt_bank_value(
                rr.refund_ifsc_encrypted
            ),
            'bank_name': decrypt_bank_value(
                rr.refund_bank_name_encrypted
            ),
        }
    except Exception:
        logger.exception(
            'Unable to decrypt refund details for return_request_id=%s',
            rr.id,
        )
        messages.error(
            request,
            'Unable to read bank details. Please check the encryption configuration.'
        )
        return redirect('manage_refunds')

    return render(request, 'refund_details.html', {
        'rr': rr,
        'bank_details': bank_details,
    })


@user_passes_test(lambda u: u.is_staff, login_url='/login/')
def update_refund(request, rr_id):
    if request.method != 'POST':
        return redirect('manage_refunds')

    with transaction.atomic():
        rr = get_object_or_404(
            ReturnRequest.objects.select_for_update().select_related('order'),
            id=rr_id,
            request_type='Return',
            status__in=['Approved', 'Completed'],
        )

        if rr.refund_status == 'Completed':
            messages.error(request, 'This refund is already marked as completed.')
            return redirect('refund_details', rr_id=rr.id)

        new_status = request.POST.get('refund_status', '').strip()
        amount_input = request.POST.get('refund_amount', '').strip()
        transaction_reference = request.POST.get(
            'refund_transaction_reference', ''
        ).strip()
        admin_note = request.POST.get('refund_admin_note', '').strip()

        if new_status not in ['Pending', 'Processing', 'Completed', 'Failed']:
            messages.error(request, 'Invalid refund status.')
            return redirect('refund_details', rr_id=rr.id)

        refund_amount = None

        if amount_input:
            try:
                refund_amount = Decimal(amount_input).quantize(
                    Decimal('0.01'),
                    rounding=ROUND_HALF_UP,
                )
            except InvalidOperation:
                messages.error(request, 'Please enter a valid refund amount.')
                return redirect('refund_details', rr_id=rr.id)

            if refund_amount <= 0:
                messages.error(request, 'Refund amount must be greater than zero.')
                return redirect('refund_details', rr_id=rr.id)

            if refund_amount > rr.order.total:
                messages.error(
                    request,
                    'Refund amount cannot exceed the order total.'
                )
                return redirect('refund_details', rr_id=rr.id)

        if new_status in ['Processing', 'Completed'] and refund_amount is None:
            messages.error(
                request,
                'Enter the refund amount before processing the refund.'
            )
            return redirect('refund_details', rr_id=rr.id)

        if new_status == 'Completed':
            if not transaction_reference:
                messages.error(
                    request,
                    'Enter the bank/payment transaction reference before completing the refund.'
                )
                return redirect('refund_details', rr_id=rr.id)

            if len(transaction_reference) > 100:
                messages.error(
                    request,
                    'Transaction reference cannot exceed 100 characters.'
                )
                return redirect('refund_details', rr_id=rr.id)

        rr.refund_status = new_status
        rr.refund_amount = refund_amount
        rr.refund_transaction_reference = transaction_reference
        rr.refund_admin_note = admin_note
        rr.refund_updated_by = request.user
        rr.refund_processed_at = (
            timezone.now() if new_status == 'Completed' else None
        )

        rr.save(update_fields=[
            'refund_status',
            'refund_amount',
            'refund_transaction_reference',
            'refund_admin_note',
            'refund_updated_by',
            'refund_processed_at',
        ])

    messages.success(request, 'Refund information updated successfully.')
    return redirect('refund_details', rr_id=rr.id)



@user_passes_test(lambda u: u.is_staff, login_url='/login/')
def update_return_status(request, rr_id):
    rr = get_object_or_404(ReturnRequest, id=rr_id)

    if request.method == 'POST':
        new_status = request.POST.get('status')
        admin_note = request.POST.get('admin_note', '').strip()

        if new_status in [
            'Pending', 'Approved', 'Rejected', 'Completed'
        ]:
            old_status = rr.status
            rr.status = new_status
            rr.admin_note = admin_note

            # Automatically enable refund tracking when a return is approved.
            if (
                new_status == 'Approved'
                and rr.request_type == 'Return'
                and rr.refund_account_number_encrypted
                and rr.refund_status == 'Not Applicable'
            ):
                rr.refund_status = 'Pending'

            # Cancel an unprocessed pending refund if the return is rejected.
            if (
                new_status == 'Rejected'
                and rr.request_type == 'Return'
                and rr.refund_status == 'Pending'
            ):
                rr.refund_status = 'Not Applicable'

            rr.save()

            if new_status != old_status:
                recipient = rr.user.email

                if recipient:
                    send_return_email(
                        rr,
                        recipient,
                        event=new_status.lower()
                    )

    return redirect('manage_returns')



def send_return_email(rr, recipient, event='submitted'):
    divider = '─' * 42
    type_label = rr.request_type

    if event == 'submitted':
        subject = (
            f"🔄 {type_label} Request Received – "
            f"Glow Cart (Order #{rr.order.id})"
        )
        body = (
            f"Dear {rr.user.username},\n\n"
            f"We have received your {type_label} request "
            f"for Order #{rr.order.id}.\n\n"
            f"  Request Type : {type_label}\n"
            f"  Reason       : {rr.reason}\n"
            f"  Status       : Pending Review\n\n"
            f"Our team will review your request within 24-48 hours.\n\n"
        )

    elif event == 'approved':
        subject = (
            f"✅ {type_label} Request Approved – "
            f"Glow Cart (Order #{rr.order.id})"
        )
        body = (
            f"Dear {rr.user.username},\n\n"
            f"Great news! Your {type_label} request has been APPROVED. 🎉\n\n"
            f"  Order ID     : #{rr.order.id}\n"
            f"  Request Type : {type_label}\n"
            f"  Note         : "
            f"{rr.admin_note or 'Our team will contact you shortly.'}\n\n"
            f"Please wait for further instructions from our team.\n\n"
        )

    elif event == 'rejected':
        subject = (
            f"❌ {type_label} Request Update – "
            f"Glow Cart (Order #{rr.order.id})"
        )
        body = (
            f"Dear {rr.user.username},\n\n"
            f"We regret to inform you that your {type_label} request "
            f"could not be approved.\n\n"
            f"  Order ID : #{rr.order.id}\n"
            f"  Reason   : "
            f"{rr.admin_note or 'Does not meet return policy criteria.'}\n\n"
            f"For queries, contact us at glowcart0811@gmail.com\n\n"
        )

    elif event == 'completed':
        subject = (
            f"🎉 {type_label} Completed – "
            f"Glow Cart (Order #{rr.order.id})"
        )
        body = (
            f"Dear {rr.user.username},\n\n"
            f"Your {type_label} request has been completed successfully!\n\n"
            f"  Order ID : #{rr.order.id}\n"
            f"  Note     : {rr.admin_note or 'Process completed.'}\n\n"
            f"Thank you for your patience.\n\n"
        )

    else:
        return

    footer = (
        f"{divider}\n"
        f"Glow Cart ✨ Where Trends Light Up Your Life\n"
        f"Support: glowcart0811@gmail.com\n"
    )

    try:
        send_mail(
            subject=subject,
            message=body + footer,
            from_email=None,
            recipient_list=[recipient],
            fail_silently=False
        )
        logger.info(
            'Return email sent to %s event=%s',
            recipient, event
        )
    except Exception as e:
        logger.error('Return email failed: %s', str(e))


# ── Reviews ──────────────────────────────────────────────────

@login_required
def order_review(request):
    if request.method == 'POST':
        try:
            rating = int(request.POST.get('rating', 5))
        except (TypeError, ValueError):
            rating = 0

        comment = request.POST.get('comment', '').strip()
        skip = request.POST.get('skip', '')

        if not skip and comment and 1 <= rating <= 5:
            Review.objects.create(
                user=request.user,
                product=None,
                rating=rating,
                comment=comment,
                is_visible=True
            )

        return redirect('/success/')

    return render(request, 'order_review.html')


@login_required
def submit_review(request):
    if request.method == 'POST':
        try:
            rating = int(request.POST.get('rating', 5))
        except (TypeError, ValueError):
            rating = 0

        comment = request.POST.get('comment', '').strip()

        if comment and 1 <= rating <= 5:
            Review.objects.update_or_create(
                user=request.user,
                product=None,
                defaults={
                    'rating': rating,
                    'comment': comment,
                    'is_visible': True
                }
            )

    return redirect('/')


@login_required
def submit_product_review(request, id):
    product = get_object_or_404(
        Product,
        id=id,
        is_active=True
    )

    if request.method == 'POST':
        try:
            rating = int(request.POST.get('rating', 0))
        except (TypeError, ValueError):
            rating = 0

        comment = request.POST.get('comment', '').strip()

        if 1 <= rating <= 5 and comment:
            Review.objects.update_or_create(
                user=request.user,
                product=product,
                defaults={
                    'rating': rating,
                    'comment': comment,
                    'is_visible': True
                }
            )

    return redirect(f'/product/{product.id}/')


def reviews_api(request):
    reviews = Review.objects.filter(
        is_visible=True,
        product__isnull=True
    ).select_related('user').order_by('-created_at')[:10]

    data = [{
        'username': r.user.username,
        'rating': r.rating,
        'comment': r.comment,
        'date': r.created_at.strftime('%d %b %Y'),
    } for r in reviews]

    return JsonResponse({'reviews': data})


# ── User Dashboard ──────────────────────────────────────────

@login_required
def user_dashboard(request):
    orders = Order.objects.filter(
        user=request.user
    ).order_by('-id')

    parsed_orders = []

    for order in orders:
        try:
            items = json.loads(order.items)
        except (ValueError, TypeError):
            items = []

        parsed_orders.append({
            'id': order.id,
            'items': items,
            'total': order.total,
            'status': order.status,
            'address': order.address,
            'tracking_id': order.tracking_id,
        })

    return_requests = ReturnRequest.objects.filter(
        user=request.user
    ).select_related('order').order_by('-created_at')

    bank_details = BankDetails.objects.filter(
        user=request.user
    ).first()

    reviews = Review.objects.filter(
        user=request.user
    ).order_by('-created_at')

    total_spent = orders.aggregate(
        t=Sum('total')
    )['t'] or 0

    return render(request, 'user_dashboard.html', {
        'orders': parsed_orders,
        'return_requests': return_requests,
        'bank_details': bank_details,
        'reviews': reviews,
        'total_spent': total_spent,
        'total_orders': orders.count(),
    })


@login_required
def manage_bank_details(request):
    if request.method != 'POST':
        return redirect('user_dashboard')

    action = request.POST.get('action', 'save')

    bank_details = BankDetails.objects.filter(
        user=request.user
    ).first()

    if action == 'delete':
        if bank_details:
            bank_details.delete()
            messages.success(
                request,
                'Your saved bank details have been deleted.'
            )
        return redirect('user_dashboard')

    account_holder = request.POST.get(
        'account_holder', ''
    ).strip()

    account_number = request.POST.get(
        'account_number', ''
    ).strip().replace(' ', '').replace('-', '')

    confirm_account_number = request.POST.get(
        'confirm_account_number', ''
    ).strip().replace(' ', '').replace('-', '')

    ifsc = request.POST.get('ifsc', '').strip().upper()
    bank_name = request.POST.get('bank_name', '').strip()

    if not 2 <= len(account_holder) <= 100:
        messages.error(
            request,
            'Please enter a valid account holder name.'
        )
        return redirect('user_dashboard')

    if not re.fullmatch(r'[A-Z]{4}0[A-Z0-9]{6}', ifsc):
        messages.error(
            request,
            'Please enter a valid 11-character IFSC code.'
        )
        return redirect('user_dashboard')

    if bank_name and len(bank_name) > 100:
        messages.error(
            request,
            'Bank name must be 100 characters or fewer.'
        )
        return redirect('user_dashboard')

    if account_number:
        if not re.fullmatch(r'[0-9]{6,18}', account_number):
            messages.error(
                request,
                'Account number must contain 6 to 18 digits.'
            )
            return redirect('user_dashboard')

        if account_number != confirm_account_number:
            messages.error(
                request,
                'Account numbers do not match.'
            )
            return redirect('user_dashboard')

    elif not bank_details:
        messages.error(
            request,
            'Please enter your bank account number.'
        )
        return redirect('user_dashboard')

    encrypted_values = {
        'account_holder_encrypted': encrypt_bank_value(account_holder),
        'ifsc_encrypted': encrypt_bank_value(ifsc),
        'bank_name_encrypted': encrypt_bank_value(bank_name),
    }

    if account_number:
        encrypted_values['account_number_encrypted'] = (
            encrypt_bank_value(account_number)
        )
        encrypted_values['account_last4'] = account_number[-4:]

    if bank_details:
        for field, value in encrypted_values.items():
            setattr(bank_details, field, value)

        bank_details.save()

        messages.success(
            request,
            'Your bank details have been updated securely.'
        )
    else:
        BankDetails.objects.create(
            user=request.user,
            **encrypted_values
        )

        messages.success(
            request,
            'Your bank details have been saved securely.'
        )

    return redirect('user_dashboard')
