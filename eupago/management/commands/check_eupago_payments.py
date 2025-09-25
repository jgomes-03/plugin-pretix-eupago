"""
Management command to check pending EuPago payments and update their status.
This is useful as a fallback mechanism for missed webhooks.

Usage: python manage.py check_eupago_payments [--days=7] [--dry-run]
"""

import logging
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils.timezone import now
from pretix.base.models import OrderPayment

logger = logging.getLogger('pretix.plugins.eupago')


class Command(BaseCommand):
    help = 'Check and update status of pending EuPago payments'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Check payments from the last N days (default: 7)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes'
        )
        parser.add_argument(
            '--event',
            type=str,
            help='Limit to specific event slug'
        )
        parser.add_argument(
            '--organizer',
            type=str,
            help='Limit to specific organizer slug'
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        event_slug = options.get('event')
        organizer_slug = options.get('organizer')
        
        # Calculate cutoff date
        cutoff_date = now() - timedelta(days=days)
        
        self.stdout.write(f'Checking EuPago payments from the last {days} days...')
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        # Filter pending/created payments that use EuPago
        payments_query = OrderPayment.objects.filter(
            provider__startswith='eupago',
            state__in=[OrderPayment.PAYMENT_STATE_PENDING, OrderPayment.PAYMENT_STATE_CREATED],
            created__gte=cutoff_date
        )
        
        # Apply additional filters if specified
        if organizer_slug:
            payments_query = payments_query.filter(order__event__organizer__slug=organizer_slug)
        
        if event_slug:
            payments_query = payments_query.filter(order__event__slug=event_slug)
        
        payments = payments_query.select_related('order__event__organizer')
        
        self.stdout.write(f'Found {payments.count()} pending EuPago payments to check')
        
        checked_count = 0
        updated_count = 0
        errors_count = 0
        
        for payment in payments:
            try:
                self.stdout.write(f'Checking payment {payment.full_id}...', ending=' ')
                
                # Get the payment provider instance
                provider = payment.payment_provider
                if not provider:
                    self.stdout.write(self.style.ERROR('Provider not found'))
                    errors_count += 1
                    continue
                
                # Check payment status
                if hasattr(provider, 'check_payment_status'):
                    status_response = provider.check_payment_status(payment)
                    checked_count += 1
                    
                    if 'error' in status_response:
                        self.stdout.write(self.style.ERROR(f'API Error: {status_response["error"]}'))
                        errors_count += 1
                        continue
                    
                    # Process the status update
                    if not dry_run and hasattr(provider, 'process_webhook_payment_update'):
                        status_changed = provider.process_webhook_payment_update(payment, status_response)
                        if status_changed:
                            updated_count += 1
                            self.stdout.write(self.style.SUCCESS('Updated'))
                        else:
                            self.stdout.write(self.style.WARNING('No change'))
                    else:
                        # In dry-run mode, just report what we found
                        status = status_response.get('status') or status_response.get('transactionStatus') or status_response.get('estado', 'unknown')
                        if dry_run:
                            self.stdout.write(self.style.WARNING(f'Would check status: {status}'))
                        else:
                            self.stdout.write(f'Status: {status}')
                else:
                    self.stdout.write(self.style.ERROR('Provider does not support status checking'))
                    errors_count += 1
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
                logger.error(f'Error checking payment {payment.full_id}: {e}', exc_info=True)
                errors_count += 1
        
        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=== SUMMARY ==='))
        self.stdout.write(f'Payments checked: {checked_count}')
        if not dry_run:
            self.stdout.write(f'Payments updated: {updated_count}')
        self.stdout.write(f'Errors: {errors_count}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('This was a dry run - no actual changes were made'))
        elif updated_count > 0:
            self.stdout.write(self.style.SUCCESS(f'Successfully updated {updated_count} payment(s)'))
