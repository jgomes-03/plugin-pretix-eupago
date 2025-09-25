import json
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
from django.test import TestCase, RequestFactory

from pretix.base.models import Event, Organizer, OrderPayment
from eupago.payment import EuPagoCreditCard, EuPagoMBWay, EuPagoMultibanco, EuPagoPayShop


class EuPagoTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.organizer = Organizer.objects.create(name='Test Organizer', slug='test')
        self.event = Event.objects.create(
            organizer=self.organizer,
            name='Test Event',
            slug='test',
            date_from=timezone.now() + timedelta(days=30),
            currency='EUR'
        )
        
        # Set up EuPago settings
        self.event.settings.payment_eupago_api_key = 'test_api_key'
        self.event.settings.payment_eupago_client_id = 'test_client_id'
        self.event.settings.payment_eupago_client_secret = 'test_client_secret'
        self.event.settings.payment_eupago_endpoint = 'sandbox'

    def test_credit_card_provider_initialization(self):
        provider = EuPagoCreditCard(self.event)
        self.assertEqual(provider.identifier, 'eupago_cc')
        self.assertEqual(provider.method, 'creditcard')
        self.assertTrue(provider.is_allowed(self.factory.get('/')))

    def test_mbway_provider_initialization(self):
        provider = EuPagoMBWay(self.event)
        self.assertEqual(provider.identifier, 'eupago_mbway')
        self.assertEqual(provider.method, 'mbway')
        self.assertTrue(provider.is_allowed(self.factory.get('/')))

    def test_multibanco_provider_initialization(self):
        provider = EuPagoMultibanco(self.event)
        self.assertEqual(provider.identifier, 'eupago_multibanco')
        self.assertEqual(provider.method, 'multibanco')
        self.assertTrue(provider.is_allowed(self.factory.get('/')))

    def test_payshop_provider_initialization(self):
        provider = EuPagoPayShop(self.event)
        self.assertEqual(provider.identifier, 'eupago_payshop')
        self.assertEqual(provider.method, 'payshop')
        self.assertTrue(provider.is_allowed(self.factory.get('/')))

    def test_settings_validation(self):
        # Test with missing settings
        event_no_settings = Event.objects.create(
            organizer=self.organizer,
            name='Test Event No Settings',
            slug='test-no-settings',
            date_from=timezone.now() + timedelta(days=30),
            currency='EUR'
        )
        
        provider = EuPagoCreditCard(event_no_settings)
        self.assertFalse(provider._check_settings())

    def test_api_base_url(self):
        provider = EuPagoCreditCard(self.event)
        
        # Test sandbox URL
        self.assertEqual(provider._get_api_base_url(), 'https://sandbox.eupago.pt')
        
        # Test live URL
        self.event.settings.payment_eupago_endpoint = 'live'
        self.assertEqual(provider._get_api_base_url(), 'https://api.eupago.pt')

    @patch('requests.post')
    def test_api_request_success(self, mock_post):
        provider = EuPagoCreditCard(self.event)
        
        # Mock successful API response
        mock_response = Mock()
        mock_response.json.return_value = {'status': 'success', 'payment_url': 'https://example.com/pay'}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        result = provider._make_api_request('/payments', {'test': 'data'})
        self.assertEqual(result['status'], 'success')

    @patch('requests.post')
    def test_api_request_failure(self, mock_post):
        provider = EuPagoCreditCard(self.event)
        
        # Mock failed API response
        mock_post.side_effect = Exception('API Error')
        
        with self.assertRaises(PaymentException):
            provider._make_api_request('/payments', {'test': 'data'})

    def test_webhook_signature_validation(self):
        provider = EuPagoCreditCard(self.event)
        self.event.settings.payment_eupago_webhook_secret = 'test_secret'
        
        # Test with valid signature
        payload = '{"test": "data"}'
        expected_signature = hmac.new(
            'test_secret'.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        self.assertTrue(provider._validate_webhook_signature(payload, expected_signature))
        
        # Test with invalid signature
        self.assertFalse(provider._validate_webhook_signature(payload, 'invalid_signature'))
