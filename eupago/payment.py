import base64
import hashlib
import hmac
import json
import logging
import requests
from collections import OrderedDict
from decimal import Decimal
from django import forms
from django.core.exceptions import ValidationError
from django.http import HttpRequest, HttpResponse
from django.template.loader import get_template
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _, pgettext_lazy

from pretix.base.forms import SecretKeySettingsField
from pretix.base.models import Event, Order, OrderPayment
from pretix.base.payment import BasePaymentProvider, PaymentException
from pretix.base.settings import SettingsSandbox
from pretix.multidomain.urlreverse import build_absolute_uri

logger = logging.getLogger('pretix.plugins.eupago')


class EuPagoBaseProvider(BasePaymentProvider):
    """Base class for all EuPago payment providers"""
    
    abort_pending_allowed = False
    
    def __init__(self, event: Event):
        super().__init__(event)
        # Acessar as configurações do organizador através do event
        self.organizer = event.organizer

    def get_setting(self, name, default=None):
        """Get a setting from organizer-level configuration"""
        # All payment methods now use the same organizer-level configuration
        # First try with payment_eupago prefix (standard pretix convention for legacy settings)
        try:
            value = self.organizer.settings.get(f'payment_eupago_{name}', None)
        except Exception:
            value = None
        
        # If not found, try with just eupago prefix (organizer-level configuration)
        if value is None:
            try:
                value = self.organizer.settings.get(f'eupago_{name}', default)
            except Exception:
                value = default
                
        return value
    
    @property
    def debug_mode(self):
        """Check if debug mode is enabled"""
        try:
            value = self.get_setting('debug_mode', False)
            # Handle various possible values
            if isinstance(value, bool):
                return value
            elif isinstance(value, str):
                return value.lower() in ('true', '1', 'yes', 'on')
            else:
                return bool(value)
        except Exception:
            return False
            
    @property
    def test_mode_message(self):
        if self.get_setting('endpoint', 'sandbox') == 'sandbox':
            return _('The EuPago plugin is operating in sandbox mode. No real payments will be processed.')
        return None

    @property
    def settings_form_fields(self):
        """
        Usar a implementação padrão do pretix que inclui o campo _enabled.
        Sobrescrever apenas para adicionar campos específicos do EuPago.
        """
        # Obter os campos padrão do BasePaymentProvider
        base_fields = super().settings_form_fields
        
        # Adicionar campos específicos do EuPago (se necessário)
        # Por exemplo, descrições personalizadas podem ser adicionadas aqui
        
        return base_fields

    def is_allowed(self, request: HttpRequest, total: Decimal = None) -> bool:
        """
        Implementação padrão que usa apenas a propriedade is_enabled do BasePaymentProvider.
        Esta é a forma correta de verificar se um método de pagamento está ativado.
        """
        # A verificação padrão do pretix já faz tudo que precisamos
        if not self.is_enabled:
            logger.debug(f"{self.identifier} is disabled")
            return False
            
        # Verificações adicionais específicas do EuPago em ambiente de produção
        if self.get_setting('endpoint', 'sandbox') == 'live':
            if not self._check_settings():
                logger.debug(f"{self.identifier} has invalid settings for live environment")
                return False
                
        logger.info(f"is_allowed for {self.identifier}: enabled=True")
        return True

    def _check_settings(self) -> bool:
        """Check if all required settings are configured"""
        required_settings = ['api_key']  # Simplified: only API key is required
        
        # Log para debug
        logger.info(f"Checking settings for {self.identifier}")
        for setting in required_settings:
            value = self.get_setting(setting)
            logger.info(f"Setting {setting}: {'configured' if value else 'not configured'}")
        
        # Verificar configurações
        for setting in required_settings:
            if not self.get_setting(setting):
                return False
        return True

    def _get_api_base_url(self) -> str:
        """Get the appropriate API base URL"""
        if self.get_setting('endpoint', 'sandbox') == 'live':
            return 'https://clientes.eupago.pt'
        return 'https://sandbox.eupago.pt'

    def _get_headers(self, payment_method: str = None) -> dict:
        """Get HTTP headers for API requests"""
        from .config import AUTH_METHODS
        
        headers = {'Content-Type': 'application/json'}
        api_key = self.get_setting("api_key")
        
        # Add authentication based on payment method
        if payment_method and AUTH_METHODS.get(payment_method) == 'header':
            if api_key:
                # EuPago Credit Card expects "ApiKey" header (not Authorization)
                if payment_method == 'creditcard':
                    headers['ApiKey'] = api_key
                    logger.debug(f'Adding API key to ApiKey header for {payment_method}')
                else:
                    # Other methods might use Authorization
                    headers['Authorization'] = f'ApiKey {api_key}'
                    logger.debug(f'Adding API key to Authorization header for {payment_method}')
            else:
                logger.error(f'No API key configured for {payment_method}')
        elif payment_method and AUTH_METHODS.get(payment_method) == 'oauth':
            if api_key:
                headers['Authorization'] = f'Bearer {api_key}'
                logger.debug(f'Adding Bearer token for {payment_method}')
            else:
                logger.error(f'No API key configured for {payment_method}')
            
        return headers

    def _make_api_request(self, endpoint: str, data: dict, method: str = 'POST', payment_method: str = None) -> dict:
        """Make API request to EuPago"""
        from .config import AUTH_METHODS
        
        url = f"{self._get_api_base_url()}{endpoint}"
        headers = self._get_headers(payment_method)
        api_key = self.get_setting("api_key")
        
        # Add API key to body for certain payment methods
        if payment_method and AUTH_METHODS.get(payment_method) == 'body':
            if api_key:
                data['chave'] = api_key
                logger.debug(f'Adding API key to body for {payment_method}')
            else:
                logger.error(f'No API key configured for {payment_method}')
        
        logger.debug(f'Making {method} request to {url} for {payment_method}')
        logger.debug(f'Headers: {headers}')
        logger.debug(f'Data: {data}')
        
        try:
            if method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)
            elif method == 'GET':
                response = requests.get(url, params=data, headers=headers, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            logger.debug(f'Response status: {response.status_code}')
            logger.debug(f'Response text: {response.text}')
            
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            logger.error(f'EuPago API request failed: {e}')
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f'Response status: {e.response.status_code}')
                logger.error(f'Response text: {e.response.text}')
                
                # Specific error messages for common issues
                if e.response.status_code == 401:
                    raise PaymentException(_('Authentication failed. Please check your EuPago API key configuration.'))
                elif e.response.status_code == 403:
                    raise PaymentException(_('Access denied. Please verify your EuPago API permissions.'))
                    
            raise PaymentException(_('Payment provider communication failed. Please try again later.'))

    def _validate_webhook_signature(self, payload: str, signature: str) -> bool:
        """
        EuPago Webhooks 2.0:
        - Se o corpo tiver {"data": "<base64>"}, a assinatura é HMAC-SHA256( key=webhook_secret,
        msg=<string do campo data> ) e enviada em base64 (X-Signature).
        - Se NÃO tiver "data" (encrypt=false), assina o corpo bruto (payload).
        """
        import json, hmac, hashlib, base64, logging
        logger = logging.getLogger('pretix.plugins.eupago')

        # 1) obter a mesma chave usada na desencriptação "direct"
        webhook_secret = self.get_setting('webhook_secret') or ''
        if not webhook_secret:
            logger.warning('No webhook secret configured - skipping signature validation')
            return True

        if not signature:
            logger.warning('No webhook signature provided')
            return False

        # 2) decidir a mensagem a assinar
        try:
            body = json.loads(payload)
            if isinstance(body, dict) and isinstance(body.get('data'), str):
                # ENCRIPTADO: assina exatamente o string do campo "data"
                msg_bytes = body['data'].encode('utf-8')
            else:
                # NÃO ENCRIPTADO: assina o corpo inteiro
                msg_bytes = payload.encode('utf-8')
        except Exception:
            # JSON inválido → assina o corpo inteiro tal como chegou
            msg_bytes = payload.encode('utf-8')

        # 3) HMAC-SHA256 e comparação em tempo constante
        expected_bin = hmac.new(webhook_secret.encode('utf-8'), msg_bytes, hashlib.sha256).digest()
        try:
            received_bin = base64.b64decode(signature)
        except Exception as e:
            logger.error(f'Failed to base64-decode X-Signature: {e}')
            return False

        ok = hmac.compare_digest(expected_bin, received_bin)

        # debug
        if getattr(self, 'debug_mode', False) or not ok:
            logger.info(f'Expected signature (base64): {base64.b64encode(expected_bin).decode()}')
            logger.info(f'Received  signature (base64): {signature}')
            logger.info(f'Signatures match: {ok}')

        return ok

    
    def check_payment_status(self, payment: OrderPayment) -> dict:
        """Enhanced payment status check via API - using correct EuPago identifiers"""
        
        try:
            payment_id = payment.full_id
            payment_info = {}
            
            # Try to get existing payment info
            try:
                payment_info = json.loads(payment.info or '{}')
            except:
                pass
                
            logger.info(f'Checking payment {payment_id} - Payment info: {payment_info}')
            
            # Extract EuPago identifiers from payment info
            eupago_reference = payment_info.get('referencia') or payment_info.get('reference')
            eupago_id = payment_info.get('identificador') or payment_info.get('identifier') 
            transaction_ref = payment_info.get('transactionRef')
            
            logger.info(f'EuPago identifiers - Reference: {eupago_reference}, ID: {eupago_id}, TransactionRef: {transaction_ref}')
            
            # If we don't have EuPago identifiers, we can't check status via API
            if not eupago_reference and not eupago_id and not transaction_ref:
                logger.warning(f'No EuPago identifiers found for payment {payment_id} - cannot check status via API')
                return {
                    'confirmed': False, 
                    'failed': False,
                    'error': 'No EuPago identifiers available for API status check'
                }
            
            # For now, return pending status since API endpoints are not working
            # In a real scenario, you would use the correct EuPago API endpoints
            logger.info(f'Payment {payment_id} - API status check not available (404 errors). Using webhook-based updates only.')
            
            return {
                'confirmed': False,
                'failed': False,
                'pending': True,
                'note': 'API status check unavailable - using webhook notifications'
            }
            
        except Exception as e:
            logger.error(f'Failed to check payment status for {payment.full_id}: {e}')
            return {'confirmed': False, 'failed': False, 'error': str(e)}

    def _handle_payment_response(self, payment: OrderPayment, response: dict) -> str:
        """
        Handle payment response and auto-confirm when appropriate.
        Returns the redirect URL for the payment.
        """
        
        # Store payment information
        payment.info = json.dumps(response)
        
        # Check if payment should be auto-confirmed
        should_confirm = self._should_auto_confirm_payment(response)
        
        if should_confirm:
            logger.info(f'Auto-confirming payment {payment.full_id} due to successful transaction')
            payment.confirm()
        else:
            # Set to pending state
            payment.state = OrderPayment.PAYMENT_STATE_PENDING
            payment.save(update_fields=['info', 'state'])
            
        # Return redirect URL to order confirmation page
        return self.order_confirm_redirect_url
    
    def _should_auto_confirm_payment(self, response: dict) -> bool:
        """
        Determine if a payment should be automatically confirmed based on the API response.
        
        Important: According to EuPago docs, 'transactionStatus: Success' only means 
        the transaction was created successfully (MBWay push sent), NOT that it was paid.
        Webhooks are only sent when payments are actually paid.
        
        This can be overridden by specific payment methods if needed.
        """
        
        # Check for actual payment confirmation indicators
        # NOTE: 'transactionStatus: Success' is NOT included as it only means transaction created
        success_indicators = [
            response.get('estado') == 'Pago',           # Payment is paid
            response.get('status') == 'paid',           # Payment is paid
            response.get('state') == 'confirmed',       # Payment is confirmed
            response.get('payment_status') == 'paid'    # Alternative paid status
        ]
        
        # Auto-confirm only if payment is actually paid
        should_confirm = any(success_indicators)
        
        logger.debug(f'Auto-confirm check for response {response}: {should_confirm}')
        logger.debug(f'Success indicators checked: estado={response.get("estado")}, status={response.get("status")}, state={response.get("state")}')
        
        return should_confirm

    def _update_payment_from_status_response(self, payment: OrderPayment, status_response: dict):
        """Update payment based on API status response"""
        status = status_response.get('status') or status_response.get('transactionStatus') or status_response.get('estado')
        
        # Update payment info
        payment.info = json.dumps(status_response)
        
        if status in ['Success', 'Sucesso', 'completed', 'paid']:
            payment.confirm()
            logger.info(f'Payment {payment.full_id} confirmed via API status check')
            
        elif status in ['Failed', 'Falhado', 'failed', 'error']:
            payment.fail(info=status_response)
            logger.info(f'Payment {payment.full_id} failed via API status check')
            
        elif status in ['Expired', 'Expirado', 'expired', 'timeout']:
            payment.state = OrderPayment.PAYMENT_STATE_CANCELED
            payment.save(update_fields=['info', 'state'])
            logger.info(f'Payment {payment.full_id} expired via API status check')
            
        else:
            payment.save(update_fields=['info'])
            logger.debug(f'Payment {payment.full_id} info updated via API status check')
    
    def process_webhook_payment_update(self, payment: OrderPayment, webhook_data: dict) -> bool:
        """Process webhook payment update - returns True if payment status was changed"""
        try:
            current_state = payment.state
            
            # Extract status information from webhook data
            status = webhook_data.get('status') or webhook_data.get('transactionStatus') or webhook_data.get('estado')
            
            logger.info(f'Processing webhook update for payment {payment.full_id}: status={status}')
            
            # Update payment info with webhook data
            payment.info = json.dumps(webhook_data)
            
            # Determine new payment state based on status
            if status in ['Success', 'Sucesso', 'completed', 'paid']:
                if current_state != OrderPayment.PAYMENT_STATE_CONFIRMED:
                    payment.confirm()
                    logger.info(f'Payment {payment.full_id} confirmed via webhook')
                    return True
                    
            elif status in ['Failed', 'Falhado', 'failed', 'error']:
                if current_state not in [OrderPayment.PAYMENT_STATE_FAILED, OrderPayment.PAYMENT_STATE_CANCELED]:
                    payment.fail(info=webhook_data)
                    logger.info(f'Payment {payment.full_id} failed via webhook')
                    return True
                    
            elif status in ['Pending', 'Pendente', 'pending', 'processing']:
                if current_state == OrderPayment.PAYMENT_STATE_CREATED:
                    payment.state = OrderPayment.PAYMENT_STATE_PENDING
                    payment.save(update_fields=['info', 'state'])
                    logger.info(f'Payment {payment.full_id} updated to pending via webhook')
                    return True
                else:
                    payment.save(update_fields=['info'])  # Just update info
                    
            elif status in ['Canceled', 'Cancelado', 'canceled', 'cancelled']:
                if current_state != OrderPayment.PAYMENT_STATE_CANCELED:
                    payment.state = OrderPayment.PAYMENT_STATE_CANCELED
                    payment.save(update_fields=['info', 'state'])
                    logger.info(f'Payment {payment.full_id} canceled via webhook')
                    return True
            else:
                logger.warning(f'Unknown payment status in webhook: {status}')
                payment.save(update_fields=['info'])  # Save updated info anyway
                
            return False
            
        except Exception as e:
            logger.error(f'Error processing webhook update for payment {payment.full_id}: {e}')
            return False

    def payment_is_valid_session(self, request):
        return True

    def checkout_confirm_render(self, request, **kwargs) -> str:
        template = get_template('pretixplugins/eupago/checkout_payment_confirm.html')
        ctx = {
            'request': request,
            'event': self.event,
            'settings': self.settings,
            'provider': self,
        }
        return template.render(ctx)

    def order_pending_mail_render(self, order, payment) -> str:
        template = get_template('pretixplugins/eupago/email/order_pending.txt')
        ctx = {
            'order': order,
            'payment': payment,
            'provider': self,
        }
        return template.render(ctx)

    def sync_pending_payments(self):
        """Sync all pending payments for this provider"""
        from django_scopes import scopes_disabled
        
        try:
            with scopes_disabled():
                # Find all pending payments for this provider
                pending_payments = OrderPayment.objects.filter(
                    provider=self.identifier,
                    state=OrderPayment.PAYMENT_STATE_PENDING
                ).order_by('-created')
                
                logger.info(f'Found {pending_payments.count()} pending {self.identifier} payments to sync')
                
                synced_count = 0
                for payment in pending_payments:
                    try:
                        status_info = self.check_payment_status(payment)
                        
                        if status_info.get('confirmed'):
                            payment.confirm()
                            synced_count += 1
                            logger.info(f'Payment {payment.full_id} confirmed during sync')
                        elif status_info.get('failed'):
                            payment.fail(info=status_info)
                            synced_count += 1
                            logger.info(f'Payment {payment.full_id} failed during sync')
                        else:
                            logger.debug(f'Payment {payment.full_id} still pending')
                            
                    except Exception as e:
                        logger.error(f'Error syncing payment {payment.full_id}: {e}')
                
                return {
                    'total_pending': pending_payments.count(),
                    'synced': synced_count,
                    'provider': self.identifier
                }
                
        except Exception as e:
            logger.error(f'Error in sync_pending_payments: {e}')
            return {'error': str(e)}

    @classmethod
    def sync_all_pending_payments(cls, event=None):
        """Sync pending payments for all EuPago providers"""
        from django_scopes import scopes_disabled
        
        results = []
        providers = [
            EuPagoMBCreditCard,      # New: MB and Credit Card
            EuPagoMBWayNew,          # New: MBWay with dedicated config
            EuPagoMBWay,            # Legacy
            EuPagoMultibanco,       # Legacy
            EuPagoCreditCard,       # Legacy
            EuPagoPayShop,          # Legacy
            EuPagoPayByLink,        # Legacy
        ]
        
        try:
            with scopes_disabled():
                for provider_class in providers:
                    if event:
                        provider = provider_class(event)
                        result = provider.sync_pending_payments()
                        results.append(result)
                    else:
                        # Sync for all events
                        from pretix.base.models import Event
                        events = Event.objects.all()
                        for evt in events:
                            provider = provider_class(evt)
                            result = provider.sync_pending_payments() 
                            if result.get('total_pending', 0) > 0:
                                results.append(result)
                
                return results
                
        except Exception as e:
            logger.error(f'Error in sync_all_pending_payments: {e}')
            return [{'error': str(e)}]


