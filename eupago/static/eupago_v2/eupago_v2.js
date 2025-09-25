/* EuPago v2 JavaScript functionality */

$(document).ready(function() {
    // Handle MBWay phone number formatting
    $('#id_payment_eupago_mbway_phone').on('input', function() {
        let phone = $(this).val().replace(/\D/g, '');
        
        // Format Portuguese phone numbers
        if (phone.length >= 9) {
            if (phone.startsWith('9')) {
                // Mobile number: 9XX XXX XXX
                phone = phone.replace(/(\d{3})(\d{3})(\d{3})/, '$1 $2 $3');
            } else if (phone.startsWith('2')) {
                // Landline: 2XX XXX XXX
                phone = phone.replace(/(\d{3})(\d{3})(\d{3})/, '$1 $2 $3');
            }
        }
        
        $(this).val(phone);
    });
    
    // Copy payment references to clipboard
    $('.payment-reference code').on('click', function() {
        const text = $(this).text();
        navigator.clipboard.writeText(text).then(function() {
            // Show tooltip or notification
            const $element = $(this);
            $element.attr('title', 'Copied!').tooltip('show');
            setTimeout(function() {
                $element.tooltip('hide').removeAttr('title');
            }, 1000);
        }).catch(function() {
            // Fallback for older browsers
            const textarea = document.createElement('textarea');
            textarea.value = text;
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand('copy');
            document.body.removeChild(textarea);
        });
    });
    
    // Auto-refresh payment status for pending payments
    if (window.location.pathname.includes('/order/') && 
        $('.payment-pending').length > 0) {
        
        // Check payment status every 30 seconds
        setInterval(function() {
            checkPaymentStatus();
        }, 30000);
    }
});

function checkPaymentStatus() {
    // This would typically make an AJAX call to check payment status
    // Implementation depends on Pretix's specific API structure
    console.log('Checking payment status...');
}

// Handle payment form submission
function submitPayment(providerId) {
    const $form = $('#payment-form');
    const $submitBtn = $form.find('button[type="submit"]');
    
    // Show loading state
    $submitBtn.prop('disabled', true);
    $submitBtn.html('<i class="fa fa-spinner fa-spin"></i> Processing...');
    
    // Submit form
    $form.submit();
}

// Format amounts for display
function formatAmount(amount, currency) {
    return new Intl.NumberFormat('pt-PT', {
        style: 'currency',
        currency: currency || 'EUR'
    }).format(amount);
}

// Validate phone numbers for MBWay
function validatePhone(phone) {
    // Portuguese mobile numbers: 9XXXXXXXX
    const mobilePattern = /^9[1236]\d{7}$/;
    // Remove spaces and non-digits
    const cleanPhone = phone.replace(/\D/g, '');
    
    return mobilePattern.test(cleanPhone);
}

// Show/hide payment method specific fields
$('input[name="payment"]').on('change', function() {
    const selectedProvider = $(this).val();
    
    // Hide all method-specific fields
    $('.payment-method-fields').hide();
    
    // Show fields for selected method
    $(`.payment-method-fields[data-provider="${selectedProvider}"]`).show();
});
