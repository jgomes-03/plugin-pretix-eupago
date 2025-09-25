"""
Comando Django para marcar pagamentos EuPago como confirmados manualmente
Útil quando webhooks não estão configurados ou falham
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django_scopes import scopes_disabled

from pretix.base.models import OrderPayment


class Command(BaseCommand):
    help = 'Manually confirm EuPago payments by Payment ID'

    def add_arguments(self, parser):
        parser.add_argument(
            'payment_ids',
            nargs='+',
            type=str,
            help='Payment IDs to confirm (space separated)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force confirmation even if payment is not pending',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be confirmed without making changes',
        )

    def handle(self, *args, **options):
        payment_ids = options['payment_ids']
        force = options.get('force', False)
        dry_run = options.get('dry_run', False)
        
        self.stdout.write('🔄 Manual EuPago Payment Confirmation...\n')
        
        confirmed_count = 0
        error_count = 0
        
        try:
            with scopes_disabled():
                for payment_id in payment_ids:
                    self.stdout.write(f'🔍 Processing payment {payment_id}...')
                    
                    # Find the payment
                    payment = OrderPayment.objects.filter(
                        local_id=payment_id,
                        provider__startswith='eupago'
                    ).first()
                    
                    if not payment:
                        self.stdout.write(self.style.ERROR(f'   ❌ Payment {payment_id} not found'))
                        error_count += 1
                        continue
                    
                    # Check current state
                    self.stdout.write(f'   📊 Current state: {payment.state}')
                    self.stdout.write(f'   💰 Amount: €{payment.amount}')
                    self.stdout.write(f'   🏷️  Provider: {payment.provider}')
                    
                    # Check if already confirmed
                    if payment.state == OrderPayment.PAYMENT_STATE_CONFIRMED:
                        if not force:
                            self.stdout.write(self.style.WARNING(f'   ⚠️  Payment {payment_id} already confirmed (use --force to override)'))
                            continue
                        else:
                            self.stdout.write(f'   🔄 Forcing re-confirmation...')
                    
                    elif payment.state not in [OrderPayment.PAYMENT_STATE_PENDING, OrderPayment.PAYMENT_STATE_CREATED]:
                        if not force:
                            self.stdout.write(self.style.WARNING(f'   ⚠️  Payment {payment_id} is in state {payment.state} (use --force to override)'))
                            continue
                    
                    if dry_run:
                        self.stdout.write(f'   🧪 Would confirm payment {payment_id} (DRY RUN)')
                        confirmed_count += 1
                        continue
                    
                    try:
                        # Confirm the payment
                        payment.confirm()
                        confirmed_count += 1
                        self.stdout.write(self.style.SUCCESS(f'   ✅ Payment {payment_id} confirmed successfully'))
                        
                        # Update payment info to reflect manual confirmation
                        import json
                        info = {}
                        try:
                            info = json.loads(payment.info or '{}')
                        except:
                            pass
                        
                        info['manual_confirmation'] = {
                            'confirmed_at': timezone.now().isoformat(),
                            'method': 'management_command'
                        }
                        
                        payment.info = json.dumps(info)
                        payment.save(update_fields=['info'])
                        
                    except Exception as e:
                        error_count += 1
                        self.stdout.write(self.style.ERROR(f'   💥 Failed to confirm payment {payment_id}: {e}'))
                
                # Summary
                self.stdout.write('\n📈 CONFIRMATION SUMMARY:')
                self.stdout.write(f'   Total Processed: {len(payment_ids)}')
                self.stdout.write(f'   ✅ Successfully Confirmed: {confirmed_count}')
                self.stdout.write(f'   💥 Errors: {error_count}')
                
                if dry_run:
                    self.stdout.write(self.style.WARNING('\n🏃 DRY RUN - No changes made'))
                elif confirmed_count > 0:
                    self.stdout.write(self.style.SUCCESS(f'\n✅ Manual confirmation completed: {confirmed_count} payments confirmed'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'💥 Command failed: {e}'))
            raise
