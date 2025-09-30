# EuPago Plugin v2 - New Payment Methods Implementation

## Overview

The EuPago plugin has been enhanced to support dedicated API keys and webhook secrets for different payment methods. This allows for better organization and security by separating configurations for different payment types.

## New Payment Methods

### 1. MB and Credit Card (EuPago)
- **Identifier**: `eupago_mb_creditcard`
- **Description**: Combined MB (Multibanco) and Credit Card payment method
- **Uses**: PayByLink API endpoint
- **Configuration**: Dedicated API key and webhook secret

### 2. MBWay (EuPago) - New Implementation
- **Identifier**: `eupago_mbway_new`
- **Description**: MBWay payment with dedicated configuration
- **Uses**: MBWay API endpoint
- **Configuration**: Dedicated API key and webhook secret

## Legacy Payment Methods

The following payment methods are now marked as "Legacy" and continue to use the default (shared) API key and webhook secret:

- **Pagamento Online (Legacy)** - `eupago_paybylink`
- **Credit Card (EuPago)** - `eupago_cc`
- **MBWay (EuPago)** - `eupago_mbway`
- **Multibanco (EuPago)** - `eupago_multibanco`
- **PayShop (EuPago)** - `eupago_payshop`

## Configuration Settings

### Organizer-Level Settings

Each payment method can now have its own configuration:

#### Default/Legacy Settings
- `api_key` - Default API key (used by legacy methods)
- `webhook_secret` - Default webhook secret (used by legacy methods)
- `endpoint` - Sandbox or Live environment

#### MB and Credit Card Settings
- `mb_creditcard_api_key` - Dedicated API key for MB/Credit Card payments
- `mb_creditcard_webhook_secret` - Dedicated webhook secret for MB/Credit Card payments
- `mb_creditcard_description` - Payment method description

#### MBWay New Settings
- `mbway_new_api_key` - Dedicated API key for new MBWay payments
- `mbway_new_webhook_secret` - Dedicated webhook secret for new MBWay payments
- `mbway_new_description` - Payment method description

## Technical Implementation

### Settings Resolution
The payment providers use a cascading settings resolution:

1. **Method-specific settings**: `payment_eupago_{method_prefix}_{setting_name}`
2. **Default settings**: `payment_eupago_{setting_name}`
3. **Legacy settings**: `eupago_{setting_name}`

### Webhook Handling
The webhook system automatically determines which webhook secret to use based on:

1. **Payment identification**: Find the payment by identifier/reference
2. **Provider detection**: Determine which payment provider was used
3. **Secret selection**: Use the appropriate webhook secret for signature validation

### API Key Usage
Each payment method uses its dedicated API key when available:

- **New methods** (MB/Credit Card, MBWay New): Always use dedicated API keys
- **Legacy methods**: Use default API key

### Security Features
- **Dedicated secrets**: Each payment method can have its own webhook secret
- **Signature validation**: Each method validates webhooks using its specific secret
- **Fallback support**: If dedicated secrets are not configured, falls back to default

## Migration Guide

### For New Installations
1. Configure the new payment methods with their dedicated API keys and webhook secrets
2. Enable the desired payment methods in Pretix
3. Test with sandbox environment before going live

### For Existing Installations
1. Existing configurations will continue to work (backward compatibility)
2. Gradually migrate to new payment methods by:
   - Configuring dedicated API keys and webhook secrets
   - Enabling new payment methods
   - Optionally disabling legacy methods

### Configuration Example

```python
# Organizer Settings
settings = {
    # Default/Legacy configuration
    'payment_eupago_api_key': 'default-api-key',
    'payment_eupago_webhook_secret': 'default-webhook-secret',
    
    # MB and Credit Card configuration
    'payment_eupago_mb_creditcard_api_key': 'mb-cc-api-key',
    'payment_eupago_mb_creditcard_webhook_secret': 'mb-cc-webhook-secret',
    
    # MBWay New configuration
    'payment_eupago_mbway_new_api_key': 'mbway-api-key',
    'payment_eupago_mbway_new_webhook_secret': 'mbway-webhook-secret',
}
```

## API Endpoints Used

- **MB and Credit Card**: `/api/v1.02/paybylink/create`
- **MBWay New**: `/api/v1.02/mbway/create`
- **Legacy methods**: Various endpoints (unchanged)

## Templates Created

- `checkout_payment_form_mb_creditcard.html` - Payment form for MB/Credit Card
- `checkout_payment_confirm_mb_creditcard.html` - Confirmation page for MB/Credit Card
- `checkout_payment_confirm_mbway_new.html` - Confirmation page for new MBWay

## Testing

### Sandbox Testing
1. Configure sandbox API keys for each payment method
2. Set `endpoint` to 'sandbox'
3. Test payment flows for each method
4. Verify webhook notifications are received and processed correctly

### Production Deployment
1. Configure production API keys for each payment method
2. Set `endpoint` to 'live'
3. Update webhook URLs in EuPago dashboard
4. Monitor payment processing and webhook delivery

## Troubleshooting

### Common Issues
1. **Webhook validation fails**: Check that correct webhook secret is configured for the payment method
2. **API authentication fails**: Verify API key configuration for the specific payment method
3. **Payment not found**: Ensure webhook identifies the correct payment using identifier/reference

### Debugging
- Enable debug mode: `debug_mode = True`
- Check logs for webhook signature validation details
- Verify API key and webhook secret configurations

## EuPago Documentation Reference

For complete API documentation, refer to: https://eupago.readme.io

This includes:
- API endpoints and parameters
- Webhook payload formats
- Authentication methods
- Testing procedures
