from django.dispatch import receiver
from pretix.base.signals import register_payment_providers
from pretix.control.signals import nav_organizer
from django.urls import reverse
from django.utils.translation import gettext_lazy as _


@receiver(register_payment_providers, dispatch_uid="payment_eupago")
def register_payment_provider(sender, **kwargs):
    from .payment import EuPagoCreditCard, EuPagoMBWay, EuPagoMultibanco, EuPagoPayShop, EuPagoPayByLink
    import logging
    
    logger = logging.getLogger('pretix.plugins.eupago')
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
    return [{
        'label': _('EuPago'),
        'url': reverse('plugins:eupago:settings', kwargs={'organizer': organizer.slug}),
        'active': request.resolver_match and request.resolver_match.url_name == 'settings',
        'icon': 'credit-card',
    }]
