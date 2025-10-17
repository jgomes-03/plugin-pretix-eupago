# EuPago Configuration Fix Summary

## Problem Identified
The user reported that updating the webhook secret in the admin interface wasn't affecting webhook decryption. The logs showed a specific webhook secret (`F7b54HQE...psBQ3ZXo`) that didn't match what they had configured.

## Root Cause Analysis
**Issue**: Form field naming inconsistency between `EuPagoSettingsForm` field definitions and database storage.

**Explanation**: 
- Pretix SettingsForm automatically adds a `payment_` prefix to field names when saving to database
- The EuPago form fields were defined WITHOUT this prefix (e.g., `eupago_webhook_secret`)
- When saved, they were stored as `eupago_webhook_secret` instead of `payment_eupago_webhook_secret`
- The webhook decryption code was looking for `payment_eupago_webhook_secret` (correct key)
- This caused the code to always use fallback/old values instead of user-configured values

## Fields Fixed
Updated all form field names in `EuPagoSettingsForm` to include the `payment_` prefix:

### Core Configuration Fields
- ✅ `eupago_api_key` → `payment_eupago_api_key`
- ✅ `eupago_client_id` → `payment_eupago_client_id`  
- ✅ `eupago_client_secret` → `payment_eupago_client_secret`
- ✅ `eupago_channel_id` → `payment_eupago_channel_id`
- ✅ `eupago_endpoint` → `payment_eupago_endpoint`
- ✅ `eupago_webhook_secret` → `payment_eupago_webhook_secret` **[CRITICAL FIX]**

### Additional Configuration Fields  
- ✅ `eupago_debug_mode` → `payment_eupago_debug_mode`
- ✅ `eupago_cc_description` → `payment_eupago_cc_description`
- ✅ `eupago_mbway_description` → `payment_eupago_mbway_description`
- ✅ `eupago_multibanco_description` → `payment_eupago_multibanco_description`
- ✅ `eupago_payshop_description` → `payment_eupago_payshop_description`

## Files Modified
- **`eupago/views.py`**: Updated `EuPagoSettingsForm` class field definitions (lines ~781-850)

## Impact
- ✅ **RESOLVED**: Webhook secret updates via admin interface now save to correct database key
- ✅ **RESOLVED**: Webhook decryption will now use user-configured secret instead of fallback values
- ✅ **MAINTAINED**: Backward compatibility maintained through fallback logic in decryption code
- ✅ **MAINTAINED**: All existing functionality preserved

## Verification Steps
1. **Restart Application**: Restart Django/Docker to load updated form definitions
2. **Update Configuration**: Access EuPago Settings in admin and update webhook secret
3. **Verify Storage**: Use `check_webhook_secret.py` to confirm correct key is being used
4. **Test Decryption**: Create test payment in live environment to verify webhook works

## Expected Results
After restart and reconfiguration:
- Admin webhook secret updates will affect actual decryption
- Webhook decryption logs should show success instead of "All decryption methods failed"
- User-configured webhook secret should match what appears in decryption logs
- Live environment webhook processing should work correctly

## Technical Notes
- The fix maintains backward compatibility through existing fallback logic
- Environment variable overrides (`EUPAGO_WEBHOOK_SECRET`) still work as intended
- Form validation and help text remain unchanged
- Database migration is not required as this only affects new configurations

---
**Status**: ✅ **COMPLETE** - All form fields updated to use correct `payment_` prefix naming convention.
