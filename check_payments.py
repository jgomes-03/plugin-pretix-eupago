#!/usr/bin/env python3
"""
Script para verificar pagamentos EuPago na base de dados
"""

import os
import sys
import django

# Add the pretix source directory to Python path
sys.path.insert(0, 'e:/ISCTE/NET/Pretix/pretix-dev/src')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pretix.settings')
django.setup()

from pretix.base.models import OrderPayment, Organizer
from django_scopes import scopes_disabled

def check_eupago_payments():
    """Check all EuPago payments in database"""
    print("=== EuPago Payments in Database ===\n")
    
    with scopes_disabled():
        # Find all EuPago payments
        eupago_payments = OrderPayment.objects.filter(
            provider__startswith='eupago'
        ).order_by('-created')
    
    if not eupago_payments:
        print("❌ No EuPago payments found in database")
        return
    
    print(f"✅ Found {eupago_payments.count()} EuPago payments:\n")
    
    for payment in eupago_payments:
        print(f"Payment ID: {payment.full_id}")
        print(f"Provider: {payment.provider}")
        print(f"State: {payment.state}")
        print(f"Amount: €{payment.amount}")
        print(f"Created: {payment.created}")
        print(f"Order: {payment.order.code if payment.order else 'None'}")
        
        # Try to get payment info
        try:
            import json
            info = json.loads(payment.info or '{}')
            if info:
                print(f"Info: {info}")
        except:
            print(f"Info: {payment.info}")
        
        print("-" * 50)

def search_specific_payments():
    """Search for specific payment IDs from the webhook test"""
    print("\n=== Searching for Specific Payment IDs ===\n")
    
    target_ids = ['J03CS-P-1', '217404', 'T0FKN-P-1', '217395']
    
    with scopes_disabled():
        for payment_id in target_ids:
            payment = OrderPayment.objects.filter(full_id=payment_id).first()
            if payment:
                print(f"✅ Found payment {payment_id}:")
                print(f"   Provider: {payment.provider}")
                print(f"   State: {payment.state}")
                print(f"   Amount: €{payment.amount}")
            else:
                print(f"❌ Payment {payment_id} not found")

if __name__ == "__main__":
    try:
        check_eupago_payments()
        search_specific_payments()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
