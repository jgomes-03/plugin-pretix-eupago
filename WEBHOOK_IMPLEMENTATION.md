# EuPago Webhook Implementation Documentation

## Overview
This document describes the webhook implementation for the EuPago payment gateway integration with Pretix, covering both Webhooks 1.0 and 2.0 formats.

## API Endpoints

### Sandbox Environment
- Base URL: `https://sandbox.eupago.pt`
- Backoffice: `https://sandbox.eupago.com`

### Live/Production Environment
- Base URL: `https://clientes.eupago.pt`
- Backoffice: `https://clientes.eupago.com`

## Authentication

### PayByLink API (MB and Credit Card, MBWay via PayByLink)
**Format:** `Authorization: ApiKey xxxx-xxxx-xxxx-xxxx-xxxx`

The API key must be prefixed with `"ApiKey "` (with space) in the Authorization header:
```python
headers['Authorization'] = f'ApiKey {api_key}'
```

### Legacy Methods (Credit Card Legacy, MBWay Legacy)
**Format:** `Authorization: ApiKey xxxx-xxxx-xxxx-xxxx-xxxx`

Same format as PayByLink.

### OAuth Methods
**Format:** `Authorization: Bearer {token}`

Used for some advanced payment methods.

## Webhook Formats

### Webhooks 1.0 (Legacy)

**Method:** GET with URL parameters

**Important:** Webhooks 1.0 only send notifications for **PAID** transactions. No notifications for expired, cancelled, or refunded transactions.

**Parameters:**
- `valor` - Payment amount
- `canal` - Channel name where reference was created
- `referencia` - Reference number
- `transacao` - Transaction ID
- `identificador` - Identifier (our payment ID in format "ORDER-P-ID")
- `mp` - Payment Method Code:
  - `PC:PT` - Multibanco
  - `PS:PT` - Payshop
  - `MW:PT` - MB WAY
  - `CC:PT` - Credit Card
  - `PF:PT` - Paysafecard
  - `DD:PT` - Direct Debit
  - `CP:PT` - CofidisPay
  - `GP:PT` - Google Pay
  - `PA:PT` - Apple Pay
  - `PX:PT` - PIX
- `chave_api` - API Key used to create the reference
- `data` - Payment date and time (YYYY-MM-DD:hh:mm)
- `entidade` - Entity
- `comissao` - Payment Fee
- `local` - Payment City

**Example URL:**
```
https://example.com/webhook?valor=2.00&canal=channel_name&referencia=102087857&transacao=10409241&identificador=ORDER-P-123&mp=PC:PT&chave_api=xxxx-xxxx-xxxx-xxxx&data=yyyy-mm-dd:hh:mm&entidade=82307&comissao=1.14&local=xxxx
```

**Configuration:**
Set webhook URL in EuPago backoffice:
1. Channels → Channel Listing
2. Click pencil to edit channel
3. Check "Receive notification for a URL"
4. Paste your webhook URL

### Webhooks 2.0 (Current)

**Method:** POST with JSON body

**Important:** Webhooks 2.0 can notify about multiple transaction statuses: PAID, REFUND, ERROR, CANCEL, EXPIRED

**Configuration Options:**
- `endpoint` - URL where notification should be sent
- `method` - HTTP method (POST)
- `status` - Which statuses to communicate: PAID, REFUND, ERROR, CANCEL, EXPIRED
- `encrypt` - Whether to encrypt request body (true/false)

**Retry Policy:**
- Every 5 minutes, up to 3 attempts
- If still unsuccessful, retries hourly for 24 hours
- Always waits for HTTP 200 response to consider communication successful

#### Unencrypted Format (encrypt=false)

**Request Body:**
```json
{
  "transactions": {
    "entity": 12345,
    "reference": 102087857,
    "identifier": "ORDER-P-123",
    "method": "Multibanco",
    "amount": {
      "value": 10.50,
      "currency": "EUR"
    },
    "fees": {
      "value": 0.25,
      "currency": "EUR"
    },
    "date": "2025-10-10T14:30:00Z",
    "trid": 10409241,
    "status": "Paid"
  },
  "channel": {
    "name": "channel_name"
  }
}
```

