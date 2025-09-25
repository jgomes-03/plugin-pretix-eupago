import json
import logging
from django.http import Http404, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.views.decorators.clickjacking import xframe_options_exempt
from django_scopes import scopes_disabled
from django.db import transaction
from django.template.loader import get_template
from django.utils import timezone

from pretix.base.models import Event, Order, OrderPayment, Quota
from pretix.control.views.organizer import OrganizerDetailViewMixin, OrganizerPermissionRequiredMixin
from django.views.generic import FormView
from django import forms
from pretix.base.forms import SettingsForm, SecretKeySettingsField
from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from django.urls import reverse

logger = logging.getLogger('pretix.plugins.eupago')


@method_decorator(xframe_options_exempt, 'dispatch')
class EuPagoReturnView(View):
    """Handle return from EuPago payment gateway"""
    
    def dispatch(self, request, *args, **kwargs):
        try:
            self.order = request.event.orders.get_with_secret_check(
                code=kwargs['order'], 
                received_secret=kwargs['hash'].lower(), 
                tag='plugins:eupago'
            )
        except Order.DoesNotExist:
            raise Http404('Unknown order')
            
        self.payment = get_object_or_404(
            self.order.payments,
            pk=self.kwargs['payment'],
            provider__startswith='eupago'
        )
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        # Handle return from payment gateway with different status
        from django.contrib import messages
        from pretix.multidomain.urlreverse import build_absolute_uri, eventreverse
        
        status = kwargs.get('status')
        logger.info(f'EuPagoReturnView.get called with status: {status} for payment {self.payment.full_id}')
        
        # Check if we got a specific status from EuPago
        if status == 'success':
            # Don't auto-confirm from success URL - wait for webhook confirmation
            # Instead, check current payment state and show appropriate message
            if self.payment.state == OrderPayment.PAYMENT_STATE_CONFIRMED:
                messages.success(request, _('Payment confirmed successfully!'))
            else:
                # Update payment info to indicate user returned via success URL
                payment_info = json.loads(self.payment.info or '{}')
                payment_info['success_url_returned'] = True
                payment_info['success_url_returned_at'] = timezone.now().isoformat()
                self.payment.info = json.dumps(payment_info)
                self.payment.save(update_fields=['info'])
                
                logger.info(f'Payment {self.payment.full_id} user returned via success URL - waiting for webhook confirmation')
                messages.info(request, _('Your payment is being processed. You will receive confirmation shortly.'))
                
            # Redirect to order page
            return redirect(eventreverse(
                self.order.event, 
                'presale:event.order', 
                kwargs={
                    'order': self.order.code,
                    'secret': self.order.secret
                }
            ))
            
        elif status == 'fail':
            # If payment failed, mark it as failed and allow the user to try again
            if self.payment.state not in [OrderPayment.PAYMENT_STATE_FAILED, OrderPayment.PAYMENT_STATE_CANCELED]:
                try:
                    logger.info(f'Marking payment {self.payment.full_id} as failed based on fail URL')
                    self.payment.fail(info={'reason': 'User returned from fail URL'})
                except Exception as e:
                    logger.error(f'Error marking payment {self.payment.full_id} as failed: {e}')
            
            messages.error(request, _('Your payment was not completed. Please try again or choose a different payment method.'))
            
            # Redirect to retry payment
            return redirect(eventreverse(
                self.order.event, 
                'presale:event.order.pay', 
                kwargs={
                    'order': self.order.code,
                    'secret': self.order.secret
                }
            ))
            
        elif status == 'back':
            # If user went back, cancel the current payment to allow starting a new one
            if self.payment.state == OrderPayment.PAYMENT_STATE_PENDING:
                self.payment.state = OrderPayment.PAYMENT_STATE_CANCELED
                self.payment.save(update_fields=['state'])
                logger.info(f'Payment {self.payment.pk} canceled due to user going back')
                
            messages.info(request, _('Payment process was interrupted. You can try again when ready.'))
            
            # Redirect to the order page as was originally intended
            return redirect(eventreverse(
                self.order.event, 
                'presale:event.order', 
                kwargs={
                    'order': self.order.code,
                    'secret': self.order.secret
                }
            ))
            
        else:
            # Default handler for normal return or unknown status
            if self.payment.state == OrderPayment.PAYMENT_STATE_CONFIRMED:
                messages.success(request, _('Payment confirmed successfully!'))
                
                # Redirect to order page
                return redirect(eventreverse(
                    self.order.event, 
                    'presale:event.order', 
                    kwargs={
                        'order': self.order.code,
                        'secret': self.order.secret
                    }
                ))
            elif self.payment.state == OrderPayment.PAYMENT_STATE_PENDING:
                messages.info(request, _('Payment is being processed. You will receive confirmation shortly.'))
                
                # Redirect to order page
                return redirect(eventreverse(
                    self.order.event, 
                    'presale:event.order', 
                    kwargs={
                        'order': self.order.code,
                        'secret': self.order.secret
                    }
                ))
            else:
                messages.error(request, _('Payment failed. Please try again.'))
                
                # Redirect to retry payment
                return redirect(eventreverse(
                    self.order.event, 
                    'presale:event.order.pay', 
                    kwargs={
                        'order': self.order.code,
                        'secret': self.order.secret
                    }
                ))


