import logging
from django.dispatch import receiver
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from pretix.base.signals import register_payment_providers
from pretix.control.signals import nav_organizer

logger = logging.getLogger('pretix.plugins.eupago')


@receiver(register_payment_providers, dispatch_uid="payment_eupago")
def register_payment_provider(sender, **kwargs):
    from .payment import (
        EuPagoCreditCard,
        EuPagoMBWay,
        EuPagoMultibanco,
        EuPagoPayByLink,
        EuPagoPayShop,
    )
    
    logger.info('Registering EuPago v2 payment providers')
    
    return [
        EuPagoCreditCard,
        EuPagoMBWay, 
        EuPagoMultibanco,
        EuPagoPayShop,
        EuPagoPayByLink,
    ]


@receiver(nav_organizer, dispatch_uid="eupago_nav_organizer")
def nav_organizer_settings(sender, request, organizer, **kwargs):
    """Add EuPago to organizer navigation (Settings section)"""
    
    # 1. Permission check: Hide link if user lacks settings permissions
    if not request.user.has_organizer_permission(organizer, 'can_change_organizer_settings', request=request):
        return []

    # 2. Namespace check: Avoid false active highlights on other settings pages
    is_active = (
        request.resolver_match
        and request.resolver_match.namespace == 'plugins:eupago'
        and request.resolver_match.url_name == 'settings'
    )

    return [{
        'label': _('EuPago'),
        'url': reverse('plugins:eupago:settings', kwargs={'organizer': organizer.slug}),
        'active': is_active,
        'icon': 'credit-card',
    }]