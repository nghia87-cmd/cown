"""
VNPay Payment Gateway Integration
"""

import hashlib
import hmac
import urllib.parse
from datetime import datetime
from django.conf import settings


class VNPayGateway:
    """VNPay payment gateway"""
    
    def __init__(self):
        self.vnp_url = settings.VNPAY_URL
        self.vnp_tmn_code = settings.VNPAY_TMN_CODE
        self.vnp_hash_secret = settings.VNPAY_HASH_SECRET
        self.vnp_return_url = settings.VNPAY_RETURN_URL
    
    def create_payment_url(self, order_id, amount, order_desc, ip_address='127.0.0.1', bank_code=None, locale='vn'):
        """
        Create VNPay payment URL
        
        Args:
            order_id: Order ID (max 40 chars)
            amount: Amount in VND (will be multiplied by 100)
            order_desc: Order description
            ip_address: Client IP address (required by VNPay)
            bank_code: Bank code (optional)
            locale: Language (vn or en)
        
        Returns:
            Payment URL string
        """
        
        # Create timestamp
        create_date = datetime.now().strftime('%Y%m%d%H%M%S')
        
        # Build request data
        vnp_params = {
            'vnp_Version': '2.1.0',
            'vnp_Command': 'pay',
            'vnp_TmnCode': self.vnp_tmn_code,
            'vnp_Amount': int(amount * 100),  # VNPay requires amount * 100
            'vnp_CreateDate': create_date,
            'vnp_CurrCode': 'VND',
            'vnp_IpAddr': ip_address,  # Real client IP address
            'vnp_Locale': locale,
            'vnp_OrderInfo': order_desc,
            'vnp_OrderType': 'other',
            'vnp_ReturnUrl': self.vnp_return_url,
            'vnp_TxnRef': order_id,
        }
        
        # Add bank code if provided
        if bank_code:
            vnp_params['vnp_BankCode'] = bank_code
        
        # Sort parameters
        sorted_params = sorted(vnp_params.items())
        
        # Create query string
        query_string = '&'.join([f"{k}={urllib.parse.quote_plus(str(v))}" for k, v in sorted_params])
        
        # Create secure hash
        hash_data = '&'.join([f"{k}={v}" for k, v in sorted_params])
        secure_hash = hmac.new(
            self.vnp_hash_secret.encode('utf-8'),
            hash_data.encode('utf-8'),
            hashlib.sha512
        ).hexdigest()
        
        # Build final URL
        payment_url = f"{self.vnp_url}?{query_string}&vnp_SecureHash={secure_hash}"
        
        return payment_url
    
    def validate_response(self, response_data):
        """
        Validate VNPay callback response
        
        Args:
            response_data: Dict of query parameters from VNPay
        
        Returns:
            tuple: (is_valid, message)
        """
        
        # Get secure hash from response
        vnp_secure_hash = response_data.get('vnp_SecureHash')
        if not vnp_secure_hash:
            return False, "Missing secure hash"
        
        # Remove hash from params
        params = {k: v for k, v in response_data.items() if k != 'vnp_SecureHash'}
        
        # Sort parameters
        sorted_params = sorted(params.items())
        
        # Create hash data
        hash_data = '&'.join([f"{k}={v}" for k, v in sorted_params])
        
        # Calculate hash
        calculated_hash = hmac.new(
            self.vnp_hash_secret.encode('utf-8'),
            hash_data.encode('utf-8'),
            hashlib.sha512
        ).hexdigest()
        
        # Validate hash
        if calculated_hash != vnp_secure_hash:
            return False, "Invalid secure hash"
        
        # Check response code
        response_code = response_data.get('vnp_ResponseCode')
        if response_code == '00':
            return True, "Payment successful"
        else:
            return False, f"Payment failed with code: {response_code}"
    
    def get_transaction_info(self, response_data):
        """
        Extract transaction information from response
        
        Args:
            response_data: Dict of query parameters from VNPay
        
        Returns:
            dict: Transaction information
        """
        
        return {
            'order_id': response_data.get('vnp_TxnRef'),
            'transaction_id': response_data.get('vnp_TransactionNo'),
            'amount': int(response_data.get('vnp_Amount', 0)) / 100,  # Convert back from VNPay format
            'response_code': response_data.get('vnp_ResponseCode'),
            'bank_code': response_data.get('vnp_BankCode'),
            'card_type': response_data.get('vnp_CardType'),
            'pay_date': response_data.get('vnp_PayDate'),
            'transaction_status': response_data.get('vnp_TransactionStatus'),
        }
