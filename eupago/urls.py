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

# Do NOT place settings or control views here. 
# organizer_patterns are served on the organizer's custom domain (public-facing views only).
organizer_patterns = []

# Global & Control Panel URLs
urlpatterns = [
    # Control Panel Organizer Settings (Always served on the main domain)
    path(
        'control/organizer/<slug:organizer>/settings/eupago/',
        EuPagoSettingsView.as_view(),
        name='settings'
    ),
    
    # Webhooks & callbacks
    re_path(
        r'^_eupago/webhook/$',
        webhook,
        name='webhook'
    ),
    re_path(
        r'^_eupago/test_webhook/$',
        lambda request: HttpResponse('Webhook test endpoint is working!', status=200),
        name='test_webhook'
    ),
    path('webhook/', webhook, name='webhook'),
    path('return/<slug:order>/<str:hash>/<int:payment>/', EuPagoReturnView.as_view(), name='return'),
    path('mbway_wait/<slug:order>/<str:hash>/<int:payment>/', EuPagoMBWayWaitView.as_view(), name='mbway_wait'),
]