class EuPagoCreditCard(EuPagoBaseProvider):
    identifier = 'eupago_cc'
    verbose_name = _('Credit Card Legacy(EuPago)')
    method = 'creditcard'
    payment_form_template_name = 'pretixplugins/eupago/checkout_payment_form_cc.html'

    @property
    def settings_form_fields(self):
        """Estende os campos base com configurações específicas do cartão de crédito"""
        base_fields = super().settings_form_fields
        
        # Adicionar campos específicos para cartão de crédito
        from collections import OrderedDict
        return OrderedDict(list(base_fields.items()) + [
            ('cc_description', forms.CharField(
                label=_('Payment description'),
                help_text=_('This will be displayed to customers during checkout'),
                required=False,
                initial=_('Pay securely with your credit card'),
            )),
        ])

    def execute_payment(self, request: HttpRequest, payment: OrderPayment):
        """Execute credit card payment"""
        from .config import API_ENDPOINTS
        
        logger.info(f'EuPagoCreditCard.execute_payment called for {payment.full_id} - Amount: €{payment.amount}')
        
        # Validar valor máximo da EuPago (3999€)
        if payment.amount > Decimal('3999.00'):
            raise PaymentException(_('Credit card payments are limited to €3999. Please use a different payment method.'))
        
        # Preparar dados conforme API EuPago Credit Card
        # Nota: chave_api vai no header, não no body
        data = {
            'valor': str(payment.amount),
            'id': payment.full_id,  # Identificador único do pagamento
            'canal': self._get_channel_id(),
            'resposta_url': build_absolute_uri(
                self.event,
                'plugins:eupago:return',
                kwargs={
                    'order': payment.order.code,
                    'hash': payment.order.tagged_secret('plugins:eupago'),
                    'payment': payment.pk,
                }
            ),
        }
        
        # Adicionar descrição personalizada se configurada
        cc_description = self.settings.get('cc_description') or self.organizer.settings.get('eupago_cc_description')
        if cc_description:
            data['descricao'] = cc_description

        try:
            logger.info(f'Creating credit card payment for {payment.full_id}: €{payment.amount}')
            logger.info(f'Credit card data being sent: {data}')
            
            response = self._make_api_request(
                API_ENDPOINTS['creditcard'], 
                data, 
                payment_method='creditcard'
            )
            
            logger.info(f'Credit card API response for {payment.full_id}: {response}')
            
            # Verificar se a resposta contém URL de pagamento
            payment_url = response.get('url') or response.get('redirect_url') or response.get('link')
            logger.info(f'Extracted payment URL: {payment_url}')
            
            if payment_url:
                # Guardar informações do pagamento
                payment_info = {
                    'payment_url': payment_url,
                    'transaction_id': response.get('transactionId') or response.get('id'),
                    'reference': response.get('referencia') or response.get('reference'),
                    'api_response': response,
                    'method': 'creditcard'
                }
                
                payment.info = json.dumps(payment_info)
                payment.state = OrderPayment.PAYMENT_STATE_PENDING
                payment.save(update_fields=['info', 'state'])
                
                logger.info(f'Credit card payment {payment.full_id} initialized successfully')
                # Note: Credit card payments are confirmed via return URL callback, not here
                return payment_url
            else:
                error_msg = response.get('error') or response.get('message') or 'No payment URL returned'
                logger.error(f'Credit card payment initialization failed for {payment.full_id}: {error_msg}')
                raise PaymentException(_('Payment initialization failed: {}').format(error_msg))
                
        except PaymentException:
            raise  # Re-raise PaymentExceptions
        except Exception as e:
            logger.error(f'Credit card payment failed for {payment.full_id}: {e}', exc_info=True)
            payment.fail(info={'error': str(e), 'method': 'creditcard'})
            raise PaymentException(_('Payment failed. Please try again later.'))
    
    def _get_channel_id(self):
        """Get channel ID from settings or use default"""
        channel_id = self.organizer.settings.get('eupago_channel_id')
        if not channel_id:
            # Use a default or derive from API key
            api_key = self.organizer.settings.get('eupago_api_key', '')
            # Extract channel from API key if possible, otherwise use default
            return api_key.split('-')[0] if api_key and '-' in api_key else 'default'
        return channel_id
    
    def checkout_prepare(self, request, cart):
        """Prepare checkout for credit card payment"""
        return True  # No special preparation needed
    
    def payment_prepare(self, request, payment):
        """Prepare payment object for credit card"""
        logger.info(f'EuPagoCreditCard.payment_prepare called for {payment.full_id}')
        
        # Store any form data in payment info for later use
        form_data = request.session.get('payment_eupago_cc', {})
        if form_data:
            payment_info = {
                'form_data': form_data,
                'method': 'creditcard',
                'prepared_at': str(timezone.now())
            }
            payment.info = json.dumps(payment_info)
            payment.save()
            logger.info(f'Credit card form data saved for {payment.full_id}')
        
        return True
        
    def payment_is_valid_session(self, request):
        """Check if payment session is valid for credit card"""
        return True  # Credit card payments are handled externally
    
    def checkout_confirm_render(self, request):
        """Render confirmation for credit card payment"""
        logger.info(f'EuPagoCreditCard.checkout_confirm_render called for event: {self.event.slug}')
        
        # Get form data from session
        form_data = request.session.get('payment_eupago_cc', {})
        
        template = get_template('pretixplugins/eupago/checkout_payment_confirm_cc.html')
        ctx = {
            'request': request, 
            'event': self.event,
            'settings': self.settings,
            'provider': self,
            'form_data': form_data,
            'total': request.session.get('cart_total', 0)
        }
        
        rendered = template.render(ctx)
        logger.info(f'EuPagoCreditCard.checkout_confirm_render - template rendered successfully (length: {len(rendered)})')
        
        return rendered
    
    @property
    def payment_form_fields(self):
        """Form fields for credit card payment - collected for better UX"""
        return OrderedDict([
            ('cc_holder', forms.CharField(
                label=_('Cardholder name'),
                max_length=100,
                required=False,
                help_text=_('Name as it appears on the card (optional - can be filled on EuPago page)')
            )),
        ])
    
    def is_allowed(self, request: HttpRequest, total: Decimal = None) -> bool:
        """Check if credit card payment is allowed"""
        logger.info(f'EuPagoCreditCard.is_allowed called - total: {total}')
        
        # Check base conditions
        if not super().is_allowed(request, total):
            logger.info('EuPagoCreditCard.is_allowed: base conditions failed')
            return False
            
        # Check maximum amount limit
        if total and total > Decimal('3999.00'):
            logger.info(f'EuPagoCreditCard.is_allowed: amount too high ({total} > 3999)')
            return False
        
        # Check if API key is configured
        if not self.organizer.settings.get('eupago_api_key'):
            logger.info('EuPagoCreditCard.is_allowed: no API key configured')
            return False
            
        logger.info('EuPagoCreditCard.is_allowed: allowed')
        return True