**Headers:**
- `Content-Type: application/json`
- `X-Signature: base64_encoded_signature` - HMAC-SHA256 signature for authenticity

#### Encrypted Format (encrypt=true)

**Request Body:**
```json
{
  "data": "base64_encoded_encrypted_data"
}
```

**Headers:**
- `Content-Type: application/json`
- `X-Signature: base64_encoded_signature` - HMAC-SHA256 of the "data" field value
- `X-Initialization-Vector: base64_encoded_iv` - IV for AES-256-CBC decryption

**Decryption:**
- Algorithm: AES-256-CBC (symmetric encryption)
- Requirements:
  1. Base64-encoded encrypted text in "data" field
  2. Initialization Vector (IV) from X-Initialization-Vector header
  3. Encryption key (same as webhook secret)

**Decrypted content:** Full JSON structure with transactions and channel objects

### Transaction Status Values

| Status | Description |
|--------|-------------|
| `Paid` | Transaction successfully paid |
| `Refund` | Transaction refunded |
| `Error` | Transaction failed with error |
| `Cancel` | Transaction cancelled |
| `Expired` | Transaction expired |

## Signature Validation

### Purpose
Ensures authenticity and integrity of webhook data - verifies data has not been tampered with during transmission.

### Algorithm
HMAC-SHA256 with base64 encoding

### Implementation

```python
def _validate_webhook_signature(self, payload: str, signature: str) -> bool:
    """
    Validate webhook signature
    
    For encrypted webhooks (with "data" field):
      - Sign the exact string value of the "data" field
    
    For unencrypted webhooks:
      - Sign the entire raw request body
    """
    webhook_secret = self.get_setting('webhook_secret') or ''
    if not webhook_secret:
        logger.warning('No webhook secret configured - skipping validation')
        return True  # Allow in development
    
    if not signature:
        logger.warning('No webhook signature provided')
        return False
    
    # Determine what to sign
    try:
        body = json.loads(payload)
        if isinstance(body, dict) and isinstance(body.get('data'), str):
            # Encrypted: sign the "data" field value
            msg_bytes = body['data'].encode('utf-8')
        else:
            # Unencrypted: sign entire body
            msg_bytes = payload.encode('utf-8')
    except Exception:
        # Invalid JSON: sign entire body as-is
        msg_bytes = payload.encode('utf-8')
    
    # Calculate HMAC-SHA256
    expected_bin = hmac.new(
        webhook_secret.encode('utf-8'),
        msg_bytes,
        hashlib.sha256
    ).digest()
    
    # Compare in constant time
    try:
        received_bin = base64.b64decode(signature)
    except Exception as e:
        logger.error(f'Failed to decode signature: {e}')
        return False
    
    return hmac.compare_digest(expected_bin, received_bin)
```

### PHP Example (from EuPago docs)
```php
function verifySignature($data, $signature, $key) {
    $generatedSignature = hash_hmac('sha256', $data, $key, true);
    return hash_equals($generatedSignature, base64_decode($signature));
}
```

## Payment Confirmation Logic

### Critical Rule
**Webhooks are the ONLY definitive source of payment confirmation.**

### Why Not Success URL?
- Success URL redirects can be spoofed
- Network issues may prevent redirect
- User may close browser before redirect completes
- `transactionStatus: Success` in API response only means transaction was **created**, not **paid**

### Correct Implementation

```python
def _handle_payment_completed(payment: OrderPayment, data: dict):
    """
    Handle completed payment webhook.
    
    This is the ONLY place where payments should be confirmed.
    """
    if payment.state == OrderPayment.PAYMENT_STATE_CONFIRMED:
        return  # Already confirmed
    
    # Update payment info
    payment.info = json.dumps({
        **data,
        'webhook_confirmed_at': timezone.now().isoformat()
    })
    payment.save(update_fields=['info'])
    
    # Confirm payment
    payment.confirm()
    logger.info(f'Payment {payment.full_id} confirmed via webhook')
```

