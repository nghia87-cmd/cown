"""
Payment Serializers
"""

from rest_framework import serializers
from .models import PaymentPackage, Payment, Subscription, Invoice


class PaymentPackageSerializer(serializers.ModelSerializer):
    """Payment package serializer"""
    
    final_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = PaymentPackage
        fields = [
            'id', 'name', 'code', 'description', 'package_type',
            'price', 'currency', 'discount_price', 'final_price',
            'duration_days', 'job_posts_quota', 'featured_quota',
            'urgent_quota', 'cv_views_quota', 'features',
            'is_active', 'is_popular', 'display_order',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PaymentSerializer(serializers.ModelSerializer):
    """Payment serializer"""
    
    package_details = PaymentPackageSerializer(source='package', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    company_name = serializers.CharField(source='company.name', read_only=True, allow_null=True)
    
    class Meta:
        model = Payment
        fields = [
            'id', 'user', 'user_email', 'company', 'company_name',
            'package', 'package_details', 'order_id', 'amount', 'currency',
            'payment_method', 'status', 'transaction_id',
            'bank_code', 'card_type', 'paid_at', 'expires_at',
            'note', 'admin_note', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'order_id', 'status', 'transaction_id',
            'paid_at', 'created_at', 'updated_at'
        ]


class CreatePaymentSerializer(serializers.Serializer):
    """Serializer for creating payment"""
    
    package_id = serializers.UUIDField(required=True)
    company_id = serializers.UUIDField(required=False, allow_null=True)
    payment_method = serializers.ChoiceField(
        choices=['VNPAY', 'STRIPE', 'BANK_TRANSFER'],
        default='VNPAY'
    )
    bank_code = serializers.CharField(required=False, allow_blank=True)
    return_url = serializers.URLField(required=False)
    
    def validate_package_id(self, value):
        """Validate package exists and is active"""
        try:
            package = PaymentPackage.objects.get(id=value, is_active=True)
        except PaymentPackage.DoesNotExist:
            raise serializers.ValidationError("Package not found or inactive")
        return value
    
    def validate_company_id(self, value):
        """Validate company exists and belongs to user"""
        if value:
            from apps.companies.models import Company
            user = self.context['request'].user
            try:
                company = Company.objects.get(id=value, owner=user)
            except Company.DoesNotExist:
                raise serializers.ValidationError("Company not found or you don't have permission")
        return value


class SubscriptionSerializer(serializers.ModelSerializer):
    """Subscription serializer"""
    
    package_details = PaymentPackageSerializer(source='package', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    company_name = serializers.CharField(source='company.name', read_only=True, allow_null=True)
    is_active_status = serializers.BooleanField(source='is_active', read_only=True)
    days_remaining = serializers.SerializerMethodField()
    
    class Meta:
        model = Subscription
        fields = [
            'id', 'user', 'user_email', 'company', 'company_name',
            'package', 'package_details', 'payment',
            'start_date', 'end_date', 'days_remaining',
            'job_posts_remaining', 'featured_remaining',
            'urgent_remaining', 'cv_views_remaining',
            'status', 'is_active_status', 'auto_renew',
            'created_at', 'updated_at', 'cancelled_at'
        ]
        read_only_fields = [
            'id', 'user', 'payment', 'start_date', 'end_date',
            'job_posts_remaining', 'featured_remaining',
            'urgent_remaining', 'cv_views_remaining',
            'status', 'created_at', 'updated_at', 'cancelled_at'
        ]
    
    def get_days_remaining(self, obj):
        """Calculate days remaining"""
        from django.utils import timezone
        if obj.end_date > timezone.now():
            delta = obj.end_date - timezone.now()
            return delta.days
        return 0


class InvoiceSerializer(serializers.ModelSerializer):
    """Invoice serializer"""
    
    payment_details = PaymentSerializer(source='payment', read_only=True)
    
    class Meta:
        model = Invoice
        fields = [
            'id', 'payment', 'payment_details', 'invoice_number',
            'issue_date', 'buyer_name', 'buyer_email', 'buyer_phone',
            'buyer_address', 'buyer_tax_code', 'items',
            'subtotal', 'tax_amount', 'total_amount',
            'is_sent', 'sent_at', 'note',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'invoice_number', 'issue_date',
            'created_at', 'updated_at'
        ]


class PaymentStatsSerializer(serializers.Serializer):
    """Payment statistics serializer"""
    
    total_revenue = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_payments = serializers.IntegerField()
    completed_payments = serializers.IntegerField()
    pending_payments = serializers.IntegerField()
    active_subscriptions = serializers.IntegerField()
    revenue_by_package = serializers.DictField()
    revenue_by_month = serializers.DictField()