class EuPagoMBWay(EuPagoBaseProvider):
    identifier = 'eupago_mbway'
    verbose_name = _('MBWay Legacy(EuPago)')
    method = 'mbway'

    @property
    def payment_form_fields(self):
        return OrderedDict([
            ('phone', forms.CharField(
                label=_('Mobile phone number'),
                max_length=15,
                help_text=_('Enter your mobile phone number for MBWay payment')
            )),
        ])

    @property
    def settings_form_fields(self):
        """Estende os campos base com configurações específicas do MBWay"""
        base_fields = super().settings_form_fields
        
        from collections import OrderedDict
        return OrderedDict(list(base_fields.items()) + [
            ('mbway_description', forms.CharField(
                label=_('Payment description'),
                help_text=_('This will be displayed to customers during checkout'),
                required=False,
                initial=_('Pay with MBWay using your mobile phone'),
            )),
        ])

    def execute_payment(self, request: HttpRequest, payment: OrderPayment):
        """Execute MBWay payment"""
        from .config import API_ENDPOINTS
        from pretix.multidomain.urlreverse import build_absolute_uri
        
        # Try multiple ways to get the phone number
        phone = None
        
        # Method 1: From session with full identifier
        phone = request.session.get(f'payment_{self.identifier}_phone')
        logger.debug(f'Method 1 - Session with full identifier: {phone}')
        
        # Method 2: From POST data
        if not phone:
            phone = request.POST.get('phone')
            logger.debug(f'Method 2 - From POST data: {phone}')
        
        # Method 3: From session with different key patterns
        if not phone:
            phone = request.session.get('payment_eupago_mbway_phone')
            logger.debug(f'Method 3 - Session with pattern: {phone}')
            
        # Method 4: From session with simple key
        if not phone:
            phone = request.session.get('phone')
            logger.debug(f'Method 4 - Simple session key: {phone}')
        
        logger.debug(f'Final phone value: {phone}')
        
        if not phone:
            raise PaymentException(_('Phone number is required for MBWay payments'))

        # Use the correct EuPago API structure from documentation
        data = {
            "payment": {
                "amount": {
                    "currency": "EUR",
                    "value": float(payment.amount)
                },
                "customerPhone": phone,
                "identifier": payment.full_id,
                "countryCode": "+351",  # Default to Portugal
                "webhookUrl": request.build_absolute_uri(reverse('plugins:eupago:webhook'))
            }
        }
        
        logger.debug(f'MBWay request data (correct format): {data}')

        try:
            response = self._make_api_request(
                API_ENDPOINTS['mbway'], 
                data, 
                payment_method='mbway'
            )
            
            logger.debug(f'MBWay response: {response}')
            
            if response.get('estado') == 'Pendente' or response.get('transactionStatus') == 'Success':
                # Note: 'transactionStatus: Success' only means MBWay push was sent, not that payment is complete
                # Payment will be confirmed later via webhook when actually paid
                logger.info(f'MBWay payment {payment.full_id} initialized successfully - waiting for customer to pay')
                
                # Use the base class method to handle response and auto-confirmation
                return self._handle_payment_response(payment, response)
            else:
                raise PaymentException(_('MBWay payment initialization failed'))
                
        except Exception as e:
            logger.error(f'MBWay payment failed: {e}')
            payment.fail(info={'error': str(e)})
            raise PaymentException(_('MBWay payment failed. Please try again.'))