### What Success URL Should Do
- Show friendly message to user
- Mark that user returned via success URL (for tracking)
- **Do NOT confirm payment** - wait for webhook

```python
if status == 'success':
    # Don't auto-confirm - wait for webhook
    if self.payment.state == OrderPayment.PAYMENT_STATE_CONFIRMED:
        messages.success(request, _('Payment confirmed!'))
    else:
        # Just track the return
        payment_info = json.loads(self.payment.info or '{}')
        payment_info['success_url_returned'] = True
        self.payment.info = json.dumps(payment_info)
        self.payment.save(update_fields=['info'])
        
        messages.info(request, _('Processing... You will receive confirmation shortly.'))
```

## Webhook URL Configuration

### Pretix Global Webhook URL
```
https://your-domain.com/_eupago/webhook/
```

### Important Notes
1. **Single URL for all events** - webhook handler uses scopes_disabled() to access payments across all events
2. **Always returns HTTP 200** - even for errors, to prevent EuPago retries for non-retryable errors
3. **No authentication required** - signature validation provides security

## Security Considerations

### Production Checklist
✅ **Debug endpoint disabled** - `debug_webhook_secret` path commented out in urls.py
✅ **Signature validation enabled** - webhook_secret configured in organizer settings
✅ **HTTPS enforced** - all webhook URLs must use HTTPS in production
✅ **API keys secured** - stored in organizer settings, never in code
✅ **Logging sanitized** - API keys shown as "[CONFIGURED]" in logs, not full values

### Debug Mode Settings
```python
# In organizer settings
eupago_debug_mode = False  # MUST be False in production
```

When debug mode is enabled:
- Signature validation errors are logged in detail
- Invalid signatures may be accepted for testing
- Additional debug information is logged

**WARNING:** Never enable debug mode in production!

## Testing

### Sandbox Testing
1. Configure sandbox environment:
   - `endpoint = 'sandbox'`
   - Use sandbox API key from sandbox.eupago.com backoffice
   - Set webhook URL in sandbox backoffice

2. Create test payment
3. Complete payment in sandbox environment
4. Verify webhook is received and processed correctly
5. Check payment is confirmed in Pretix

### Production Deployment
1. Switch to live environment:
   - `endpoint = 'live'`
   - Use production API key from clientes.eupago.com backoffice
   - Update webhook URL in production backoffice

2. Monitor logs for first real transactions
3. Verify webhook signature validation works
4. Confirm payment confirmations are working

## Common Issues and Solutions

### Issue: Webhook signature validation fails
**Solution:**
- Verify webhook_secret matches the one configured in EuPago backoffice
- Check that signature is calculated on correct data (entire body for unencrypted, "data" field for encrypted)
- Ensure secret is stored correctly (check for extra spaces or encoding issues)

### Issue: Payment not found in webhook
**Solution:**
- Check identifier format matches "ORDER-P-ID" pattern
- Verify payment exists in database with correct provider (eupago_*)
- Check payment info contains reference/identifier for lookup

### Issue: API authentication fails (401)
**Solution:**
- Verify API key format: `Authorization: ApiKey xxxx-xxxx-xxxx-xxxx-xxxx`
- Check API key is correct for environment (sandbox vs live)
- Ensure API key has correct permissions in EuPago backoffice

### Issue: Webhook decryption fails
**Solution:**
- Verify X-Initialization-Vector header is present
- Check encryption key matches webhook secret
- Ensure base64 decoding is working correctly
- Verify AES-256-CBC algorithm parameters

## References

- [EuPago API Documentation](https://eupago.readme.io/reference)
- [Webhooks 1.0 Documentation](https://eupago.readme.io/reference/webhooks)
- [Webhooks 2.0 Documentation](https://eupago.readme.io/reference/realtime-webhooks-20)
- [PayByLink API Documentation](https://eupago.readme.io/reference/paybylink)
- [EuPago Help Center](https://eupago.atlassian.net/servicedesk/customer/portals)

## Support

For EuPago-specific issues:
- Email: suporte@eupago.pt
- Support Form: [EuPago Support Portal](https://eupago.atlassian.net/servicedesk/customer/portal/5/group/19/create/70)
