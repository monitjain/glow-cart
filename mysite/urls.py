from django.contrib import admin
from django.urls import path
from store import views
from django.contrib.auth import views as auth_views

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home),
    path('cart/', views.cart),
    path('product/<int:id>/', views.product_detail, name='product_detail'),
    path('checkout/', views.checkout, name='checkout'),
    path('success/', views.success, name='success'),
    path('login/', auth_views.LoginView.as_view(template_name='login.html', next_page='/'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
    path('signup/', views.signup, name='signup'),
    path('orders/', views.my_orders, name='orders'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/orders/', views.manage_orders, name='manage_orders'),
    path('dashboard/orders/<int:order_id>/status/', views.update_order_status, name='update_order_status'),
    path('dashboard/products/', views.manage_products, name='manage_products'),
    path('dashboard/products/<int:product_id>/delete/', views.delete_product, name='delete_product'),
    path('dashboard/customers/', views.manage_customers, name='manage_customers'),
]

# For media and static files
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.BASE_DIR / 'store/static')