# EuPago v2 Plugin Configuration

# Pretix stores payment provider settings with a 'payment_' prefix before the provider identifier
# e.g., 'payment_eupago_webhook_secret' instead of just 'eupago_webhook_secret'
DEFAULT_SETTINGS = {
    'api_key': '',
    'client_id': '',
    'client_secret': '',
    'webhook_secret': '',
    'endpoint': 'sandbox',
    'debug_mode': False,  # When enabled, provides additional debugging information and accepts more signature formats
    
    # Method-specific settings (legacy)
    'cc_description': 'Pay securely with your credit card',
    'mbway_description': 'Pay with MBWay using your mobile phone', 
    'multibanco_description': 'Pay via bank transfer using Multibanco reference',
    'payshop_description': 'Pay in cash at any PayShop location',
    'paybylink_description': 'Pay online with your preferred payment method',
    
    # New payment methods with dedicated configurations
    'mb_creditcard_api_key': '',
    'mb_creditcard_webhook_secret': '',
    'mb_creditcard_description': 'Pay with MB or Credit Card',
    'mbway_new_api_key': '',
    'mbway_new_webhook_secret': '',
    'mbway_new_description': 'Pay with MBWay using your mobile phone',
}

# API Endpoints
ENDPOINTS = {
    'sandbox': 'https://sandbox.eupago.pt',
    'live': 'https://clientes.eupago.pt'
}

# Payment method identifiers
PAYMENT_METHODS = {
    'creditcard': 'eupago_cc',
    'mbway': 'eupago_mbway', 
    'multibanco': 'eupago_multibanco',
    'payshop': 'eupago_payshop',
    'paybylink': 'eupago_paybylink',
    'mb_creditcard': 'eupago_mb_creditcard',  # New: MB and Credit Card
    'mbway_new': 'eupago_mbway_new'          # New: MBWay with dedicated config
}

# API Endpoints for each payment method
API_ENDPOINTS = {
    'auth_token': '/api/auth/token',
    'creditcard': '/api/v1.02/creditcard/create',
    'mbway': '/api/v1.02/mbway/create',
    'multibanco': '/clientes/rest_api/multibanco/create',
    'payshop': '/clientes/rest_api/payshop/create',
    'paybylink': '/api/v1.02/paybylink/create'
}

# Required parameters for each payment method
REQUIRED_PARAMS = {
    'creditcard': ['valor', 'id', 'canal', 'resposta_url'],  # chave_api goes in header, not body
    'mbway': ['valor', 'id', 'canal', 'customer_phone'],     # chave_api goes in header, not body  
    'multibanco': ['chave_api', 'valor', 'id', 'canal'],     # chave_api goes in body
    'payshop': ['chave_api', 'valor', 'id', 'canal'],        # chave_api goes in body
    'paybylink': ['payment.amount', 'payment.identifier', 'urlReturn']  # chave_api goes in header, not body
}

# Authentication methods for each payment type
AUTH_METHODS = {
    'creditcard': 'header',  # API Key in header
    'mbway': 'header',       # API Key in header  
    'multibanco': 'body',    # API Key in body
    'payshop': 'body',       # API Key in body
    'paybylink': 'header',   # API Key in header
    'auth_token': 'oauth'    # OAuth 2.0
}

# Supported currencies
SUPPORTED_CURRENCIES = ['EUR']

# Webhook event types
WEBHOOK_EVENTS = [
    'payment.completed',
    'payment.failed',
    'payment.cancelled', 
    'payment.pending',
    'payment.refunded'
]