@method_decorator(xframe_options_exempt, 'dispatch')
class EuPagoMBWayWaitView(View):
    """MBWay payment waiting page with timer"""
    
    def dispatch(self, request, *args, **kwargs):
        try:
            self.order = request.event.orders.get_with_secret_check(
                code=kwargs['order'], 
                received_secret=kwargs['hash'].lower(), 
                tag='plugins:eupago'
            )
        except Order.DoesNotExist:
            raise Http404('Unknown order')
            
        self.payment = get_object_or_404(
            self.order.payments,
            pk=self.kwargs['payment'],
            provider='eupago_mbway'
        )
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        """Show MBWay waiting page"""
        from pretix.multidomain.urlreverse import build_absolute_uri, eventreverse
        
        # Check if payment is already confirmed
        if self.payment.state == OrderPayment.PAYMENT_STATE_CONFIRMED:
            return redirect(eventreverse(
                self.order.event, 
                'presale:event.order', 
                kwargs={
                    'order': self.order.code,
                    'secret': self.order.secret
                }
            ))
        
        # Check if payment failed or was cancelled
        if self.payment.state in [OrderPayment.PAYMENT_STATE_FAILED, OrderPayment.PAYMENT_STATE_CANCELED]:
            messages.error(request, _('MBWay payment was cancelled or failed. Please try again.'))
            return redirect(eventreverse(
                self.order.event, 
                'presale:event.order.pay', 
                kwargs={
                    'order': self.order.code,
                    'secret': self.order.secret
                }
            ))
        
        # Show waiting page
        template = get_template('pretixplugins/eupago/mbway_wait.html')
        
        # Get phone number from payment info
        payment_info = {}
        try:
            payment_info = json.loads(self.payment.info or '{}')
        except:
            pass
            
        phone = payment_info.get('customerPhone', '')
        
        ctx = {
            'request': request,
            'event': self.order.event,
            'order': self.order,
            'payment': self.payment,
            'phone': phone,
            'amount': self.payment.amount,
        }
        
        return HttpResponse(template.render(ctx))

    def post(self, request, *args, **kwargs):
        """Handle AJAX status checks"""
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # Optionally check with EuPago API for current status
            try:
                provider = self.payment.payment_provider
                if hasattr(provider, 'check_payment_status'):
                    api_status = provider.check_payment_status(self.payment)
                    logger.debug(f'API status check for payment {self.payment.full_id}: {api_status}')
            except Exception as e:
                logger.warning(f'API status check failed for payment {self.payment.full_id}: {e}')
            
            # Refresh payment from database in case it was updated
            self.payment.refresh_from_db()
            
            # Return current payment status as JSON
            status = {
                'state': self.payment.state,
                'state_display': self.payment.get_state_display(),
                'confirmed': self.payment.state == OrderPayment.PAYMENT_STATE_CONFIRMED,
                'failed': self.payment.state in [OrderPayment.PAYMENT_STATE_FAILED, OrderPayment.PAYMENT_STATE_CANCELED],
                'pending': self.payment.state == OrderPayment.PAYMENT_STATE_PENDING,
            }
            
            if status['confirmed']:
                from pretix.multidomain.urlreverse import eventreverse
                status['redirect_url'] = eventreverse(
                    self.order.event, 
                    'presale:event.order', 
                    kwargs={
                        'order': self.order.code,
                        'secret': self.order.secret
                    }
                )
            elif status['failed']:
                from pretix.multidomain.urlreverse import eventreverse
                status['redirect_url'] = eventreverse(
                    self.order.event, 
                    'presale:event.order.pay', 
                    kwargs={
                        'order': self.order.code,
                        'secret': self.order.secret
                    }
                )
            
            return HttpResponse(json.dumps(status), content_type='application/json')
        
        # Non-AJAX request - redirect back to get
        return redirect(request.path)


