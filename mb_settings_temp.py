    @property
    def settings_form_fields(self):
        """Configurações específicas do PayByLink MB - organizador level"""
        from collections import OrderedDict
        from pretix.base.forms import SecretKeySettingsField
        
        fields = OrderedDict([
            ('paybylink_mb_description', forms.CharField(
                label=_('Payment description'),
                help_text=_('This will be displayed to customers during checkout'),
                required=False,
                initial=_('Pay via Multibanco or MB WAY'),
            )),
            ('paybylink_mb_canal', forms.CharField(
                label=_('Channel ID for MB/MB WAY'),
                help_text=_('EuPago channel ID for Multibanco and MB WAY payments'),
                required=True,
            )),
            ('paybylink_mb_api_key', SecretKeySettingsField(
                label=_('API Key for MB/MB WAY'),
                help_text=_('Your EuPago API key for this specific channel'),
                required=True,
            )),
            ('paybylink_mb_webhook_secret', SecretKeySettingsField(
                label=_('Webhook Secret for MB/MB WAY'),
                help_text=_('Secret key for webhook validation for this channel'),
                required=False,
            )),
            ('paybylink_mb_endpoint', forms.ChoiceField(
                label=_('Environment for MB/MB WAY'),
                choices=[
                    ('sandbox', _('Sandbox (Testing)')),
                    ('live', _('Live (Production)')),
                ],
                initial='sandbox',
                help_text=_('Choose sandbox for testing or live for production'),
            )),
        ])
        return fields
