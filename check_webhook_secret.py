#!/usr/bin/env python3
"""
Quick script to check webhook secret configuration
Run this after updating the webhook secret in organizer settings
"""

import os
import sys
import django

# Add the pretix-dev src directory to Python path
sys.path.insert(0, r'e:\ISCTE\NET\Pretix\pretix-dev\src')

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pretix.settings')
django.setup()

from pretix.base.models import Organizer
from django_scopes import scopes_disabled

def check_webhook_secrets():
    print("Checking webhook secret configuration...")
    print("=" * 60)
    
    try:
        with scopes_disabled():
            organizers = Organizer.objects.all()
            
            for organizer in organizers:
                print(f"\nOrganizer: {organizer.slug}")
                print("-" * 40)
                
                # Check different possible setting keys
                settings_to_check = [
                    'payment_eupago_webhook_secret',
                    'eupago_webhook_secret', 
                    'webhook_secret',
                    'payment_webhook_secret'
                ]
                
                found_secret = False
                for setting_key in settings_to_check:
                    value = organizer.settings.get(setting_key, '')
                    if value:
                        found_secret = True
                        # Show partial value for security
                        masked = value[:8] + '...' + value[-8:] if len(value) > 16 else value
                        print(f"  ✅ {setting_key}: {masked} (length: {len(value)})")
                        
                        # Check if it matches the expected pattern from logs
                        if value.startswith('F7b54HQE') and value.endswith('psBQ3ZXo'):
                            print(f"  🎯 MATCHES log pattern! This should work.")
                        else:
                            print(f"  ⚠️  Does NOT match log pattern F7b54HQE...psBQ3ZXo")
                
                if not found_secret:
                    print(f"  ❌ No webhook secret found")
                    
                # Check other EuPago settings for context
                print(f"\nOther EuPago settings:")
                api_key = organizer.settings.get('payment_eupago_api_key', '')
                endpoint = organizer.settings.get('payment_eupago_endpoint', 'sandbox')
                print(f"  API Key: {'[CONFIGURED]' if api_key else '[NOT SET]'}")
                print(f"  Endpoint: {endpoint}")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_webhook_secrets()