@csrf_exempt
@scopes_disabled()
def webhook(request, *args, **kwargs):
    """Handle EuPago webhook notifications - supports both GET and POST for testing"""
    
    try:
        logger.info(f'====== WEBHOOK RECEBIDO ======')
        logger.info(f'Webhook received: method={request.method}, content_type={request.content_type}')
        logger.info(f'Webhook headers: {dict(request.headers)}')
        logger.info(f'Webhook query params: {dict(request.GET)}')
        
        # Handle both POST (production) and GET (testing)
        if request.method == 'GET':
            # GET method - parameters in URL (for testing)
            logger.info('Processing GET webhook (test mode)')
            return _handle_webhook_v1(request)
        else:
            # POST method - normal webhook processing
            try:
                event_body = request.body.decode('utf-8').strip()
                logger.info(f'Webhook body: {event_body}')
                
                # Try to parse as JSON first (Webhooks 2.0)
                if event_body and event_body.startswith('{'):
                    try:
                        event_data = json.loads(event_body)
                        logger.info(f'Parsed webhook data: {event_data}')
                        return _handle_webhook_v2(request, event_data, event_body)
                    except json.JSONDecodeError as e:
                        logger.warning(f'Failed to parse JSON: {e}')
                
                # Not JSON, might be Webhooks 1.0 format (URL params or form data)
                logger.info('Webhook body is not JSON, checking for Webhooks 1.0 format')
                return _handle_webhook_v1(request)
            except UnicodeDecodeError as e:
                logger.error(f'Webhook body decode error: {e}')
                return HttpResponseBadRequest('Invalid body encoding')
            
    except Exception as e:
        logger.error(f'Webhook processing error: {e}', exc_info=True)
        return HttpResponse('Internal error', status=500)


