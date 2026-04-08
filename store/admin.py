from django.contrib import admin
from .models import Product, Order

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price')
    fields = ('name', 'price', 'image', 'description')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'total', 'status')
    list_editable = ('status',)
    fields = ('user', 'name', 'address', 'phone', 'items', 'total', 'status')
