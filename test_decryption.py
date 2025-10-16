#!/usr/bin/env python3
"""
Test script for EuPago webhook decryption debugging
Run this script to test different webhook secret configurations
"""

import base64
import hashlib
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

def test_decryption(encrypted_data_b64, iv_b64, webhook_secrets):
    """Test decryption with multiple webhook secret variations"""
    
    print(f"Testing decryption...")
    print(f"Encrypted data (base64): {encrypted_data_b64[:50]}...")
    print(f"IV (base64): {iv_b64}")
    print(f"Testing {len(webhook_secrets)} webhook secret variations...")
    print("-" * 80)
    
    try:
        encrypted_bytes = base64.b64decode(encrypted_data_b64)
        iv_bytes = base64.b64decode(iv_b64)
        
        print(f"Encrypted bytes: {len(encrypted_bytes)} bytes")
        print(f"IV bytes: {len(iv_bytes)} bytes")
        print("-" * 80)
        
        for i, (name, secret) in enumerate(webhook_secrets, 1):
            print(f"\n[{i}] Testing: {name}")
            print(f"    Secret: {secret[:8]}...{secret[-8:] if len(secret) > 16 else secret[8:]}")
            
            # Test different key preparation methods
            key_methods = []
            
            # Method 1: Direct UTF-8 encoding
            key_utf8 = secret.encode('utf-8')
            if len(key_utf8) <= 32:
                key_padded = key_utf8.ljust(32, b'\0') if len(key_utf8) < 32 else key_utf8[:32]
                key_methods.append(('utf8-direct', key_padded))
            
            # Method 2: SHA-256 hash
            key_hash = hashlib.sha256(secret.encode('utf-8')).digest()
            key_methods.append(('sha256-hash', key_hash))
            
            # Method 3: If it looks like hex, try decoding
            if len(secret) == 64 and all(c in '0123456789abcdefABCDEF' for c in secret):
                try:
                    key_hex = bytes.fromhex(secret)
                    key_methods.append(('hex-decoded', key_hex))
                except:
                    pass
            
            # Method 4: If it looks like base64, try decoding
            if len(secret) > 20 and secret.replace('+', '').replace('/', '').replace('=', '').isalnum():
                try:
                    key_b64 = base64.b64decode(secret)
                    if len(key_b64) <= 32:
                        key_b64_padded = key_b64.ljust(32, b'\0') if len(key_b64) < 32 else key_b64[:32]
                        key_methods.append(('base64-decoded', key_b64_padded))
                except:
                    pass
            
            # Test each key method
            for method_name, key in key_methods:
                print(f"    [{method_name}] Key: {key[:4].hex()}...{key[-4:].hex()} ({len(key)} bytes)")
                
                try:
                    cipher = AES.new(key, AES.MODE_CBC, iv_bytes)
                    decrypted_padded = cipher.decrypt(encrypted_bytes)
                    
                    # Try different padding removal methods
                    padding_methods = []
                    
                    # PKCS7 unpadding
                    try:
                        decrypted_pkcs7 = unpad(decrypted_padded, AES.block_size)
                        padding_methods.append(('pkcs7', decrypted_pkcs7))
                    except:
                        pass
                    
                    # Manual PKCS7
                    try:
                        pad_length = decrypted_padded[-1]
                        if isinstance(pad_length, str):
                            pad_length = ord(pad_length)
                        if 1 <= pad_length <= 16:
                            if all(b == pad_length for b in decrypted_padded[-pad_length:]):
                                decrypted_manual = decrypted_padded[:-pad_length]
                                padding_methods.append(('manual-pkcs7', decrypted_manual))
                    except:
                        pass
                    
                    # No padding removal
                    padding_methods.append(('none', decrypted_padded))
                    
                    # Test UTF-8 decoding for each padding method
                    for pad_name, decrypted_bytes in padding_methods:
                        try:
                            decoded_string = decrypted_bytes.decode('utf-8')
                            trimmed = decoded_string.strip()
                            
                            # Check if it looks like JSON
                            if (trimmed.startswith('{') and trimmed.endswith('}')) or (trimmed.startswith('[') and trimmed.endswith(']')):
                                print(f"    ✅ SUCCESS! Method: {method_name}+{pad_name}")
                                print(f"       Decoded: {trimmed[:100]}...")
                                try:
                                    import json
                                    parsed = json.loads(trimmed)
                                    print(f"       Valid JSON with {len(parsed)} keys" if isinstance(parsed, dict) else f"       Valid JSON array with {len(parsed)} items")
                                    return True, f"{name} using {method_name}+{pad_name}", trimmed
                                except:
                                    pass
                            else:
                                print(f"       Decoded but not JSON: {trimmed[:50]}...")
                        except UnicodeDecodeError as e:
                            print(f"       UTF-8 decode failed ({pad_name}): {str(e)[:50]}")
                
                except Exception as e:
                    print(f"    ❌ Decryption failed: {str(e)[:50]}")
    
    except Exception as e:
        print(f"❌ Setup error: {e}")
    
    return False, None, None

def main():
    print("EuPago Webhook Decryption Test")
    print("=" * 80)
    
    # From your error logs:
    encrypted_data = input("Enter encrypted data (base64): ").strip()
    iv = input("Enter IV (base64): ").strip()
    
    print("\nEnter webhook secrets to test (one per line, empty line to finish):")
    webhook_secrets = []
    
    # Add some common variations to test
    base_secret = input("Primary webhook secret: ").strip()
    if base_secret:
        webhook_secrets.append(("primary", base_secret))
        
        # Add variations
        webhook_secrets.append(("primary-stripped", base_secret.strip()))
        
        if base_secret != base_secret.lower():
            webhook_secrets.append(("primary-lowercase", base_secret.lower()))
        
        if base_secret != base_secret.upper():
            webhook_secrets.append(("primary-uppercase", base_secret.upper()))
    
    # Allow additional secrets
    print("Any additional secrets? (empty line to finish)")
    while True:
        additional = input("Additional secret: ").strip()
        if not additional:
            break
        webhook_secrets.append((f"additional-{len(webhook_secrets)}", additional))
    
    if not webhook_secrets:
        print("No webhook secrets provided!")
        return
    
    success, method, result = test_decryption(encrypted_data, iv, webhook_secrets)
    
    if success:
        print(f"\n🎉 DECRYPTION SUCCESSFUL!")
        print(f"Working method: {method}")
        print(f"Result: {result}")
    else:
        print(f"\n❌ All decryption methods failed!")
        print(f"Please check:")
        print(f"1. Webhook secret is exactly as configured in EuPago backoffice")
        print(f"2. You're using the correct environment (sandbox vs live)")
        print(f"3. The encrypted data and IV are from a real webhook")

if __name__ == "__main__":
    main()