def _handle_webhook_v2(request, event_data, event_body):
    """Handle Webhooks 2.0 format"""
    logger.info('Processing Webhooks 2.0 format')
    
    # Check for encrypted data
    if 'data' in event_data and isinstance(event_data['data'], str):
        # This is encrypted data - would need decryption logic
        logger.warning('Received encrypted webhook data - decryption not implemented')
        return HttpResponse('Encrypted webhooks not supported yet', status=501)
    
    # Extract transaction data (could be direct or in transactions array)
    transaction_data = None
    if 'transactions' in event_data:
        if isinstance(event_data['transactions'], list) and event_data['transactions']:
            transaction_data = event_data['transactions'][0]  # First transaction
        elif isinstance(event_data['transactions'], dict):
            transaction_data = event_data['transactions']
    else:
        # Direct format - the whole event_data is the transaction
        transaction_data = event_data
    
    if not transaction_data:
        logger.warning('No transaction data found in webhook')
        return HttpResponseBadRequest('Missing transaction data')
    
    # Find payment by identifier
    identifier = transaction_data.get('identifier') or transaction_data.get('identificador')
    reference = transaction_data.get('reference') or transaction_data.get('referencia')
    
    if not identifier and not reference:
        logger.warning('Missing identifier and reference in webhook')
        return HttpResponseBadRequest('Missing identifier and reference')
    
    # Try to find payment by identifier first, then by reference
    payment = _find_payment_by_identifiers(identifier, reference)
        
    if not payment:
        logger.warning(f'Payment not found for identifier={identifier}, reference={reference}')
        return HttpResponse('Payment not found', status=200)
    
    # Skip signature validation for testing (when no signature provided)
    webhook_signature = request.META.get('HTTP_X_SIGNATURE', '')
    if webhook_signature:
        provider = payment.payment_provider
        if provider and hasattr(provider, '_validate_webhook_signature'):
            if not provider._validate_webhook_signature(event_body, webhook_signature):
                logger.warning(f'Invalid webhook signature for payment: {payment.full_id}')
                return HttpResponseBadRequest('Invalid signature')
    else:
        logger.info('No webhook signature provided - skipping validation (test mode)')
    
    # Process the webhook
    try:
        with transaction.atomic():
            status = transaction_data.get('status', '').lower()
            
            logger.info(f'Processing webhook for payment {payment.full_id}: status={status}')
            
            if status == 'paid' or status == 'success':
                _handle_payment_completed(payment, transaction_data)
            elif status in ['error', 'failed', 'failure']:
                _handle_payment_failed(payment, transaction_data)
            elif status in ['cancel', 'cancelled']:
                _handle_payment_cancelled(payment, transaction_data)
            elif status == 'expired':
                _handle_payment_expired(payment, transaction_data)
            else:
                logger.info(f'Unhandled webhook status: {status} - updating payment info only')
                # Still update payment info
                payment.info = json.dumps(transaction_data)
                payment.save(update_fields=['info'])
            
        return HttpResponse('OK', status=200)
        
    except Exception as e:
        logger.error(f'Error processing webhook for payment {payment.full_id}: {e}', exc_info=True)
        return HttpResponse('Processing error', status=500)


def _find_payment_by_identifiers(identifier, reference):
    """Find payment by identifier or reference"""
    try:
        payment = None
        
        logger.info(f'Looking for payment: identifier="{identifier}", reference="{reference}"')
        
        # Try to find by identifier first - identifier might be in format "ORDER-P-ID"
        if identifier:
            # Parse the identifier in format "ORDER-P-ID" to extract order code and local_id
            if '-P-' in identifier:
                order_code, local_id = identifier.split('-P-', 1)
                try:
                    # First try by order code and local_id
                    payment = OrderPayment.objects.filter(
                        order__code=order_code,
                        local_id=local_id,
                        provider__startswith='eupago'
                    ).first()
                    logger.info(f'Search by parsed identifier {identifier} (order_code={order_code}, local_id={local_id}): {"Found" if payment else "Not found"}')
                except (ValueError, TypeError):
                    logger.info(f'Could not parse identifier {identifier} into order code and local ID')
            
            # If not found, try looking in info JSON field (might contain identifier)
            if not payment:
                from django.db.models import Q
                import json
                
                # Try to find payments that might have the identifier stored in info
                candidates = OrderPayment.objects.filter(
                    provider__startswith='eupago'
                ).order_by('-created')[:50]  # Limit to recent payments
                
                for p in candidates:
                    try:
                        # Check if info might contain our identifier
                        if p.info and isinstance(p.info, str):
                            info = json.loads(p.info)
                            if str(identifier) in json.dumps(info):
                                payment = p
                                logger.info(f'Found payment by searching info JSON: {p.full_id}')
                                break
                    except Exception as e:
                        logger.debug(f'Error checking info for payment {p.full_id}: {e}')
                
                if not payment:
                    logger.info(f'Could not find payment by identifier in info')
        
        # If not found and we have reference, try by reference
        if not payment and reference:
            # Try to find reference in info JSON
            from django.db.models import Q
            import json
            
            # Try to find payments that might have the reference stored in info
            candidates = OrderPayment.objects.filter(
                provider__startswith='eupago'
            ).order_by('-created')[:50]  # Limit to recent payments
            
            for p in candidates:
                try:
                    # Check if info might contain our reference
                    if p.info and isinstance(p.info, str):
                        info = json.loads(p.info)
                        if str(reference) in json.dumps(info):
                            payment = p
                            logger.info(f'Found payment by searching reference in info JSON: {p.full_id}')
                            break
                except Exception as e:
                    logger.debug(f'Error checking info for payment {p.full_id}: {e}')
        
        # Debug: List all payments to see what we have
        if not payment:
            all_payments = OrderPayment.objects.filter(provider__startswith='eupago')[:10]
            logger.info(f'Available EuPago payments: {[p.full_id for p in all_payments]}')
            
        return payment
        
    except Exception as e:
        logger.error(f'Error finding payment: {e}', exc_info=True)
        return None


