from django.utils.translation import gettext_lazy as _
from pretix.base.settings import GlobalSettingsObject
from pretix.base.forms import SecretKeySettingsField
from django import forms


class EuPagoGlobalSettingsHolder:
    """Global settings holder for EuPago v2 plugin"""
    
    identifier = 'eupago'
    verbose_name = _('EuPago')
    
    @property 
    def settings_form_fields(self):
        return {
            'api_key': SecretKeySettingsField(
                label=_('API Key'),
                help_text=_('Your EuPago API key'),
                required=False,
            ),
            'client_id': forms.CharField(
                label=_('Client ID'),
                help_text=_('Your EuPago Client ID'),
                required=False,
                widget=forms.TextInput(attrs={'placeholder': 'Client ID'})
            ),
            'client_secret': SecretKeySettingsField(
                label=_('Client Secret'),
                help_text=_('Your EuPago Client Secret'),
                required=False,
            ),
            'webhook_secret': SecretKeySettingsField(
                label=_('Webhook Secret'),
                help_text=_('Secret key for webhook signature validation'),
                required=False,
            ),
            'endpoint': forms.ChoiceField(
                label=_('Endpoint'),
                help_text=_('Choose between sandbox (testing) and live environment'),
                choices=[
                    ('sandbox', _('Sandbox')),
                    ('live', _('Live')),
                ],
                initial='sandbox',
                widget=forms.Select()
            ),
            'cc_description': forms.CharField(
                label=_('Credit Card Description'),
                help_text=_('Description shown to customers for credit card payments'),
                initial='Pay securely with your credit card',
                required=False,
                widget=forms.TextInput(attrs={'placeholder': 'Credit card payment description'})
            ),
            'mbway_description': forms.CharField(
                label=_('MBWay Description'),
                help_text=_('Description shown to customers for MBWay payments'),
                initial='Pay with MBWay using your mobile phone',
                required=False,
                widget=forms.TextInput(attrs={'placeholder': 'MBWay payment description'})
            ),
            'multibanco_description': forms.CharField(
                label=_('Multibanco Description'),
                help_text=_('Description shown to customers for Multibanco payments'),
                initial='Pay via bank transfer using Multibanco reference',
                required=False,
                widget=forms.TextInput(attrs={'placeholder': 'Multibanco payment description'})
            ),
            'payshop_description': forms.CharField(
                label=_('PayShop Description'),
                help_text=_('Description shown to customers for PayShop payments'),
                initial='Pay in cash at any PayShop location',
                required=False,
                widget=forms.TextInput(attrs={'placeholder': 'PayShop payment description'})
            ),
            
            # New payment methods - MB and Credit Card
            'mb_creditcard_api_key': SecretKeySettingsField(
                label=_('MB and Credit Card API Key'),
                help_text=_('Dedicated API key for MB and Credit Card payments'),
                required=False,
            ),
            'mb_creditcard_webhook_secret': SecretKeySettingsField(
                label=_('MB and Credit Card Webhook Secret'),
                help_text=_('Dedicated webhook secret for MB and Credit Card payments'),
                required=False,
            ),
            'mb_creditcard_description': forms.CharField(
                label=_('MB and Credit Card Description'),
                help_text=_('Description shown to customers for MB and Credit Card payments'),
                initial='Pay with MB or Credit Card',
                required=False,
                widget=forms.TextInput(attrs={'placeholder': 'MB and Credit Card payment description'})
            ),
            
            # New payment methods - MBWay New
            'mbway_new_api_key': SecretKeySettingsField(
                label=_('MBWay New API Key'),
                help_text=_('Dedicated API key for new MBWay payments'),
                required=False,
            ),
            'mbway_new_webhook_secret': SecretKeySettingsField(
                label=_('MBWay New Webhook Secret'),
                help_text=_('Dedicated webhook secret for new MBWay payments'),
                required=False,
            ),
            'mbway_new_description': forms.CharField(
                label=_('MBWay New Description'),
                help_text=_('Description shown to customers for new MBWay payments'),
                initial='Pay with MBWay using your mobile phone',
                required=False,
                widget=forms.TextInput(attrs={'placeholder': 'MBWay payment description'})
            ),
        }
