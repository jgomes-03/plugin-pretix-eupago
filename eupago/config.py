# EuPago v2 Plugin Configuration

DEFAULT_SETTINGS = {
    'api_key': '',
    'client_id': '',
    'client_secret': '',
    'webhook_secret': '',
    'endpoint': 'sandbox',
    
    # Method-specific settings
    'cc_description': 'Pay securely with your credit card',
    'mbway_description': 'Pay with MBWay using your mobile phone', 
    'multibanco_description': 'Pay via bank transfer using Multibanco reference',
    'payshop_description': 'Pay in cash at any PayShop location',
    'paybylink_description': 'Pay online with your preferred payment method',
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
    'paybylink': 'eupago_paybylink'
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