def _handle_webhook_v1(request):
    """Handle Webhooks 1.0 format (URL parameters)"""
    try:
        logger.info('Processing Webhooks 1.0 format')
        
        # Extract parameters from GET or POST
        params = request.GET.dict()
        if not params and request.method == 'POST':
            params = request.POST.dict()
        
        logger.info(f'Webhook 1.0 params: {params}')
        
        # Required parameters for Webhooks 1.0
        required_params = ['referencia', 'identificador', 'valor']
        missing_params = [param for param in required_params if param not in params]
        
        if missing_params:
            logger.warning(f'Missing required parameters: {missing_params}')
            return HttpResponseBadRequest(f'Missing parameters: {", ".join(missing_params)}')
        
        # Find payment by identifier
        identifier = params.get('identificador')
        reference = params.get('referencia')
        
        logger.info(f'Searching for payment: identifier={identifier}, reference={reference}')
        
        payment = _find_payment_by_identifiers(identifier, reference)
            
        if not payment:
            logger.warning(f'Payment not found for identifier={identifier}, reference={reference}')
            return HttpResponse('Payment not found', status=200)
        
        # Webhooks 1.0 only sends notifications for paid transactions
        logger.info(f'Webhooks 1.0: Payment {payment.full_id} marked as paid')
        _handle_payment_completed(payment, params)
        
        return HttpResponse('OK', status=200)
        
    except Exception as e:
        logger.error(f'Error processing Webhooks 1.0: {e}', exc_info=True)
        return HttpResponse('Processing error', status=500)


def _handle_payment_completed(payment: OrderPayment, data: dict):
    """
    Handle completed payment webhook.
    
    Webhooks are the definitive source of payment confirmation from EuPago.
    Only mark payments as confirmed when receiving this webhook, not from success URL redirects.
    This ensures that the payment status in our system accurately reflects the payment processor's records.
    """
    try:
        if payment.state in (OrderPayment.PAYMENT_STATE_CONFIRMED, OrderPayment.PAYMENT_STATE_REFUNDED):
            logger.info(f'Payment {payment.full_id} already confirmed')
            return
        
        logger.info(f'====== CONFIRMANDO PAGAMENTO VIA WEBHOOK ======')
        logger.info(f'Updating payment {payment.full_id} info and confirming')
        logger.info(f'Current payment state: {payment.state} ({payment.get_state_display()})')
        logger.info(f'Payment data: {data}')
        
        # Preserve any existing info when updating with webhook data
        try:
            existing_info = json.loads(payment.info or '{}')
            # Merge webhook data with existing info
            merged_info = {**existing_info, **data, 'webhook_confirmed_at': timezone.now().isoformat()}
            payment.info = json.dumps(merged_info)
            logger.info(f'Successfully merged payment info with webhook data')
        except Exception as json_error:
            # If any error occurs with merging, just use the webhook data
            logger.warning(f'Error merging payment info: {json_error}')
            payment.info = json.dumps({**data, 'webhook_confirmed_at': timezone.now().isoformat()})
        
        payment.save(update_fields=['info'])
        
        # Confirm the payment - this is the ONLY place where payments should be confirmed
        try:
            payment.confirm()
            logger.info(f'Payment {payment.full_id} confirmed via webhook successfully')
            logger.info(f'New payment state: {payment.state} ({payment.get_state_display()})')
        except Exception as confirm_error:
            logger.error(f'Error during payment.confirm(): {confirm_error}', exc_info=True)
            raise
        
    except Exception as e:
        logger.error(f'Error confirming payment {payment.full_id}: {e}', exc_info=True)


