from django.db import models
from django.contrib.auth.models import User



class Product(models.Model):
    name = models.CharField(max_length=100)
    price = models.IntegerField()
    image = models.ImageField(upload_to='images/')
    description = models.TextField(blank=True, default='')

    # Inventory and product management
    sku = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True
    )
    stock = models.PositiveIntegerField(
        null=True,
        blank=True,
        default=None
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name



class Order(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    STATUS_CHOICES = [
    ('Pending',          'Pending'),
    ('Confirmed',        'Confirmed'),
    ('Accepted',         'Accepted'),
    ('Pickup Scheduled', 'Pickup Scheduled'),
    ('Shipped',          'Shipped'),
    ('Delivered',        'Delivered'),
]

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    name        = models.CharField(max_length=100)
    address     = models.TextField()
    street      = models.CharField(max_length=200, blank=True, default='')
    city        = models.CharField(max_length=100, blank=True, default='')
    state       = models.CharField(max_length=100, blank=True, default='')
    pincode     = models.CharField(max_length=10,  blank=True, default='')
    phone       = models.CharField(max_length=15)
    email       = models.EmailField(blank=True, default='')
    items       = models.TextField()
    total       = models.IntegerField()
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Confirmed')
    tracking_id = models.CharField(max_length=100, blank=True, default='')
    def __str__(self):
        return f"Order #{self.id} — {self.name}"


class ReturnRequest(models.Model):
    TYPE_CHOICES = [
        ('Return',   'Return'),
        ('Exchange', 'Exchange'),
        ('Replace',  'Replace'),
    ]
    STATUS_CHOICES = [
        ('Pending',   'Pending'),
        ('Approved',  'Approved'),
        ('Rejected',  'Rejected'),
        ('Completed', 'Completed'),
    ]
    order       = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='return_requests')
    user        = models.ForeignKey(User, on_delete=models.CASCADE)
    request_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    reason      = models.TextField()
    status      = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Pending')
    created_at  = models.DateTimeField(auto_now_add=True)
    admin_note  = models.TextField(blank=True, default='')
        # Encrypted snapshot of the refund destination selected for this request
    refund_account_holder_encrypted = models.TextField(blank=True, default='')
    refund_account_number_encrypted = models.TextField(blank=True, default='')
    refund_ifsc_encrypted = models.TextField(blank=True, default='')
    refund_bank_name_encrypted = models.TextField(blank=True, default='')
    refund_account_last4 = models.CharField(max_length=4, blank=True, default='')
        # Separate refund payment tracking
    REFUND_STATUS_CHOICES = [
        ('Not Applicable', 'Not Applicable'),
        ('Pending', 'Pending'),
        ('Processing', 'Processing'),
        ('Completed', 'Completed'),
        ('Failed', 'Failed'),
    ]

    refund_status = models.CharField(
        max_length=20,
        choices=REFUND_STATUS_CHOICES,
        default='Not Applicable'
    )

    refund_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    refund_transaction_reference = models.CharField(
        max_length=100,
        blank=True,
        default=''
    )

    refund_processed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    refund_admin_note = models.TextField(
        blank=True,
        default=''
    )

    refund_updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_refunds'
    )

    def __str__(self):
        return f"{self.request_type} for Order #{self.order.id} — {self.status}"


class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='reviews',
        null=True,
        blank=True
    )
    rating = models.IntegerField(default=5)  # 1-5
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_visible = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username} - {self.rating} stars"

class SiteVisitor(models.Model):
    session_key  = models.CharField(max_length=40, unique=True)
    last_seen    = models.DateTimeField(auto_now=True)
    page         = models.CharField(max_length=200, default='/')
    is_logged_in = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.session_key} — {self.last_seen}"
class BankDetails(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='bank_details'
    )

    # Sensitive information is stored only as encrypted text
    account_holder_encrypted = models.TextField()
    account_number_encrypted = models.TextField()
    ifsc_encrypted = models.TextField()
    bank_name_encrypted = models.TextField(blank=True, default='')

    # Safe to use for displaying a masked account number
    account_last4 = models.CharField(max_length=4)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Bank details for user #{self.user_id}"        
