import json
import logging
from datetime import timedelta
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum
from django.core.mail import send_mail
from django.http import JsonResponse
from django.utils import timezone
from .models import Product, Order, SiteVisitor, ReturnRequest, Review


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
        xpressbees_url = f"https://www.xpressbees.com/shipment/tracking?awb={tracking_id}" if tracking_id else ""
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
        logger.info('Email sent to %s for order #%s event=%s', recipient, order.id, event)
    except Exception as e:
        logger.error('Email failed for order #%s event=%s: %s', order.id, event, str(e))


# ── Visitor tracking helper ───────────────────────────────────
def track_visitor(request):
    if not request.session.session_key:
        request.session.create()
    SiteVisitor.objects.update_or_create(
        session_key=request.session.session_key,
        defaults={
            'page':         request.path,
            'is_logged_in': request.user.is_authenticated,
        }
    )


# ── Public views ──────────────────────────────────────────────
def home(request):
    track_visitor(request)
    products = Product.objects.all()
    return render(request, 'home.html', {'products': products})


def cart(request):
    track_visitor(request)
    return render(request, 'cart.html')


def product_detail(request, id):
    track_visitor(request)
    product = get_object_or_404(Product, id=id)
    return render(request, 'product.html', {'product': product})


@login_required
def checkout(request):
    track_visitor(request)
    if request.method == 'POST':
        name     = request.POST.get('name')
        street   = request.POST.get('street', '').strip()
        city     = request.POST.get('city', '').strip()
        state    = request.POST.get('state', '').strip()
        pincode  = request.POST.get('pincode', '').strip()
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

        recipient = request.user.email or email
        if recipient:
            send_order_email(order, recipient, event='confirmed')

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
            'id':          order.id,
            'items':       items,
            'address':     order.address,
            'phone':       order.phone,
            'total':       order.total,
            'status':      order.status,
            'tracking_id': order.tracking_id,
        })
    return render(request, 'orders.html', {'orders': orders})


# ── Admin views ───────────────────────────────────────────────
@user_passes_test(lambda u: u.is_staff, login_url='/login/')
def dashboard(request):
    # Clean up stale visitors (inactive > 5 minutes)
    cutoff = timezone.now() - timedelta(minutes=5)
    SiteVisitor.objects.filter(last_seen__lt=cutoff).delete()

    live_count    = SiteVisitor.objects.count()
    live_visitors = SiteVisitor.objects.order_by('-last_seen')[:20]

    total_orders   = Order.objects.count()
    total_revenue  = Order.objects.aggregate(rev=Sum('total'))['rev'] or 0
    total_users    = User.objects.count()
    total_products = Product.objects.count()
    status_counts  = {
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
        'live_count':     live_count,
        'live_visitors':  live_visitors,
    })


@user_passes_test(lambda u: u.is_staff, login_url='/login/')
def live_visitors_api(request):
    """JSON endpoint polled every 30s by dashboard JS."""
    cutoff = timezone.now() - timedelta(minutes=5)
    SiteVisitor.objects.filter(last_seen__lt=cutoff).delete()
    visitors = list(SiteVisitor.objects.values('page', 'is_logged_in', 'last_seen'))
    for v in visitors:
        v['last_seen'] = v['last_seen'].strftime('%H:%M:%S')
    return JsonResponse({'count': len(visitors), 'visitors': visitors})


@user_passes_test(lambda u: u.is_staff, login_url='/login/')
def manage_orders(request):
    all_orders = Order.objects.select_related('user').order_by('-id')
    return render(request, 'manage_orders.html', {'orders': all_orders})


@user_passes_test(lambda u: u.is_staff, login_url='/login/')
def update_order_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if request.method == 'POST':
        new_status  = request.POST.get('status')
        tracking_id = request.POST.get('tracking_id', '').strip()

        if new_status in ['Pending', 'Confirmed', 'Shipped', 'Delivered']:
            old_status  = order.status
            order.status = new_status
            if tracking_id:
                order.tracking_id = tracking_id
            order.save()

            # Send email only when status actually changes
            if new_status != old_status:
                recipient = order.user.email if order.user else ''
                if recipient:
                    send_order_email(
                        order, recipient,
                        event=new_status.lower(),
                        tracking_id=order.tracking_id
                    )

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