class EuPagoMultibanco(EuPagoBaseProvider):
    identifier = 'eupago_multibanco'
    verbose_name = _('Multibanco Legacy (EuPago)')
    method = 'multibanco'

    @property
    def settings_form_fields(self):
        """Estende os campos base com configurações específicas do Multibanco"""
        base_fields = super().settings_form_fields
        
        from collections import OrderedDict
        return OrderedDict(list(base_fields.items()) + [
            ('multibanco_description', forms.CharField(
                label=_('Payment description'),
                help_text=_('This will be displayed to customers during checkout'),
                required=False,
                initial=_('Pay via bank transfer using Multibanco reference'),
            )),
        ])

    def execute_payment(self, request: HttpRequest, payment: OrderPayment):
        """Execute Multibanco payment"""
        from .config import API_ENDPOINTS
        
        data = {
            'valor': str(payment.amount),
            'id': payment.full_id,
            'webhook_url': request.build_absolute_uri(reverse('plugins:eupago:webhook')),
        }

        try:
            response = self._make_api_request(
                API_ENDPOINTS['multibanco'], 
                data, 
                payment_method='multibanco'
            )
            
            if response.get('referencia'):
                payment.info = json.dumps(response)
                payment.state = OrderPayment.PAYMENT_STATE_PENDING
                payment.save(update_fields=['info', 'state'])
                return None  # Stay on same page, show payment reference
            else:
                raise PaymentException(_('Multibanco payment reference generation failed'))
                
        except Exception as e:
            logger.error(f'Multibanco payment failed: {e}')
            payment.fail(info={'error': str(e)})
            raise PaymentException(_('Multibanco payment failed. Please try again.'))

    def checkout_confirm_render(self, request, **kwargs) -> str:
        template = get_template('pretixplugins/eupago/checkout_multibanco_confirm.html')
        ctx = {
            'request': request,
            'event': self.event,
            'settings': self.settings,
            'provider': self,
        }
        return template.render(ctx)