def _handle_payment_failed(payment: OrderPayment, data: dict):
    """Handle failed payment webhook"""
    if payment.state == OrderPayment.PAYMENT_STATE_FAILED:
        logger.info(f'Payment {payment.full_id} already marked as failed')
        return
        
    # Mark payment as failed
    payment.fail(info=data)
    logger.info(f'Payment {payment.full_id} marked as failed via webhook')


def _handle_payment_cancelled(payment: OrderPayment, data: dict):
    """Handle cancelled payment webhook"""
    if payment.state == OrderPayment.PAYMENT_STATE_CANCELED:
        logger.info(f'Payment {payment.full_id} already marked as cancelled')
        return
        
    # Mark payment as cancelled
    payment.state = OrderPayment.PAYMENT_STATE_CANCELED
    payment.info = json.dumps(data)
    payment.save(update_fields=['state', 'info'])
    
    logger.info(f'Payment {payment.full_id} marked as cancelled via webhook')


def _handle_payment_expired(payment: OrderPayment, data: dict):
    """Handle expired payment webhook"""
    if payment.state == OrderPayment.PAYMENT_STATE_CANCELED:
        logger.info(f'Payment {payment.full_id} already marked as expired/cancelled')
        return
        
    # Mark payment as cancelled (expired)
    payment.state = OrderPayment.PAYMENT_STATE_CANCELED
    payment.info = json.dumps(data)
    payment.save(update_fields=['state', 'info'])
    
    logger.info(f'Payment {payment.full_id} marked as expired via webhook')


def _handle_payment_pending(payment: OrderPayment, data: dict):
    """Handle pending payment webhook"""
    if payment.state != OrderPayment.PAYMENT_STATE_CREATED:
        # Update payment info but keep current state
        payment.info = json.dumps(data)
        payment.save(update_fields=['info'])
        
    logger.info(f'Payment {payment.full_id} updated with pending status via webhook')


class EuPagoSettingsForm(SettingsForm):
    """Form for EuPago global settings"""
    
    eupago_api_key = SecretKeySettingsField(
        label=_('API Key'),
        help_text=_('Your EuPago API key'),
        required=False,
    )
    eupago_client_id = forms.CharField(
        label=_('Client ID'),
        help_text=_('Your EuPago Client ID'),
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Client ID', 'class': 'form-control'})
    )
    eupago_client_secret = SecretKeySettingsField(
        label=_('Client Secret'),
        help_text=_('Your EuPago Client Secret'),
        required=False,
    )
    eupago_webhook_secret = SecretKeySettingsField(
        label=_('Webhook Secret'),
        help_text=_('Secret key for webhook signature validation'),
        required=False,
    )
    eupago_channel_id = forms.CharField(
        label=_('Channel ID'),
        help_text=_('Your EuPago Channel ID (found in backoffice under Channels)'),
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Channel ID', 'class': 'form-control'})
    )
    eupago_endpoint = forms.ChoiceField(
        label=_('Endpoint'),
        help_text=_('Choose between sandbox (testing) and live environment'),
        choices=[
            ('sandbox', _('Sandbox')),
            ('live', _('Live')),
        ],
        initial='sandbox',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    eupago_cc_description = forms.CharField(
        label=_('Credit Card Description'),
        help_text=_('Description shown to customers for credit card payments'),
        initial='Pay securely with your credit card',
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Credit card payment description',
            'class': 'form-control'
        })
    )
    eupago_mbway_description = forms.CharField(
        label=_('MBWay Description'),
        help_text=_('Description shown to customers for MBWay payments'),
        initial='Pay with MBWay using your mobile phone',
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'MBWay payment description',
            'class': 'form-control'
        })
    )
    eupago_multibanco_description = forms.CharField(
        label=_('Multibanco Description'),
        help_text=_('Description shown to customers for Multibanco payments'),
        initial='Pay via bank transfer using Multibanco reference',
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Multibanco payment description',
            'class': 'form-control'
        })
    )
    eupago_payshop_description = forms.CharField(
        label=_('PayShop Description'),
        help_text=_('Description shown to customers for PayShop payments'),
        initial='Pay in cash at any PayShop location',
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'PayShop payment description',
            'class': 'form-control'
        })
    )


