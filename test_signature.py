#!/usr/bin/env python3
"""
Test script to validate EuPago signature validation matches their PHP documentation.

PHP documentation shows:
function verifySignature($data, $signature, $key) {
    $generatedSignature = hash_hmac('sha256', $data, $key, true);
    return hash_equals($generatedSignature, base64_decode($signature));
}
"""

import hmac
import hashlib
import base64

def validate_webhook_signature_php_equivalent(data, signature, key):
    """
    Python equivalent of EuPago's PHP signature validation.
    
    PHP: hash_hmac('sha256', $data, $key, true) 
    The 'true' parameter means raw binary output (not hex)
    """
    # Generate signature using HMAC-SHA256 with raw binary output
    generated_signature = hmac.new(
        key.encode('utf-8'),
        data.encode('utf-8'),
        hashlib.sha256
    ).digest()  # .digest() returns raw bytes (equivalent to PHP's true parameter)
    
    # Decode the provided signature from base64
    try:
        provided_signature = base64.b64decode(signature)
    except Exception as e:
        print(f"Error decoding signature: {e}")
        return False
    
    # Compare using secure comparison (equivalent to PHP's hash_equals)
    return hmac.compare_digest(generated_signature, provided_signature)

# Test with sample data
test_data = "{'channel': {'account': 'demo-NÚCLEO DE ESTUDANTES DE TECNOLOGIAS DO ISCTE-IUL - NET ISCTE-IUL', 'name': 'demo-NÚCLEO DE ESTUDANTES DE TECNOLOGIAS DO ISCTE-IUL - NET ISCTE-IUL'}, 'transaction': {'entity': '10045', 'reference': '217733', 'identifier': 'J0G9U-P-1', 'method': 'MW:PT', 'amount': {'value': '35.00000', 'currency': 'EUR'}, 'fees': {'value': 0.38745, 'currency': 'EUR'}, 'date': '2025-09-26T01:07:55', 'trid': '29738480', 'status': 'Paid', 'local': 'demo'}}"
test_key = "F7b54HQEOaHvbNPBgv5fZMF7psBQ3ZXo"
test_signature_raw = hmac.new(
    test_key.encode('utf-8'),
    test_data.encode('utf-8'),
    hashlib.sha256
).digest()
test_signature_base64 = "JwyfXA4NLwOd+vph0eqbvskdd+zln9hkpgrdhy2jik9fflu6km4rshaa==" #base64.b64encode(test_signature_raw).decode('utf-8')

print("Testing EuPago signature validation:")
print(f"Data: {test_data}")
print(f"Key: {test_key}")
print(f"Generated signature (base64): {test_signature_base64}")

# Test validation
result = validate_webhook_signature_php_equivalent(test_data, test_signature_base64, test_key)
print(f"Validation result: {result}")

# Test with wrong signature
wrong_signature = base64.b64encode(b"wrong_signature_data_here").decode('utf-8')
wrong_result = validate_webhook_signature_php_equivalent(test_data, wrong_signature, test_key)
print(f"Wrong signature validation: {wrong_result}")

print("\nSignature validation implementation is working correctly!" if result and not wrong_result else "ERROR: Signature validation failed!")
