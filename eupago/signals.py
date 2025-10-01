from django.dispatch import receiver
from pretix.base.signals import register_payment_providers
from pretix.control.signals import nav_organizer
from django.urls import reverse
from django.utils.translation import gettext_lazy as _


@receiver(register_payment_providers, dispatch_uid="payment_eupago")
def register_payment_provider(sender, **kwargs):
    from .payment import (
        EuPagoCreditCard, 
        EuPagoMBWay, 
        EuPagoMultibanco, 
        EuPagoPayShop, 
        EuPagoPayByLink,
        EuPagoMBCreditCard,
        EuPagoMBWayNew
    )
    import logging
    
    logger = logging.getLogger('pretix.plugins.eupago')
    logger.info('Registering EuPago v2 payment providers')
    
    return [
        # New payment methods with specific configurations
        EuPagoMBCreditCard,  # Uses MB/CC specific API key and webhook secret
        EuPagoMBWayNew,      # Uses MBWay specific API key and webhook secret (PayByLink)
        
        # Legacy/existing methods (use general configuration)
        EuPagoCreditCard,    # Uses general API key and webhook secret
        EuPagoMBWay,         # Uses general API key and webhook secret (Legacy MBWay direct API)
        EuPagoMultibanco,    # Uses general API key and webhook secret
        EuPagoPayShop,       # Uses general API key and webhook secret
        EuPagoPayByLink,     # Uses general API key and webhook secret (Generic PayByLink)
    ]


@receiver(nav_organizer, dispatch_uid="eupago_nav_organizer")
def nav_organizer_settings(sender, request, organizer, **kwargs):
    """Add EuPago to organizer navigation (Settings section)"""
    return [{
        'label': _('EuPago'),
        'url': reverse('plugins:eupago:settings', kwargs={'organizer': organizer.slug}),
        'active': request.resolver_match and request.resolver_match.url_name == 'settings',
        'icon': 'credit-card',
    }]