class EuPagoPayShop(EuPagoBaseProvider):
    identifier = 'eupago_payshop'
    verbose_name = _('PayShop Legacy (EuPago)')
    method = 'payshop'

    @property
    def settings_form_fields(self):
        """Estende os campos base com configurações específicas do PayShop"""
        base_fields = super().settings_form_fields
        
        from collections import OrderedDict
        return OrderedDict(list(base_fields.items()) + [
            ('payshop_description', forms.CharField(
                label=_('Payment description'),
                help_text=_('This will be displayed to customers during checkout'),
                required=False,
                initial=_('Pay in cash at any PayShop location'),
            )),
        ])

    def execute_payment(self, request: HttpRequest, payment: OrderPayment):
        """Execute PayShop payment"""
        from .config import API_ENDPOINTS
        
        data = {
            'valor': str(payment.amount),
            'id': payment.full_id,
            'webhook_url': request.build_absolute_uri(reverse('plugins:eupago:webhook')),
        }

        try:
            response = self._make_api_request(
                API_ENDPOINTS['payshop'], 
                data, 
                payment_method='payshop'
            )
            
            if response.get('referencia'):
                payment.info = json.dumps(response)
                payment.state = OrderPayment.PAYMENT_STATE_PENDING
                payment.save(update_fields=['info', 'state'])
                return None  # Stay on same page, show payment reference
            else:
                raise PaymentException(_('PayShop payment reference generation failed'))
                
        except Exception as e:
            logger.error(f'PayShop payment failed: {e}')
            payment.fail(info={'error': str(e)})
            raise PaymentException(_('PayShop payment failed. Please try again.'))

    def checkout_confirm_render(self, request, **kwargs) -> str:
        template = get_template('pretixplugins/eupago/checkout_payshop_confirm.html')
        ctx = {
            'request': request,
            'event': self.event,
            'settings': self.settings,
            'provider': self,
        }
        return template.render(ctx)


