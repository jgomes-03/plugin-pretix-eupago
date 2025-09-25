"""
Django management command to sync EuPago payments
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django_scopes import scopes_disabled

from pretix.base.models import OrderPayment


class Command(BaseCommand):
    help = 'Sync pending EuPago payments with API status'

    def add_arguments(self, parser):
        parser.add_argument(
            '--provider',
            type=str,
            help='Sync only specific provider (eupago_mbway, eupago_multibanco, etc.)',
        )
        parser.add_argument(
            '--hours',
            type=int,
            default=24,
            help='Only sync payments created in last N hours (default: 24)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be synced without making changes',
        )

    def handle(self, *args, **options):
        self.stdout.write('🔄 Starting EuPago payment sync...\n')
        
        provider_filter = options.get('provider')
        hours = options.get('hours', 24)
        dry_run = options.get('dry_run', False)
        
        # Calculate time threshold
        time_threshold = timezone.now() - timezone.timedelta(hours=hours)
        
        try:
            with scopes_disabled():
                # Build query filters
                filters = {
                    'provider__startswith': 'eupago',
                    'state': OrderPayment.PAYMENT_STATE_PENDING,
                    'created__gte': time_threshold
                }
                
                if provider_filter:
                    filters['provider'] = provider_filter
                
                # Find pending payments
                pending_payments = OrderPayment.objects.filter(**filters).order_by('-created')
                
                total_count = pending_payments.count()
                self.stdout.write(f'📊 Found {total_count} pending payments to check\n')
                
                if total_count == 0:
                    self.stdout.write(self.style.SUCCESS('✅ No pending payments found'))
                    return
                
                # Group by provider for stats
                providers_stats = {}
                confirmed_count = 0
                failed_count = 0
                error_count = 0
                
                for payment in pending_payments:
                    provider_name = payment.provider
                    
                    if provider_name not in providers_stats:
                        providers_stats[provider_name] = {
                            'total': 0,
                            'confirmed': 0, 
                            'failed': 0,
                            'errors': 0
                        }
                    
                    providers_stats[provider_name]['total'] += 1
                    
                    self.stdout.write(f'🔍 Checking payment {payment.full_id} ({payment.provider})...')
                    
                    try:
                        # Get payment provider instance
                        provider_instance = payment.payment_provider
                        
                        if not provider_instance:
                            self.stdout.write(self.style.WARNING(f'   ⚠️  No provider instance for {payment.full_id}'))
                            error_count += 1
                            providers_stats[provider_name]['errors'] += 1
                            continue
                        
                        # Check status via API
                        status_info = provider_instance.check_payment_status(payment)
                        
                        if dry_run:
                            self.stdout.write(f'   🔍 Status: {status_info} (DRY RUN)')
                            continue
                        
                        # Process status update
                        if status_info.get('confirmed'):
                            payment.confirm()
                            confirmed_count += 1
                            providers_stats[provider_name]['confirmed'] += 1
                            self.stdout.write(self.style.SUCCESS(f'   ✅ Payment {payment.full_id} confirmed'))
                            
                        elif status_info.get('failed'):
                            payment.fail(info=status_info)
                            failed_count += 1
                            providers_stats[provider_name]['failed'] += 1
                            self.stdout.write(self.style.WARNING(f'   ❌ Payment {payment.full_id} failed'))
                            
                        else:
                            self.stdout.write(f'   ⏳ Payment {payment.full_id} still pending')
                            
                    except Exception as e:
                        error_count += 1
                        providers_stats[provider_name]['errors'] += 1
                        self.stdout.write(self.style.ERROR(f'   💥 Error checking {payment.full_id}: {e}'))
                
                # Display summary
                self.stdout.write('\n📈 SYNC SUMMARY:')
                self.stdout.write(f'   Total Checked: {total_count}')
                self.stdout.write(f'   ✅ Confirmed: {confirmed_count}')
                self.stdout.write(f'   ❌ Failed: {failed_count}')
                self.stdout.write(f'   💥 Errors: {error_count}')
                
                # Provider breakdown
                self.stdout.write('\n📊 BY PROVIDER:')
                for provider, stats in providers_stats.items():
                    self.stdout.write(f'   {provider}:')
                    self.stdout.write(f'     Total: {stats["total"]}')
                    self.stdout.write(f'     Confirmed: {stats["confirmed"]}')
                    self.stdout.write(f'     Failed: {stats["failed"]}')
                    self.stdout.write(f'     Errors: {stats["errors"]}')
                
                if dry_run:
                    self.stdout.write(self.style.WARNING('\n🏃 DRY RUN - No changes made'))
                else:
                    self.stdout.write(self.style.SUCCESS(f'\n✅ Sync completed: {confirmed_count + failed_count} payments updated'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'💥 Sync failed: {e}'))
            raise
