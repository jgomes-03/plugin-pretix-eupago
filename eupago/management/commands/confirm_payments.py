"""
Comando para confirmar pagamentos EuPago manualmente
"""
from django.core.management.base import BaseCommand
from pretix.base.models import OrderPayment, Order
from django_scopes import scopes_disabled
import json

class Command(BaseCommand):
    help = 'Confirma pagamentos EuPago manualmente'

    def add_arguments(self, parser):
        parser.add_argument('--payment-id', type=int, help='ID do pagamento no Pretix para confirmar')
        parser.add_argument('--list', action='store_true', help='Listar pagamentos pendentes')
        parser.add_argument('--confirm-all', action='store_true', help='Confirmar todos os pagamentos pendentes')
        parser.add_argument('--dry-run', action='store_true', help='Apenas simular, não fazer alterações')

    @scopes_disabled()
    def handle(self, *args, **options):
        if options['list']:
            self.list_pending_payments()
        elif options['payment_id']:
            self.confirm_single_payment(options['payment_id'], options['dry_run'])
        elif options['confirm_all']:
            self.confirm_all_pending(options['dry_run'])
        else:
            self.stdout.write(self.style.ERROR('Use --list, --payment-id X, ou --confirm-all'))

    def list_pending_payments(self):
        """Lista todos os pagamentos pendentes"""
        self.stdout.write("=== Pagamentos EuPago Pendentes ===\n")
        
        pending_payments = OrderPayment.objects.filter(
            provider__startswith='eupago',
            state='pending'
        )
        
        if not pending_payments.exists():
            self.stdout.write(self.style.SUCCESS("✅ Nenhum pagamento pendente encontrado"))
            return
        
        for payment in pending_payments:
            self.stdout.write(f"ID: {payment.id}")
            self.stdout.write(f"  Provider: {payment.provider}")
            self.stdout.write(f"  Amount: {payment.amount}")
            self.stdout.write(f"  Created: {payment.created}")
            self.stdout.write(f"  Order: {payment.order.code}")
            
            if payment.info:
                try:
                    info = payment.info if isinstance(payment.info, dict) else json.loads(payment.info)
                    if 'transactionID' in info:
                        self.stdout.write(f"  Transaction ID: {info['transactionID']}")
                    if 'reference' in info:
                        self.stdout.write(f"  Reference: {info['reference']}")
                except:
                    pass
            self.stdout.write("---")

    def confirm_single_payment(self, payment_id, dry_run=False):
        """Confirma um pagamento específico"""
        try:
            payment = OrderPayment.objects.get(id=payment_id)
        except OrderPayment.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"❌ Pagamento com ID {payment_id} não encontrado"))
            return

        if not payment.provider.startswith('eupago'):
            self.stdout.write(self.style.ERROR(f"❌ Pagamento {payment_id} não é EuPago v2"))
            return

        if payment.state != 'pending':
            self.stdout.write(self.style.WARNING(f"⚠️ Pagamento {payment_id} já está em estado: {payment.state}"))
            return

        self.stdout.write(f"💰 Confirmando pagamento {payment_id}:")
        self.stdout.write(f"   Provider: {payment.provider}")
        self.stdout.write(f"   Amount: {payment.amount}")
        self.stdout.write(f"   Order: {payment.order.code}")

        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 DRY RUN - Não fazendo alterações reais"))
        else:
            # Confirmar o pagamento
            payment.confirm()
            self.stdout.write(self.style.SUCCESS(f"✅ Pagamento {payment_id} confirmado com sucesso!"))
            self.stdout.write(f"   Novo estado: {payment.state}")

    def confirm_all_pending(self, dry_run=False):
        """Confirma todos os pagamentos pendentes"""
        pending_payments = OrderPayment.objects.filter(
            provider__startswith='eupago',
            state='pending'
        )
        
        total = pending_payments.count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS("✅ Nenhum pagamento pendente encontrado"))
            return

        self.stdout.write(f"📦 Encontrados {total} pagamentos pendentes para confirmar")
        
        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 DRY RUN - Não fazendo alterações reais"))
        
        confirmed = 0
        for payment in pending_payments:
            self.stdout.write(f"Processando pagamento {payment.id}...")
            
            if not dry_run:
                try:
                    payment.confirm()
                    confirmed += 1
                    self.stdout.write(self.style.SUCCESS(f"  ✅ Confirmado"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  ❌ Erro: {e}"))
            else:
                self.stdout.write(self.style.WARNING(f"  🔍 Seria confirmado"))

        if not dry_run:
            self.stdout.write(self.style.SUCCESS(f"✅ {confirmed}/{total} pagamentos confirmados com sucesso!"))