class EuPagoSettingsView(OrganizerDetailViewMixin, OrganizerPermissionRequiredMixin, FormView):
    """View for managing EuPago global settings"""
    
    template_name = 'pretixplugins/eupago/admin/settings.html'
    form_class = EuPagoSettingsForm
    permission = 'can_change_organizer_settings'
    
    def get_success_url(self):
        return reverse('plugins:eupago:settings', kwargs={
            'organizer': self.request.organizer.slug
        })
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['obj'] = self.request.organizer
        return kwargs
    
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        # Handle payment status check if requested
        if 'check_payment_status' in request.POST:
            payment_id = request.POST.get('payment_id', '').strip()
            return self._handle_payment_status_check(payment_id)
        
        # Handle manual webhook simulation if requested
        if 'simulate_webhook' in request.POST:
            payment_id = request.POST.get('payment_id', '').strip()
            status = request.POST.get('webhook_status', 'paid').strip()
            return self._handle_simulate_webhook(payment_id, status)
        
        # Handle normal form submission
        form = self.get_form()
        if form.is_valid():
            form.save()
            if form.has_changed():
                self.request.organizer.log_action(
                    'pretix.organizer.settings', user=self.request.user, data={
                        k: form.cleaned_data.get(k) for k in form.changed_data
                    }
                )
                
                # Forçar a atualização das configurações
                from django.core.cache import cache
                cache_keys = [f'settings_organizer_{self.request.organizer.pk}']
                for key in cache_keys:
                    cache.delete(key)
                
            messages.success(self.request, _('Your changes have been saved.'))
            return redirect(self.get_success_url())
        else:
            messages.error(self.request, _('We could not save your changes. See below for details.'))
            return self.get(request)
    
    def _handle_payment_status_check(self, payment_id: str):
        """Handle manual payment status check request"""
        if not payment_id:
            messages.error(self.request, _('Please provide a payment ID.'))
            return redirect(self.get_success_url())
        
        try:
            # Find the payment using the helper function
            payment = _find_payment_by_identifiers(payment_id, payment_id)
            
            # Make sure the payment belongs to this organizer
            if payment and payment.order.event.organizer != self.request.organizer:
                payment = None
            
            if not payment:
                messages.error(self.request, _('Payment not found or does not belong to this organizer.'))
                return redirect(self.get_success_url())
            
            # Get payment provider and check status
            provider = payment.payment_provider
            if not provider or not hasattr(provider, 'check_payment_status'):
                messages.error(self.request, _('Payment provider does not support status checking.'))
                return redirect(self.get_success_url())
            
            # Check payment status
            status_response = provider.check_payment_status(payment)
            
            if 'error' in status_response:
                messages.error(self.request, _('Error checking payment status: {}').format(status_response['error']))
            else:
                # Try to update payment status
                if hasattr(provider, 'process_webhook_payment_update'):
                    status_changed = provider.process_webhook_payment_update(payment, status_response)
                    if status_changed:
                        messages.success(self.request, _('Payment status updated successfully! Payment {} is now {}').format(
                            payment_id, payment.get_state_display()
                        ))
                    else:
                        status = status_response.get('status') or status_response.get('transactionStatus') or status_response.get('estado', 'unknown')
                        messages.info(self.request, _('Payment status checked. Current status: {} (no update needed)').format(status))
                else:
                    status = status_response.get('status') or status_response.get('transactionStatus') or status_response.get('estado', 'unknown')
                    messages.info(self.request, _('Payment status: {}').format(status))
                    
        except Exception as e:
            logger.error(f'Error in manual payment status check: {e}', exc_info=True)
            messages.error(self.request, _('An error occurred while checking payment status.'))
        
        return redirect(self.get_success_url())
        
    def _handle_simulate_webhook(self, payment_id: str, status: str = 'paid'):
        """Handle manual webhook simulation"""
        if not payment_id:
            messages.error(self.request, _('Please provide a payment ID for webhook simulation.'))
            return redirect(self.get_success_url())
        
        try:
            # Find the payment using our helper function that properly handles the full_id
            payment = _find_payment_by_identifiers(payment_id, payment_id)
            
            # Make sure the payment belongs to this organizer
            if payment and payment.order.event.organizer != self.request.organizer:
                payment = None
            
            if not payment:
                messages.error(self.request, _('Payment not found or does not belong to this organizer.'))
                return redirect(self.get_success_url())
                
            # Create webhook simulation data
            webhook_data = {
                'identifier': payment.full_id,  # This is fine here as we're just using the property
                'reference': payment.full_id,
                'status': status,
                'amount': float(payment.amount),
                'currency': 'EUR',
                'timestamp': timezone.now().isoformat(),
                'simulated': True,
                'simulation_source': f'manual-admin-{self.request.user.id}'
            }
            
            logger.info(f'Manual webhook simulation for payment {payment_id} with status {status}')
            
            # Process the simulated webhook
            if status.lower() == 'paid' or status.lower() == 'success':
                _handle_payment_completed(payment, webhook_data)
                messages.success(self.request, _('Payment {} was manually marked as confirmed via simulated webhook.').format(payment_id))
            elif status.lower() in ['failed', 'error']:
                _handle_payment_failed(payment, webhook_data)
                messages.warning(self.request, _('Payment {} was manually marked as failed via simulated webhook.').format(payment_id))
            elif status.lower() in ['cancelled', 'canceled']:
                _handle_payment_cancelled(payment, webhook_data)
                messages.info(self.request, _('Payment {} was manually marked as cancelled via simulated webhook.').format(payment_id))
            else:
                messages.error(self.request, _('Unknown webhook status: {}').format(status))
                
            # Refresh the payment to get its new status
            payment.refresh_from_db()
            messages.info(self.request, _('Payment status is now: {}').format(payment.get_state_display()))
            
        except Exception as e:
            logger.error(f'Error in manual webhook simulation: {e}', exc_info=True)
            messages.error(self.request, _('An error occurred during webhook simulation.'))
            
        return redirect(self.get_success_url())
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('EuPago Settings')
        
        # Add some statistics for the organizer
        from django.utils.timezone import now
        from datetime import timedelta
        
        # Recent payments statistics
        recent_payments = OrderPayment.objects.filter(
            provider__startswith='eupago',
            order__event__organizer=self.request.organizer,
            created__gte=now() - timedelta(days=7)
        )
        
        context['recent_stats'] = {
            'total_payments': recent_payments.count(),
            'pending_payments': recent_payments.filter(state=OrderPayment.PAYMENT_STATE_PENDING).count(),
            'confirmed_payments': recent_payments.filter(state=OrderPayment.PAYMENT_STATE_CONFIRMED).count(),
            'failed_payments': recent_payments.filter(state=OrderPayment.PAYMENT_STATE_FAILED).count(),
        }
        
        return context
