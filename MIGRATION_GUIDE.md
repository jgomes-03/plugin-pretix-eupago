# Migration Guide: EuPago Plugin v2 New Payment Methods

## Summary of Changes

This update introduces **two new payment methods** with **dedicated API keys and webhook secrets**:

1. **MB and Credit Card (EuPago)** - `eupago_mb_creditcard`
2. **MBWay (EuPago)** - `eupago_mbway_new`

The existing **"Pagamento Online"** method is now labeled as **"Legacy"** and continues to work with your current configuration.

## What You Need to Do

### Step 1: Get New API Credentials from EuPago

Contact EuPago to obtain **separate API keys and webhook secrets** for:
- MB and Credit Card payments
- MBWay payments

### Step 2: Configure New Payment Methods

In your Pretix organizer settings, you'll see new configuration options:

#### MB and Credit Card Settings
- **MB and Credit Card API Key**: Enter the dedicated API key for MB/CC payments
- **MB and Credit Card Webhook Secret**: Enter the dedicated webhook secret for MB/CC
- **Description**: Customize the payment method description (optional)

#### MBWay New Settings
- **MBWay New API Key**: Enter the dedicated API key for MBWay payments
- **MBWay New Webhook Secret**: Enter the dedicated webhook secret for MBWay
- **Description**: Customize the payment method description (optional)

### Step 3: Enable New Payment Methods

1. Go to your event settings
2. Navigate to "Payment" section
3. Enable the new payment methods:
   - ✅ **MB and Credit Card (EuPago)**
   - ✅ **MBWay (EuPago)**

### Step 4: Update EuPago Webhook Configuration

In your EuPago dashboard, configure webhooks for each payment method to point to:
```
https://yourdomain.com/eupago/webhook/
```

Make sure each payment method uses its respective webhook secret.

### Step 5: Test the Configuration

1. Set your environment to **Sandbox** initially
2. Create test orders using each new payment method
3. Verify that payments are processed correctly
4. Check that webhook notifications are received and payments are confirmed

### Step 6: Go Live

1. Switch from **Sandbox** to **Live** environment
2. Update API keys to production keys
3. Test with small amounts first
4. Monitor payment processing

## Backward Compatibility

✅ **Your existing setup will continue to work unchanged**

- The **"Pagamento Online (Legacy)"** method keeps using your current API key and webhook secret
- All existing payments and configurations remain functional
- You can migrate to new methods gradually

## Benefits of New Implementation

1. **Better Organization**: Separate API credentials for different payment types
2. **Enhanced Security**: Dedicated webhook secrets for each payment method
3. **Improved Monitoring**: Easier to track and debug specific payment types
4. **Flexibility**: Enable/disable payment methods independently

## Rollback Plan

If you encounter issues:
1. **Disable new payment methods** in event settings
2. **Keep using the legacy method** until issues are resolved
3. **Contact support** for assistance

## Support

If you need help with:
- Obtaining new API credentials from EuPago
- Configuring the new payment methods
- Testing or troubleshooting

Please refer to the full documentation in `NEW_PAYMENT_METHODS.md` or contact your system administrator.

---

**Important**: The new payment methods provide the same functionality as before but with better configuration management. Users will see clearer payment options, and you'll have better control over each payment type.