class EuPagoPayByLink(EuPagoBaseProvider):
    identifier = 'eupago_paybylink'
    verbose_name = _('Pagamento Online (Legacy)')
    method = 'paybylink'
    payment_form_template_name = 'pretixplugins/eupago/checkout_payment_form_paybylink.html'

    @property
    def settings_form_fields(self):
        """Estende os campos base com configurações específicas do PayByLink"""
        base_fields = super().settings_form_fields
        
        from collections import OrderedDict
        return OrderedDict(list(base_fields.items()) + [
            ('paybylink_description', forms.CharField(
                label=_('Payment description'),
                help_text=_('This will be displayed to customers during checkout'),
                required=False,
                initial=_('Pay online with your preferred payment method'),
            )),
        ])

    def execute_payment(self, request: HttpRequest, payment: OrderPayment):
        """Execute PayByLink payment"""
        from .config import API_ENDPOINTS
        
        logger.info(f'EuPagoPayByLink.execute_payment called for {payment.full_id} - Amount: €{payment.amount}')
        
        # Preparar dados conforme API EuPago PayByLink
        # Construir as URLs diretamente usando os padrões corretos
        # Usar build_absolute_uri para cada URL sem tentativas de manipulação de string
        return_url_base = build_absolute_uri(
            self.event,
            'plugins:eupago:return',
            kwargs={
                'order': payment.order.code,
                'hash': payment.order.tagged_secret('plugins:eupago'),
                'payment': payment.pk,
            }
        )
        
        # URLs para os diferentes status usando o padrão específico
        success_url = build_absolute_uri(
            self.event,
            'plugins:eupago:return_with_status',
            kwargs={
                'order': payment.order.code,
                'hash': payment.order.tagged_secret('plugins:eupago'),
                'payment': payment.pk,
                'status': 'success'
            }
        )
        
        fail_url = build_absolute_uri(
            self.event,
            'plugins:eupago:return_with_status',
            kwargs={
                'order': payment.order.code,
                'hash': payment.order.tagged_secret('plugins:eupago'),
                'payment': payment.pk,
                'status': 'fail'
            }
        )
        
        back_url = build_absolute_uri(
            self.event,
            'plugins:eupago:return_with_status',
            kwargs={
                'order': payment.order.code,
                'hash': payment.order.tagged_secret('plugins:eupago'),
                'payment': payment.pk,
                'status': 'back'
            }
        )
        
        # Log das URLs para depuração
        logger.info(f"Base return URL: {return_url_base}")
        logger.info(f"Success URL: {success_url}")
        logger.info(f"Fail URL: {fail_url}")
        logger.info(f"Back URL: {back_url}")
        
        data = {
            'payment': {
                'amount': {
                    'currency': 'EUR',
                    'value': float(payment.amount)
                },
                'identifier': payment.full_id,  # Identificador único do pagamento
                'successUrl': success_url,
                'failUrl': fail_url,
                'backUrl': back_url
            },
            'urlReturn': return_url_base,
            'urlCallback': request.build_absolute_uri(reverse('plugins:eupago:webhook'))
        }
        
        # Adicionar descrição personalizada se configurada
        paybylink_description = self.settings.get('paybylink_description') or self.organizer.settings.get('eupago_paybylink_description')
        if paybylink_description:
            data['payment']['description'] = paybylink_description

        try:
            logger.info(f'Creating PayByLink payment for {payment.full_id}: €{payment.amount}')
            logger.info(f'PayByLink data being sent: {data}')
            
            response = self._make_api_request(
                API_ENDPOINTS['paybylink'], 
                data, 
                payment_method='paybylink'
            )
            
            logger.info(f'PayByLink API response for {payment.full_id}: {response}')
            
            # Verificar se a resposta contém URL de pagamento
            payment_url = None
            
            # Check for URL in different response structures
            if response.get('url'):
                payment_url = response.get('url')
            elif response.get('redirect_url'):
                payment_url = response.get('redirect_url')
            elif response.get('link'):
                payment_url = response.get('link')
            elif response.get('paymentUrl'):
                payment_url = response.get('paymentUrl')
            elif response.get('redirectUrl'):
                payment_url = response.get('redirectUrl')
            elif isinstance(response.get('data'), dict) and response.get('data').get('paymentUrl'):
                payment_url = response.get('data').get('paymentUrl')
                
            logger.info(f'Extracted payment URL: {payment_url}')
            
            if payment_url:
                # Guardar informações do pagamento
                payment_info = {
                    'payment_url': payment_url,
                    'transaction_id': (
                        response.get('transactionId') or 
                        response.get('id') or 
                        (response.get('data', {}).get('transactionId') if isinstance(response.get('data'), dict) else None)
                    ),
                    'reference': (
                        response.get('referencia') or 
                        response.get('reference') or 
                        (response.get('data', {}).get('reference') if isinstance(response.get('data'), dict) else None)
                    ),
                    'api_response': response,
                    'method': 'paybylink'
                }
                
                payment.info = json.dumps(payment_info)
                payment.state = OrderPayment.PAYMENT_STATE_PENDING
                payment.save(update_fields=['info', 'state'])
                
                logger.info(f'PayByLink payment {payment.full_id} initialized successfully')
                # NOTE: This payment is only set to PENDING state here.
                # The payment will be confirmed ONLY when we receive a webhook notification
                # from EuPago, not from the success URL redirect.
                # See views.py: _handle_payment_completed for the confirmation logic
                return payment_url
            else:
                error_msg = response.get('error') or response.get('message') or 'No payment URL returned'
                logger.error(f'PayByLink payment initialization failed for {payment.full_id}: {error_msg}')
                raise PaymentException(_('Payment initialization failed: {}').format(error_msg))
                
        except PaymentException:
            raise  # Re-raise PaymentExceptions
        except Exception as e:
            logger.error(f'PayByLink payment failed for {payment.full_id}: {e}', exc_info=True)
            payment.fail(info={'error': str(e), 'method': 'paybylink'})
            raise PaymentException(_('Payment failed. Please try again later.'))
    
    def checkout_prepare(self, request, cart):
        """Prepare checkout for PayByLink payment"""
        return True  # No special preparation needed
    
    def payment_is_valid_session(self, request):
        """Check if payment session is valid"""
        return True  # PayByLink payments are handled externally
    
    def checkout_confirm_render(self, request, **kwargs):
        """Render confirmation for PayByLink payment"""
        logger.info(f'EuPagoPayByLink.checkout_confirm_render called for event: {self.event.slug}')
        
        template = get_template('pretixplugins/eupago/checkout_payment_confirm_paybylink.html')
        ctx = {
            'request': request, 
            'event': self.event,
            'settings': self.settings,
            'provider': self,
            'total': request.session.get('cart_total', 0)
        }
        
        rendered = template.render(ctx)
        logger.info(f'EuPagoPayByLink.checkout_confirm_render - template rendered successfully (length: {len(rendered)})')
        
        return rendered

    def test_webhook_signature_validation(self, test_payload: str, test_signature: str, test_secret: str) -> dict:
        """Test webhook signature validation with provided values - for debugging only"""
        import hmac
        import hashlib
        import base64
        
        result = {
            'payload': test_payload,
            'signature': test_signature,
            'secret': test_secret,
            'validation_result': False,
            'expected_signature': None,
            'debug_info': {}
        }
        
        try:
            # Generate expected signature
            expected_signature_binary = hmac.new(
                test_secret.encode('utf-8'),
                test_payload.encode('utf-8'),
                hashlib.sha256
            ).digest()
            
            expected_signature_b64 = base64.b64encode(expected_signature_binary).decode('utf-8')
            result['expected_signature'] = expected_signature_b64
            
            # Validate
            received_signature_binary = base64.b64decode(test_signature)
            is_valid = hmac.compare_digest(expected_signature_binary, received_signature_binary)
            result['validation_result'] = is_valid
            
            result['debug_info'] = {
                'payload_length': len(test_payload),
                'secret_length': len(test_secret),
                'signature_length': len(test_signature),
                'expected_binary_length': len(expected_signature_binary),
                'received_binary_length': len(received_signature_binary),
            }
            
        except Exception as e:
            result['error'] = str(e)
            
        return result


