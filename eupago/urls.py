from django.urls import include, re_path, path
from django.http import HttpResponse
from .views import (
    EuPagoReturnView, EuPagoMBWayWaitView, webhook, EuPagoSettingsView,
    debug_webhook_secret
)

event_patterns = [
    re_path(r'^eupago/', include([
        re_path(
            r'^return/(?P<order>[^/]+)/(?P<hash>[^/]+)/(?P<payment>[0-9]+)(/(?P<status>[^/]+))?/$',
            EuPagoReturnView.as_view(),
            name='return'
        ),
        # Padrões adicionais para URLs com status explícito
        re_path(
            r'^return/(?P<order>[^/]+)/(?P<hash>[^/]+)/(?P<payment>[0-9]+)/(?P<status>success|fail|back)/$',
            EuPagoReturnView.as_view(),
            name='return_with_status'
        ),
        re_path(
            r'^mbway-wait/(?P<order>[^/]+)/(?P<hash>[^/]+)/(?P<payment>[0-9]+)/$',
            EuPagoMBWayWaitView.as_view(),
            name='mbway_wait'
        ),
    ])),
]

# Organizer-level patterns for settings
organizer_patterns = [
    path('settings/eupago/', EuPagoSettingsView.as_view(), name='settings'),
]

# Global webhook URL - same for all events and organizers
urlpatterns = [
    re_path(
        r'^_eupago/webhook/$',
        webhook,
        name='webhook'
    ),
    # Teste de webhook - para diagnóstico
    re_path(
        r'^_eupago/test_webhook/$',
        lambda request: HttpResponse('Webhook test endpoint is working!', status=200),
        name='test_webhook'
    ),
    path('webhook/', webhook, name='webhook'),
    path('return/<slug:order>/<str:hash>/<int:payment>/', EuPagoReturnView.as_view(), name='return'),
    path('mbway_wait/<slug:order>/<str:hash>/<int:payment>/', EuPagoMBWayWaitView.as_view(), name='mbway_wait'),
    path('settings/<slug:organizer>/', EuPagoSettingsView.as_view(), name='settings'),
    
    # Debug endpoint - disabled in production, enable only for troubleshooting
    # path('debug_webhook_secret/', debug_webhook_secret, name='debug_webhook_secret'),
]
