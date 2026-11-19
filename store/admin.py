
from django.contrib import admin
from .models import Product, Order


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'sku', 'stock', 'is_active')
    list_editable = ('price', 'sku', 'stock', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'sku')
    ordering = ('name',)

    fields = ('name', 'price', 'sku', 'stock', 'is_active', 'image', 'description')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'total', 'status')
    list_editable = ('status',)
    fields = ('user', 'name', 'address', 'phone', 'items', 'total', 'status')