class EuPagoMBCreditCard(EuPagoBaseProvider):
    """MB and Credit Card payment method using organizer-level configuration"""
    identifier = 'eupago_mb_creditcard'
    verbose_name = _('MB and Credit Card (EuPago)')
    method = 'paybylink'
    payment_form_template_name = 'pretixplugins/eupago/checkout_payment_form_mb_creditcard.html'

    @property
    def settings_form_fields(self):
        """Use base settings form fields - no method-specific configuration needed"""
        return super().settings_form_fields

    def _get_headers(self, payment_method: str = None) -> dict:
        """Override to use method-specific API key"""
        headers = {'Content-Type': 'application/json'}
        
        # Use method-specific API key
        api_key = self.get_setting("api_key")  # This will use the method-specific key due to get_setting override
        
        if api_key and payment_method:
            from .config import AUTH_METHODS
            if AUTH_METHODS.get(payment_method) == 'header':
                headers['Authorization'] = f'Bearer {api_key}'
                logger.debug(f'Adding method-specific API key to header for {payment_method}')
            elif AUTH_METHODS.get(payment_method) == 'oauth':
                headers['Authorization'] = f'Bearer {api_key}'
                logger.debug(f'Adding method-specific Bearer token for {payment_method}')
        
        return headers

    def _validate_webhook_signature(self, payload: str, signature: str) -> bool:
        """Override to use method-specific webhook secret"""
        import json, hmac, hashlib, base64, logging
        logger = logging.getLogger('pretix.plugins.eupago')

        # Use method-specific webhook secret
        webhook_secret = self.get_setting('webhook_secret') or ''
        if not webhook_secret:
            logger.warning('No MB/Credit Card webhook secret configured - skipping signature validation')
            return True

        if not signature:
            logger.warning('No webhook signature provided')
            return False

        # 2) decidir a mensagem a assinar
        try:
            body = json.loads(payload)
            if isinstance(body, dict) and isinstance(body.get('data'), str):
                # ENCRIPTADO: assina exatamente o string do campo "data"
                msg_bytes = body['data'].encode('utf-8')
            else:
                # NÃO ENCRIPTADO: assina o corpo inteiro
                msg_bytes = payload.encode('utf-8')
        except Exception:
            # JSON inválido → assina o corpo inteiro tal como chegou
            msg_bytes = payload.encode('utf-8')

        # 3) HMAC-SHA256 e comparação em tempo constante
        expected_bin = hmac.new(webhook_secret.encode('utf-8'), msg_bytes, hashlib.sha256).digest()
        try:
            received_bin = base64.b64decode(signature)
        except Exception as e:
            logger.error(f'Failed to base64-decode X-Signature: {e}')
            return False

        ok = hmac.compare_digest(expected_bin, received_bin)

        # debug
        if getattr(self, 'debug_mode', False) or not ok:
            logger.info(f'Expected signature (base64): {base64.b64encode(expected_bin).decode()}')
            logger.info(f'Received  signature (base64): {signature}')
            logger.info(f'Signatures match: {ok}')

        return ok

    def execute_payment(self, request: HttpRequest, payment: OrderPayment):
        """Execute MB and Credit Card payment using PayByLink"""
        from .config import API_ENDPOINTS
        
        logger.info(f'EuPagoMBCreditCard.execute_payment called for {payment.full_id} - Amount: €{payment.amount}')
        
        # Build return URLs
        return_url_base = build_absolute_uri(
            self.event,
            'plugins:eupago:return',
            kwargs={
                'order': payment.order.code,
                'hash': payment.order.tagged_secret('plugins:eupago'),
                'payment': payment.pk,
            }
        )
        
        success_url = build_absolute_uri(
            self.event,
            'plugins:eupago:return_with_status',
            kwargs={
                'order': payment.order.code,
                'hash': payment.order.tagged_secret('plugins:eupago'),
                'payment': payment.pk,
                'status': 'success'
            }
        )
        
        fail_url = build_absolute_uri(
            self.event,
            'plugins:eupago:return_with_status',
            kwargs={
                'order': payment.order.code,
                'hash': payment.order.tagged_secret('plugins:eupago'),
                'payment': payment.pk,
                'status': 'fail'
            }
        )
        
        back_url = build_absolute_uri(
            self.event,
            'plugins:eupago:return_with_status',
            kwargs={
                'order': payment.order.code,
                'hash': payment.order.tagged_secret('plugins:eupago'),
                'payment': payment.pk,
                'status': 'back'
            }
        )
        
        data = {
            'payment': {
                'amount': {
                    'currency': 'EUR',
                    'value': float(payment.amount)
                },
                'identifier': payment.full_id,
                'successUrl': success_url,
                'failUrl': fail_url,
                'backUrl': back_url
            },
            'urlReturn': return_url_base,
            'urlCallback': request.build_absolute_uri(reverse('plugins:eupago:webhook'))
        }
        
        # Add custom description if configured
        description = self.get_setting('description') or 'Pay with MB or Credit Card'
        data['payment']['description'] = description

        try:
            logger.info(f'Creating MB/Credit Card payment for {payment.full_id}: €{payment.amount}')
            
            response = self._make_api_request(
                API_ENDPOINTS['paybylink'], 
                data, 
                payment_method='paybylink'
            )
            
            logger.info(f'MB/Credit Card API response for {payment.full_id}: {response}')
            
            # Extract payment URL from response
            payment_url = (response.get('url') or 
                          response.get('redirect_url') or 
                          response.get('link') or 
                          response.get('paymentUrl') or 
                          response.get('redirectUrl'))
                          
            if isinstance(response.get('data'), dict):
                payment_url = payment_url or response.get('data').get('paymentUrl')
            
            if payment_url:
                payment_info = {
                    'payment_url': payment_url,
                    'transaction_id': (response.get('transactionId') or response.get('id') or
                                     (response.get('data', {}).get('transactionId') if isinstance(response.get('data'), dict) else None)),
                    'reference': (response.get('referencia') or response.get('reference') or
                                (response.get('data', {}).get('reference') if isinstance(response.get('data'), dict) else None)),
                    'api_response': response,
                    'method': 'mb_creditcard'
                }
                
                payment.info = json.dumps(payment_info)
                payment.state = OrderPayment.PAYMENT_STATE_PENDING
                payment.save(update_fields=['info', 'state'])
                
                logger.info(f'MB/Credit Card payment {payment.full_id} initialized successfully')
                return payment_url
            else:
                error_msg = response.get('error') or response.get('message') or 'No payment URL returned'
                logger.error(f'MB/Credit Card payment initialization failed for {payment.full_id}: {error_msg}')
                raise PaymentException(_('Payment initialization failed: {}').format(error_msg))
                
        except PaymentException:
            raise
        except Exception as e:
            logger.error(f'MB/Credit Card payment failed for {payment.full_id}: {e}', exc_info=True)
            payment.fail(info={'error': str(e), 'method': 'mb_creditcard'})
            raise PaymentException(_('Payment failed. Please try again later.'))

    def checkout_confirm_render(self, request, **kwargs):
        """Render confirmation for MB and Credit Card payment"""
        logger.info(f'EuPagoMBCreditCard.checkout_confirm_render called for event: {self.event.slug}')
        
        template = get_template('pretixplugins/eupago/checkout_payment_confirm_mb_creditcard.html')
        ctx = {
            'request': request, 
            'event': self.event,
            'settings': self.settings,
            'provider': self,
            'total': request.session.get('cart_total', 0)
        }
        
        rendered = template.render(ctx)
        logger.info(f'EuPagoMBCreditCard.checkout_confirm_render - template rendered successfully')
        
        return rendered


