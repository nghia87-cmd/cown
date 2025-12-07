"""
Payment URLs
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('packages', views.PaymentPackageViewSet, basename='payment-package')
router.register('payments', views.PaymentViewSet, basename='payment')
router.register('subscriptions', views.SubscriptionViewSet, basename='subscription')
router.register('invoices', views.InvoiceViewSet, basename='invoice')

urlpatterns = [
    path('', include(router.urls)),
    
    # Payment gateway callbacks
    path('vnpay/return/', views.vnpay_return, name='vnpay-return'),
    path('stripe/webhook/', views.stripe_webhook, name='stripe-webhook'),
]
