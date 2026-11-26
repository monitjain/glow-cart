
from django.contrib import admin
from .models import Product, ProductImage, Order


class StockStatusFilter(admin.SimpleListFilter):
    title = 'Stock status'
    parameter_name = 'stock_status'

    def lookups(self, request, model_admin):
        return [
            ('in_stock', 'In Stock'),
            ('out_of_stock', 'Out of Stock'),
            ('unknown', 'Stock Unknown'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'in_stock':
            return queryset.filter(stock__gt=0)
        if self.value() == 'out_of_stock':
            return queryset.filter(stock=0)
        if self.value() == 'unknown':
            return queryset.filter(stock__isnull=True)
        return queryset


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 4
    fields = ('image', 'alt_text')
    verbose_name = 'Additional Product Image'
    verbose_name_plural = 'Additional Product Images'


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'sku', 'stock', 'is_active')
    list_editable = ('price', 'sku', 'stock', 'is_active')
    list_filter = ('is_active', StockStatusFilter)
    search_fields = ('name', 'sku')
    ordering = ('name',)
    list_per_page = 25

    fields = ('name', 'price', 'sku', 'stock', 'is_active', 'image', 'description')
    inlines = [ProductImageInline]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'total', 'status')
    list_editable = ('status',)
    fields = ('user', 'name', 'address', 'phone', 'items', 'total', 'status')
