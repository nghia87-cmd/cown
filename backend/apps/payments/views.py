"""
Payment Views
"""

from django.shortcuts import redirect
from django.utils import timezone
from django.db.models import Sum, Count, Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from drf_spectacular.utils import extend_schema, OpenApiParameter
import uuid

from .models import PaymentPackage, Payment, Subscription, Invoice, PaymentWebhook
from .serializers import (
    PaymentPackageSerializer, PaymentSerializer, CreatePaymentSerializer,
    SubscriptionSerializer, InvoiceSerializer, PaymentStatsSerializer
)
from .vnpay import VNPayGateway
from .stripe_gateway import StripeGateway


class PaymentPackageViewSet(viewsets.ReadOnlyModelViewSet):
    """Payment package endpoints"""
    
    queryset = PaymentPackage.objects.filter(is_active=True)
    serializer_class = PaymentPackageSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        package_type = self.request.query_params.get('package_type')
        if package_type:
            queryset = queryset.filter(package_type=package_type)
        return queryset
    
    @action(detail=False, methods=['get'])
    def popular(self, request):
        """Get popular packages"""
        packages = self.queryset.filter(is_popular=True)
        serializer = self.get_serializer(packages, many=True)
        return Response(serializer.data)


class PaymentViewSet(viewsets.ModelViewSet):
    """Payment endpoints"""
    
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return self.queryset
        return self.queryset.filter(user=user)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CreatePaymentSerializer
        return PaymentSerializer
    
    @extend_schema(
        request=CreatePaymentSerializer,
        responses={200: {'type': 'object', 'properties': {'payment_url': {'type': 'string'}}}}
    )
    def create(self, request):
        """Create payment and get payment URL"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Get package
        package = PaymentPackage.objects.get(id=serializer.validated_data['package_id'])
        
        # Create payment record
        order_id = f"ORD{uuid.uuid4().hex[:12].upper()}"
        payment = Payment.objects.create(
            user=request.user,
            company_id=serializer.validated_data.get('company_id'),
            package=package,
            order_id=order_id,
            amount=package.final_price,
            currency=package.currency,
            payment_method=serializer.validated_data['payment_method'],
            status='PENDING',
            expires_at=timezone.now() + timezone.timedelta(minutes=15)
        )
        
        # Generate payment URL based on method
        payment_method = serializer.validated_data['payment_method']
        payment_url = None
        client_secret = None
        
        if payment_method == 'VNPAY':
            vnpay = VNPayGateway()
            payment_url = vnpay.create_payment_url(
                order_id=payment.order_id,
                amount=payment.amount,
                order_desc=f"{package.name} - {request.user.email}",
                bank_code=serializer.validated_data.get('bank_code')
            )
        
        elif payment_method == 'STRIPE':
            stripe_gateway = StripeGateway()
            
            # Create or get Stripe customer
            customer = stripe_gateway.create_customer(
                email=request.user.email,
                name=request.user.get_full_name(),
                metadata={'user_id': str(request.user.id)}
            )
            
            if 'error' in customer:
                payment.status = 'FAILED'
                payment.gateway_response = customer
                payment.save()
                return Response(
                    {'error': customer.get('error', 'Customer creation failed')},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create checkout session
            success_url = serializer.validated_data.get('return_url', f"{request.scheme}://{request.get_host()}/payment/success?session_id={{CHECKOUT_SESSION_ID}}")
            cancel_url = f"{request.scheme}://{request.get_host()}/payment/cancelled"
            
            session = stripe_gateway.create_checkout_session(
                line_items=[{
                    'price_data': {
                        'currency': package.currency.lower(),
                        'product_data': {
                            'name': package.name,
                            'description': package.description,
                        },
                        'unit_amount': int(package.final_price * 100) if package.currency == 'USD' else int(package.final_price),
                    },
                    'quantity': 1,
                }],
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    'order_id': payment.order_id,
                    'user_id': str(request.user.id),
                    'package_id': str(package.id)
                }
            )
            
            if 'error' in session:
                payment.status = 'FAILED'
                payment.gateway_response = session
                payment.save()
                return Response(
                    {'error': session.get('error', 'Session creation failed')},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            payment_url = session.url
            payment.transaction_id = session.id
            payment.gateway_response = {'session_id': session.id, 'customer_id': customer.id}
            payment.save()
        
        return Response({
            'payment_id': payment.id,
            'order_id': payment.order_id,
            'payment_url': payment_url,
            'expires_at': payment.expires_at
        })
    
    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """Check payment status"""
        payment = self.get_object()
        return Response({
            'order_id': payment.order_id,
            'status': payment.status,
            'amount': payment.amount,
            'paid_at': payment.paid_at,
            'transaction_id': payment.transaction_id
        })
    
    @action(detail=False, methods=['get'], permission_classes=[IsAdminUser])
    def statistics(self, request):
        """Get payment statistics"""
        from django.db.models.functions import TruncMonth
        
        payments = Payment.objects.filter(status='COMPLETED')
        
        stats = {
            'total_revenue': payments.aggregate(Sum('amount'))['amount__sum'] or 0,
            'total_payments': Payment.objects.count(),
            'completed_payments': payments.count(),
            'pending_payments': Payment.objects.filter(status='PENDING').count(),
            'active_subscriptions': Subscription.objects.filter(status='ACTIVE').count(),
        }
        
        # Revenue by package
        revenue_by_package = payments.values('package__name').annotate(
            total=Sum('amount')
        ).order_by('-total')
        stats['revenue_by_package'] = {item['package__name']: float(item['total']) for item in revenue_by_package}
        
        # Revenue by month
        revenue_by_month = payments.annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            total=Sum('amount')
        ).order_by('month')
        stats['revenue_by_month'] = {str(item['month'].date()): float(item['total']) for item in revenue_by_month}
        
        serializer = PaymentStatsSerializer(stats)
        return Response(serializer.data)


class SubscriptionViewSet(viewsets.ReadOnlyModelViewSet):
    """Subscription endpoints"""
    
    queryset = Subscription.objects.all()
    serializer_class = SubscriptionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return self.queryset
        return self.queryset.filter(user=user)
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get active subscriptions"""
        subscriptions = self.get_queryset().filter(
            status='ACTIVE',
            end_date__gte=timezone.now()
        )
        serializer = self.get_serializer(subscriptions, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel subscription"""
        subscription = self.get_object()
        
        if subscription.user != request.user and not request.user.is_staff:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        subscription.status = 'CANCELLED'
        subscription.cancelled_at = timezone.now()
        subscription.auto_renew = False
        subscription.save()
        
        serializer = self.get_serializer(subscription)
        return Response(serializer.data)


class InvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    """Invoice endpoints"""
    
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return self.queryset
        return self.queryset.filter(payment__user=user)
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Download invoice PDF (placeholder)"""
        invoice = self.get_object()
        # TODO: Generate PDF invoice
        return Response({
            'message': 'PDF generation not implemented yet',
            'invoice_number': invoice.invoice_number
        })


@extend_schema(exclude=True)
def stripe_webhook(request):
    """Stripe webhook handler"""
    import json
    from django.http import HttpResponse
    
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    
    # Log webhook
    PaymentWebhook.objects.create(
        gateway='STRIPE',
        method='POST',
        path=request.path,
        headers=dict(request.headers),
        body=json.loads(payload) if payload else {}
    )
    
    # Validate webhook
    stripe_gateway = StripeGateway()
    is_valid, event = stripe_gateway.validate_webhook(payload, sig_header)
    
    if not is_valid:
        return HttpResponse(status=400)
    
    # Handle different event types
    if event.type == 'checkout.session.completed':
        session = event.data.object
        order_id = session.metadata.get('order_id')
        
        try:
            payment = Payment.objects.get(order_id=order_id)
            payment.mark_as_paid(
                transaction_id=session.id,
                gateway_response=dict(session)
            )
        except Payment.DoesNotExist:
            pass
    
    elif event.type == 'payment_intent.succeeded':
        payment_intent = event.data.object
        # Handle successful payment
        pass
    
    elif event.type == 'payment_intent.payment_failed':
        payment_intent = event.data.object
        # Handle failed payment
        pass
    
    return HttpResponse(status=200)


@extend_schema(exclude=True)
def vnpay_return(request):
    """VNPay payment return URL"""
    # Get response data
    response_data = dict(request.GET)
    response_data = {k: v[0] if isinstance(v, list) else v for k, v in response_data.items()}
    
    # Log webhook
    PaymentWebhook.objects.create(
        gateway='VNPAY',
        method='GET',
        path=request.path,
        headers=dict(request.headers),
        query_params=response_data
    )
    
    # Validate response
    vnpay = VNPayGateway()
    is_valid, message = vnpay.validate_response(response_data)
    
    if is_valid:
        # Get transaction info
        trans_info = vnpay.get_transaction_info(response_data)
        
        # Update payment
        try:
            payment = Payment.objects.get(order_id=trans_info['order_id'])
            payment.mark_as_paid(
                transaction_id=trans_info['transaction_id'],
                gateway_response=response_data
            )
            payment.bank_code = trans_info.get('bank_code', '')
            payment.card_type = trans_info.get('card_type', '')
            payment.save()
            
            # Redirect to success page
            return redirect(f"/payment/success?order_id={payment.order_id}")
        except Payment.DoesNotExist:
            pass
    
    # Redirect to failure page
    return redirect(f"/payment/failed?message={message}")


