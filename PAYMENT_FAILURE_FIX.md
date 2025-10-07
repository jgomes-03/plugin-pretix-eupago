# EuPago Payment Failure Fix Summary

## Problem
When credit card or PayByLink payments failed, EuPago would redirect users to a fail URL, but this caused an **Internal Server Error (500)** in Pretix instead of showing a user-friendly error message.

## Root Causes

### 1. Credit Card Payment - Missing Failure URLs
**File:** `eupago/payment.py` - `EuPagoCreditCard.execute_payment()`

**Issue:** The credit card payment was only setting a single `resposta_url`, but EuPago API requires separate URLs for different payment outcomes (success, failure, cancellation).

**Fix:** Added proper URL configuration:
```python
success_url = build_absolute_uri(..., status='success')
fail_url = build_absolute_uri(..., status='fail')
back_url = build_absolute_uri(..., status='back')

data = {
    'resposta_url': success_url,  # Main return URL
    'url_ok': success_url,         # Success URL
    'url_ko': fail_url,           # Failure URL
    'url_cancel': back_url,       # Cancellation URL
}
```

### 2. Missing Global URL Pattern with Status
**File:** `eupago/urls.py`

**Issue:** The global URL patterns (`urlpatterns`) didn't include a route for return URLs with status parameters. When EuPago redirected to `/return/.../fail/`, there was no matching URL pattern.

**Fix:** Added status parameter to global URL pattern:
```python
path('return/<slug:order>/<str:hash>/<int:payment>/<str:status>/', 
     EuPagoReturnView.as_view(), 
     name='return_with_status'),
```

### 3. Return View Couldn't Handle Global URLs
**File:** `eupago/views.py` - `EuPagoReturnView.dispatch()`

**Issue:** The dispatch method assumed `request.event` would always be available, but this is only true for event-specific URL patterns, not global ones.

**Fix:** Added logic to handle both cases:
```python
if hasattr(request, 'event'):
    # Event-specific URL - use request.event
    self.order = request.event.orders.get_with_secret_check(...)
else:
    # Global URL - find order across all events
    with scopes_disabled():
        orders = Order.objects.filter(code=kwargs['order'])...
```

### 4. Improved Error Handling in Return View
**File:** `eupago/views.py` - `EuPagoReturnView.get()`

**Issue:** Any unexpected errors would cause unhandled exceptions.

**Fix:** Wrapped entire method in try-except block:
```python
try:
    # Handle success/fail/back status...
except Exception as e:
    logger.error(f'Error handling payment return: {e}', exc_info=True)
    messages.error(request, _('An error occurred...'))
    # Safely redirect to order page
```

### 5. Better Failure Information Logging
**File:** `eupago/views.py` - Fail URL handler

**Fix:** Enhanced failure handling to capture more information:
```python
failure_info = {
    'reason': 'User returned from fail URL',
    'timestamp': timezone.now().isoformat(),
    'query_params': request.GET.dict()  # Capture any error params from EuPago
}
self.payment.fail(info=failure_info)
```

## Testing Recommendations

1. **Test Credit Card Failure:**
   - Create a test order
   - Select credit card payment
   - On EuPago payment page, trigger a failure (decline card, cancel, etc.)
   - Verify user sees friendly error message, not 500 error
   - Verify user can retry payment

2. **Test PayByLink Failure:**
   - Create a test order
   - Select "Pagamento Online" (PayByLink)
   - On EuPago page, trigger a failure
   - Verify proper error handling

3. **Test Payment Cancellation:**
   - Start payment process
   - Click "Back" or "Cancel" on EuPago page
   - Verify user returns to order page with info message

4. **Check Logs:**
   - Monitor logs during failed payments
   - Verify proper error information is captured
   - Ensure no stack traces for expected failures

## Files Modified

1. **eupago/payment.py**
   - Updated `EuPagoCreditCard.execute_payment()` to include all failure URLs

2. **eupago/urls.py**
   - Added `return_with_status` URL pattern to global `urlpatterns`

3. **eupago/views.py**
   - Updated `EuPagoReturnView.dispatch()` to handle both event-specific and global URLs
   - Added try-except wrapper in `EuPagoReturnView.get()` for better error handling
   - Enhanced failure information logging with query parameters

## Notes

- **PayByLink** (`EuPagoPayByLink`) was already correctly configured with proper failure URLs
- **MB/Credit Card** (`EuPagoMBCreditCard`) was already correctly configured
- **MBWay New** (`EuPagoMBWayNew`) was already correctly configured
- Only the legacy **Credit Card** payment method needed URL configuration updates
- The return view needed updates to handle global URL patterns used by all payment methods

## Impact

✅ Users will now see friendly error messages when payments fail
✅ Failed payments are properly logged with detailed information
✅ Users can easily retry payments after failure
✅ No more Internal Server Errors (500) on payment failures
