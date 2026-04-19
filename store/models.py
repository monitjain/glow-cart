from django.db import models
from django.contrib.auth.models import User


class Product(models.Model):
    name        = models.CharField(max_length=100)
    price       = models.IntegerField()
    image       = models.ImageField(upload_to='images/')
    description = models.TextField(blank=True, default='')

    def __str__(self):
        return self.name


class Order(models.Model):
    STATUS_CHOICES = [
        ('Pending',   'Pending'),
        ('Confirmed', 'Confirmed'),
        ('Shipped',   'Shipped'),
        ('Delivered', 'Delivered'),
    ]
    user        = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    name        = models.CharField(max_length=100)
    address     = models.TextField()
    phone       = models.CharField(max_length=15)
    items       = models.TextField()
    total       = models.IntegerField()
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
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

    def __str__(self):
        return f"{self.request_type} for Order #{self.order.id} — {self.status}"


class Review(models.Model):
    user       = models.ForeignKey(User, on_delete=models.CASCADE)
    rating     = models.IntegerField(default=5)  # 1-5
    comment    = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_visible = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username} — {self.rating}★"


class SiteVisitor(models.Model):
    session_key  = models.CharField(max_length=40, unique=True)
    last_seen    = models.DateTimeField(auto_now=True)
    page         = models.CharField(max_length=200, default='/')
    is_logged_in = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.session_key} — {self.last_seen}"