# ── Return / Exchange / Replace ─────────────────────────────────
@login_required
def submit_return_request(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    if order.status != 'Delivered':
        return redirect('orders')
    if request.method == 'POST':
        request_type = request.POST.get('request_type')
        reason       = request.POST.get('reason', '').strip()
        if request_type in ['Return', 'Exchange', 'Replace'] and reason:
            rr = ReturnRequest.objects.create(
                order=order, user=request.user,
                request_type=request_type, reason=reason
            )
            recipient = request.user.email
            if recipient:
                send_return_email(rr, recipient, event='submitted')
            return redirect('orders')
    return render(request, 'return_request.html', {'order': order})


@user_passes_test(lambda u: u.is_staff, login_url='/login/')
def manage_returns(request):
    requests = ReturnRequest.objects.select_related('order', 'user').order_by('-created_at')
    return render(request, 'manage_returns.html', {'requests': requests})


@user_passes_test(lambda u: u.is_staff, login_url='/login/')
def update_return_status(request, rr_id):
    rr = get_object_or_404(ReturnRequest, id=rr_id)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        admin_note = request.POST.get('admin_note', '').strip()
        if new_status in ['Pending', 'Approved', 'Rejected', 'Completed']:
            old_status    = rr.status
            rr.status     = new_status
            rr.admin_note = admin_note
            rr.save()
            if new_status != old_status:
                recipient = rr.user.email
                if recipient:
                    send_return_email(rr, recipient, event=new_status.lower())
    return redirect('manage_returns')


def send_return_email(rr, recipient, event='submitted'):
    divider = '─' * 42
    type_label = rr.request_type
    if event == 'submitted':
        subject = f"🔄 {type_label} Request Received – Glow Cart (Order #{rr.order.id})"
        body = (
            f"Dear {rr.user.username},\n\n"
            f"We have received your {type_label} request for Order #{rr.order.id}.\n\n"
            f"  Request Type : {type_label}\n"
            f"  Reason       : {rr.reason}\n"
            f"  Status       : Pending Review\n\n"
            f"Our team will review your request within 24-48 hours.\n\n"
        )
    elif event == 'approved':
        subject = f"✅ {type_label} Request Approved – Glow Cart (Order #{rr.order.id})"
        body = (
            f"Dear {rr.user.username},\n\n"
            f"Great news! Your {type_label} request has been APPROVED. 🎉\n\n"
            f"  Order ID     : #{rr.order.id}\n"
            f"  Request Type : {type_label}\n"
            f"  Note         : {rr.admin_note or 'Our team will contact you shortly.'}\n\n"
            f"Please wait for further instructions from our team.\n\n"
        )
    elif event == 'rejected':
        subject = f"❌ {type_label} Request Update – Glow Cart (Order #{rr.order.id})"
        body = (
            f"Dear {rr.user.username},\n\n"
            f"We regret to inform you that your {type_label} request could not be approved.\n\n"
            f"  Order ID : #{rr.order.id}\n"
            f"  Reason   : {rr.admin_note or 'Does not meet return policy criteria.'}\n\n"
            f"For queries, contact us at glowcart0811@gmail.com\n\n"
        )
    elif event == 'completed':
        subject = f"🎉 {type_label} Completed – Glow Cart (Order #{rr.order.id})"
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
        send_mail(subject=subject, message=body + footer,
                  from_email=None, recipient_list=[recipient], fail_silently=False)
        logger.info('Return email sent to %s event=%s', recipient, event)
    except Exception as e:
        logger.error('Return email failed: %s', str(e))


# ── Reviews ──────────────────────────────────────────────────
@login_required
def submit_review(request):
    if request.method == 'POST':
        rating  = int(request.POST.get('rating', 5))
        comment = request.POST.get('comment', '').strip()
        if comment and 1 <= rating <= 5:
            Review.objects.update_or_create(
                user=request.user,
                defaults={'rating': rating, 'comment': comment, 'is_visible': True}
            )
    return redirect('/')


def reviews_api(request):
    reviews = Review.objects.filter(is_visible=True).select_related('user').order_by('-created_at')[:10]
    data = [{
        'username': r.user.username,
        'rating':   r.rating,
        'comment':  r.comment,
        'date':     r.created_at.strftime('%d %b %Y'),
    } for r in reviews]
    return JsonResponse({'reviews': data})
