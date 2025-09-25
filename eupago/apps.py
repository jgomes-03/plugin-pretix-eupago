from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

__version__ = '2.1.1'


class PluginApp(AppConfig):
    name = 'eupago'
    verbose_name = 'EuPago Payment Provider'

    class PretixPluginMeta:
        name = _('EuPago')
        author = 'EuPago Integration Team'
        category = 'PAYMENT'
        description = _('Accept payments via EuPago (Credit Card, MBWay, Multibanco, PayShop)')
        visible = True
        version = __version__
        compatibility = "pretix>=2.7.0"

    def ready(self):
        from . import signals  # noqa


default_app_config = 'eupago.PluginApp'