class EuPagoMBWayNew(EuPagoBaseProvider):
    """New MBWay payment method via PayByLink using organizer-level configuration"""
    identifier = 'eupago_mbway_new'
    verbose_name = _('MBWay')
    method = 'mbway_paybylink'

    @property
    def payment_form_fields(self):
        """No form fields needed - phone number will be entered on EuPago's page"""
        from collections import OrderedDict
        return OrderedDict()

    @property
    def settings_form_fields(self):
        """Use base settings form fields - no method-specific configuration needed"""
        return super().settings_form_fields

    def _get_headers(self, payment_method: str = None) -> dict:
        """Override to use method-specific API key"""
        headers = {'Content-Type': 'application/json'}
        
        # Use method-specific API key
        api_key = self.get_setting("api_key")  # This will use the method-specific key due to get_setting override
        
        if api_key and payment_method:
            from .config import AUTH_METHODS
            if AUTH_METHODS.get(payment_method) == 'header':
                headers['Authorization'] = f'Bearer {api_key}'
                logger.debug(f'Adding method-specific API key to header for {payment_method}')
            elif AUTH_METHODS.get(payment_method) == 'oauth':
                headers['Authorization'] = f'Bearer {api_key}'
                logger.debug(f'Adding method-specific Bearer token for {payment_method}')
        
        return headers

    def _validate_webhook_signature(self, payload: str, signature: str) -> bool:
        """Override to use method-specific webhook secret"""
        import json, hmac, hashlib, base64, logging
        logger = logging.getLogger('pretix.plugins.eupago')

        # Use method-specific webhook secret
        webhook_secret = self.get_setting('webhook_secret') or ''
        if not webhook_secret:
            logger.warning('No MBWay webhook secret configured - skipping signature validation')
            return True

        if not signature:
            logger.warning('No webhook signature provided')
            return False

        # 2) decidir a mensagem a assinar
        try:
            body = json.loads(payload)
            if isinstance(body, dict) and isinstance(body.get('data'), str):
                # ENCRIPTADO: assina exatamente o string do campo "data"
                msg_bytes = body['data'].encode('utf-8')
            else:
                # NÃO ENCRIPTADO: assina o corpo inteiro
                msg_bytes = payload.encode('utf-8')
        except Exception:
            msg_bytes = payload.encode('utf-8')

        # 3) HMAC-SHA256 e comparação em tempo constante
        expected_bin = hmac.new(webhook_secret.encode('utf-8'), msg_bytes, hashlib.sha256).digest()
        try:
            received_bin = base64.b64decode(signature)
        except Exception as e:
            logger.error(f'Failed to base64-decode X-Signature: {e}')
            return False

        ok = hmac.compare_digest(expected_bin, received_bin)

        # debug
        if getattr(self, 'debug_mode', False) or not ok:
            logger.info(f'Expected signature (base64): {base64.b64encode(expected_bin).decode()}')
            logger.info(f'Received  signature (base64): {signature}')
            logger.info(f'Signatures match: {ok}')

        return ok

    def execute_payment(self, request: HttpRequest, payment: OrderPayment):
        """Execute MBWay payment via PayByLink"""
        from .config import API_ENDPOINTS
        from pretix.multidomain.urlreverse import build_absolute_uri
        
        logger.info(f'EuPagoMBWayNew.execute_payment called for {payment.full_id} - Amount: €{payment.amount}')
        
        # Construir as URLs de retorno usando o mesmo padrão do PayByLink
        return_url_base = build_absolute_uri(
            self.event,
            'plugins:eupago:return',
            kwargs={
                'order': payment.order.code,
                'hash': payment.order.tagged_secret('plugins:eupago'),
                'payment': payment.pk,
            }
        )
        
        # URLs para os diferentes status
        success_url = build_absolute_uri(
            self.event,
            'plugins:eupago:return_with_status',
            kwargs={
                'order': payment.order.code,
                'hash': payment.order.tagged_secret('plugins:eupago'),
                'payment': payment.pk,
                'status': 'success'
            }
        )
        
        fail_url = build_absolute_uri(
            self.event,
            'plugins:eupago:return_with_status',
            kwargs={
                'order': payment.order.code,
                'hash': payment.order.tagged_secret('plugins:eupago'),
                'payment': payment.pk,
                'status': 'fail'
            }
        )
        
        back_url = build_absolute_uri(
            self.event,
            'plugins:eupago:return_with_status',
            kwargs={
                'order': payment.order.code,
                'hash': payment.order.tagged_secret('plugins:eupago'),
                'payment': payment.pk,
                'status': 'back'
            }
        )
        
        # Usar PayByLink API com preferência para MBWay
        data = {
            'payment': {
                'amount': {
                    'currency': 'EUR',
                    'value': float(payment.amount)
                },
                'identifier': payment.full_id,
                'successUrl': success_url,
                'failUrl': fail_url,
                'backUrl': back_url,
                'preferredMethod': 'mbway'  # Sugestão para mostrar MBWay como opção principal
            },
            'urlReturn': return_url_base,
            'urlCallback': request.build_absolute_uri(reverse('plugins:eupago:webhook'))
        }
        
        # Adicionar descrição personalizada se configurada
        mbway_description = self.get_setting('mbway_new_description') or self.get_setting('mbway_description')
        if mbway_description:
            data['payment']['description'] = mbway_description

        try:
            logger.info(f'Creating MBWay PayByLink payment for {payment.full_id}: €{payment.amount}')
            logger.info(f'MBWay PayByLink data being sent: {data}')
            
            response = self._make_api_request(
                API_ENDPOINTS['paybylink'], 
                data, 
                payment_method='paybylink'  # Use PayByLink endpoint
            )
            
            logger.info(f'MBWay PayByLink API response for {payment.full_id}: {response}')
            
            # Verificar se a resposta contém URL de pagamento
            payment_url = None
            
            # Check for URL in different response structures
            if response.get('url'):
                payment_url = response.get('url')
            elif response.get('redirect_url'):
                payment_url = response.get('redirect_url')
            elif response.get('link'):
                payment_url = response.get('link')
            elif response.get('paymentUrl'):
                payment_url = response.get('paymentUrl')
            elif response.get('redirectUrl'):
                payment_url = response.get('redirectUrl')
            elif isinstance(response.get('data'), dict) and response.get('data').get('paymentUrl'):
                payment_url = response.get('data').get('paymentUrl')
                
            logger.info(f'Extracted MBWay payment URL: {payment_url}')
            
            if payment_url:
                # Guardar informações do pagamento
                payment_info = {
                    'payment_url': payment_url,
                    'transaction_id': (
                        response.get('transactionId') or 
                        response.get('id') or 
                        (response.get('data', {}).get('transactionId') if isinstance(response.get('data'), dict) else None)
                    ),
                    'reference': (
                        response.get('referencia') or 
                        response.get('reference') or 
                        (response.get('data', {}).get('reference') if isinstance(response.get('data'), dict) else None)
                    ),
                    'api_response': response,
                    'method': 'mbway_paybylink',
                    'preferred_method': 'mbway'
                }
                
                payment.info = json.dumps(payment_info)
                payment.state = OrderPayment.PAYMENT_STATE_PENDING
                payment.save(update_fields=['info', 'state'])
                
                logger.info(f'MBWay PayByLink payment {payment.full_id} initialized successfully')
                # NOTE: This payment is only set to PENDING state here.
                # The payment will be confirmed ONLY when we receive a webhook notification
                # from EuPago, not from the success URL redirect.
                return payment_url
            else:
                error_msg = response.get('error') or response.get('message') or 'No payment URL returned'
                logger.error(f'MBWay PayByLink payment initialization failed for {payment.full_id}: {error_msg}')
                raise PaymentException(_('MBWay payment initialization failed: {}').format(error_msg))
                
        except PaymentException:
            raise  # Re-raise PaymentExceptions
        except Exception as e:
            logger.error(f'MBWay PayByLink payment failed for {payment.full_id}: {e}', exc_info=True)
            payment.fail(info={'error': str(e), 'method': 'mbway_paybylink'})
            raise PaymentException(_('MBWay payment failed. Please try again later.'))

    def checkout_confirm_render(self, request, **kwargs):
        """Render confirmation for MBWay PayByLink payment"""
        logger.info(f'EuPagoMBWayNew.checkout_confirm_render called for event: {self.event.slug}')
        
        template = get_template('pretixplugins/eupago/checkout_payment_confirm_paybylink.html')
        ctx = {
            'request': request, 
            'event': self.event,
            'settings': self.settings,
            'provider': self,
            'method_name': _('MBWay'),
            'payment_description': self.get_setting('mbway_new_description') or self.get_setting('mbway_description') or _('Pay with MBWay using your mobile phone'),
        }
        return template.render(ctx)
        
    def checkout_prepare(self, request, cart):
        """Prepare checkout for MBWay PayByLink payment"""
        return True  # No special preparation needed
    
    def payment_is_valid_session(self, request):
        """Check if payment session is valid"""
        return True  # PayByLink payments are handled externally
