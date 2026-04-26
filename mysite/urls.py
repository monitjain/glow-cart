from django.contrib import admin
from django.urls import path, re_path
from store import views
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home),
    path('cart/', views.cart),
    path('product/<int:id>/', views.product_detail, name='product_detail'),
    path('checkout/', views.checkout, name='checkout'),
    path('success/', views.success, name='success'),
    path('policy/', views.policy, name='policy'),
    path('faq/', views.faq, name='faq'),
    path('login/', auth_views.LoginView.as_view(template_name='login.html', next_page='/'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
    path('signup/', views.signup, name='signup'),
    path('orders/', views.my_orders, name='orders'),
    path('my-dashboard/', views.user_dashboard, name='user_dashboard'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/live/', views.live_visitors_api, name='live_visitors_api'),
    path('dashboard/orders/', views.manage_orders, name='manage_orders'),
    path('dashboard/orders/<int:order_id>/status/', views.update_order_status, name='update_order_status'),
    path('dashboard/orders/<int:order_id>/shiprocket/', views.push_to_shiprocket, name='push_to_shiprocket'),
    path('dashboard/products/', views.manage_products, name='manage_products'),
    path('dashboard/products/<int:product_id>/delete/', views.delete_product, name='delete_product'),
    path('dashboard/customers/', views.manage_customers, name='manage_customers'),
    path('orders/return/<int:order_id>/', views.submit_return_request, name='submit_return_request'),
    path('dashboard/returns/', views.manage_returns, name='manage_returns'),
    path('dashboard/returns/<int:rr_id>/status/', views.update_return_status, name='update_return_status'),
    path('review/submit/', views.submit_review, name='submit_review'),
    path('review/order/', views.order_review, name='order_review'),
    path('api/reviews/', views.reviews_api, name='reviews_api'),
    # Always serve media files (works in both dev and production)
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]

# Serve static files in development only
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.BASE_DIR / 'store/static')
