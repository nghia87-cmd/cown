"""
Custom exceptions for payment processing
Provides specific error types for better error handling and logging
"""


class PaymentError(Exception):
    """Base exception for all payment-related errors"""
    
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        self.message = message
        self.error_code = error_code or 'PAYMENT_ERROR'
        self.details = details or {}
        super().__init__(self.message)


class PaymentGatewayError(PaymentError):
    """
    Error from payment gateway (VNPay, Stripe, etc.)
    
    Usage:
        raise PaymentGatewayError(
            message="VNPay signature verification failed",
            error_code="VNPAY_INVALID_SIGNATURE",
            details={'response_code': '97'}
        )
    """
    
    def __init__(self, message: str, gateway: str = None, error_code: str = None, details: dict = None):
        self.gateway = gateway
        super().__init__(
            message=message,
            error_code=error_code or 'GATEWAY_ERROR',
            details=details or {}
        )


class PaymentValidationError(PaymentError):
    """
    Payment data validation error
    
    Usage:
        raise PaymentValidationError(
            message="Invalid payment amount",
            error_code="INVALID_AMOUNT"
        )
    """
    
    def __init__(self, message: str, field: str = None, error_code: str = None):
        self.field = field
        super().__init__(
            message=message,
            error_code=error_code or 'VALIDATION_ERROR',
            details={'field': field} if field else {}
        )


class PaymentProcessingError(PaymentError):
    """
    Error during payment processing (database, logic, etc.)
    
    Usage:
        raise PaymentProcessingError(
            message="Failed to create subscription after payment",
            error_code="SUBSCRIPTION_CREATION_FAILED"
        )
    """
    pass


class SubscriptionError(Exception):
    """Base exception for subscription-related errors"""
    
    def __init__(self, message: str, error_code: str = None):
        self.message = message
        self.error_code = error_code or 'SUBSCRIPTION_ERROR'
        super().__init__(self.message)


class SubscriptionQuotaExceeded(SubscriptionError):
    """
    User exceeded their subscription quota
    
    Usage:
        raise SubscriptionQuotaExceeded(
            quota_type="job_posts",
            current=10,
            limit=10
        )
    """
    
    def __init__(self, quota_type: str, current: int, limit: int):
        self.quota_type = quota_type
        self.current = current
        self.limit = limit
        message = f"{quota_type} quota exceeded: {current}/{limit}"
        super().__init__(message=message, error_code='QUOTA_EXCEEDED')


class SubscriptionNotFound(SubscriptionError):
    """
    No active subscription found for user
    
    Usage:
        raise SubscriptionNotFound(user_id=user.id)
    """
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        message = f"No active subscription found for user {user_id}"
        super().__init__(message=message, error_code='NO_SUBSCRIPTION')


class SubscriptionExpired(SubscriptionError):
    """
    User's subscription has expired
    
    Usage:
        raise SubscriptionExpired(subscription_id=sub.id, expired_at=sub.end_date)
    """
    
    def __init__(self, subscription_id: int, expired_at):
        self.subscription_id = subscription_id
        self.expired_at = expired_at
        message = f"Subscription {subscription_id} expired on {expired_at}"
        super().__init__(message=message, error_code='SUBSCRIPTION_EXPIRED')


class InvalidPackageError(PaymentError):
    """
    Invalid subscription package selected
    
    Usage:
        raise InvalidPackageError(
            package_code="INVALID_CODE",
            message="Package not found or inactive"
        )
    """
    
    def __init__(self, package_code: str, message: str = None):
        self.package_code = package_code
        error_message = message or f"Invalid package: {package_code}"
        super().__init__(
            message=error_message,
            error_code='INVALID_PACKAGE',
            details={'package_code': package_code}
        )


class WebhookVerificationError(PaymentGatewayError):
    """
    Webhook signature verification failed
    
    Usage:
        raise WebhookVerificationError(
            gateway="stripe",
            message="Invalid webhook signature"
        )
    """
    
    def __init__(self, gateway: str, message: str = None):
        error_message = message or f"{gateway} webhook verification failed"
        super().__init__(
            message=error_message,
            gateway=gateway,
            error_code='WEBHOOK_VERIFICATION_FAILED'
        )


class DuplicatePaymentError(PaymentError):
    """
    Payment already processed (idempotency check)
    
    Usage:
        raise DuplicatePaymentError(
            payment_id=payment.id,
            transaction_id=vnpay_txn_ref
        )
    """
    
    def __init__(self, payment_id: str = None, transaction_id: str = None):
        self.payment_id = payment_id
        self.transaction_id = transaction_id
        message = "Payment already processed"
        if transaction_id:
            message += f" (transaction: {transaction_id})"
        super().__init__(
            message=message,
            error_code='DUPLICATE_PAYMENT',
            details={
                'payment_id': payment_id,
                'transaction_id': transaction_id
            }
        )


class RefundError(PaymentError):
    """
    Error during refund processing
    
    Usage:
        raise RefundError(
            payment_id=payment.id,
            message="Refund window expired"
        )
    """
    
    def __init__(self, payment_id: int, message: str, error_code: str = None):
        self.payment_id = payment_id
        super().__init__(
            message=message,
            error_code=error_code or 'REFUND_ERROR',
            details={'payment_id': payment_id}
        )


# Convenience function for HTTP response mapping
def get_http_status(exception: Exception) -> int:
    """
    Map exception to HTTP status code
    
    Usage:
        except PaymentError as e:
            return Response({'error': str(e)}, status=get_http_status(e))
    """
    mapping = {
        PaymentValidationError: 400,
        InvalidPackageError: 400,
        DuplicatePaymentError: 409,
        SubscriptionQuotaExceeded: 403,
        SubscriptionNotFound: 404,
        SubscriptionExpired: 402,  # Payment Required
        PaymentGatewayError: 502,  # Bad Gateway
        WebhookVerificationError: 400,
        RefundError: 400,
        PaymentProcessingError: 500,
        PaymentError: 500,
        SubscriptionError: 500,
    }
    
    for exc_class, status in mapping.items():
        if isinstance(exception, exc_class):
            return status
    
    return 500
