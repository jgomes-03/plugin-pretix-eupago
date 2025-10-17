from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

__version__ = '2.0'


class PluginApp(AppConfig):
    name = 'eupago'
    verbose_name = 'Payment Provider EuPago'

    class PretixPluginMeta:
        name = _('EuPago')
        author = 'Jorge Gomes'
        category = 'PAYMENT'
        description = _('Aceite pagamentos via EuPago')
        visible = True
        version = __version__
        compatibility = "pretix>=2.7.0"

    def ready(self):
        from . import signals  # noqa


default_app_config = 'eupago.PluginApp'
