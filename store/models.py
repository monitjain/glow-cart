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


class SiteVisitor(models.Model):
    session_key  = models.CharField(max_length=40, unique=True)
    last_seen    = models.DateTimeField(auto_now=True)
    page         = models.CharField(max_length=200, default='/')
    is_logged_in = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.session_key} — {self.last_seen}"
