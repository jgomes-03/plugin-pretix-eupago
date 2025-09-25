#!/usr/bin/env python3
"""
Test script to validate EuPago signature validation with HEX format.

CORRECTION: EuPago uses HMAC-SHA256 in HEX format, not Base64!
"""

import hmac
import hashlib

def validate_webhook_signature_hex_format(data, signature_hex, key):
    """
    Python implementation for EuPago's HEX-based signature validation.
    
    EuPago uses HMAC-SHA256 and returns the signature in hexadecimal format.
    """
    # Generate signature using HMAC-SHA256  
    generated_signature_binary = hmac.new(
        key.encode('utf-8'),
        data.encode('utf-8'),
        hashlib.sha256
    ).digest()
    
    # Convert to hexadecimal (lowercase)
    generated_signature_hex = generated_signature_binary.hex().lower()
    
    # Clean and normalize received signature
    received_signature_hex = signature_hex.strip().lower()
    
    # Compare using secure comparison
    return hmac.compare_digest(generated_signature_hex, received_signature_hex)

# Test with sample data
test_data = '{"transaction_id":"123","amount":"10.50","status":"completed"}'
test_key = "your_webhook_secret_key"

# Generate test signature in HEX format
test_signature_binary = hmac.new(
    test_key.encode('utf-8'),
    test_data.encode('utf-8'),
    hashlib.sha256
).digest()
test_signature_hex = test_signature_binary.hex().lower()

print("Testing EuPago signature validation (HEX format):")
print(f"Data: {test_data}")
print(f"Key: {test_key}")
print(f"Generated signature (HEX): {test_signature_hex}")

# Test validation
result = validate_webhook_signature_hex_format(test_data, test_signature_hex, test_key)
print(f"Validation result: {result}")

# Test with wrong signature
wrong_signature = "wrong_hex_signature_12345"
wrong_result = validate_webhook_signature_hex_format(test_data, wrong_signature, test_key)
print(f"Wrong signature validation: {wrong_result}")

# Test case sensitivity
upper_signature = test_signature_hex.upper()
upper_result = validate_webhook_signature_hex_format(test_data, upper_signature, test_key)
print(f"Uppercase signature validation: {upper_result}")

print("\n✅ HEX signature validation implementation is working correctly!" if result and not wrong_result and upper_result else "❌ ERROR: Signature validation failed!")
