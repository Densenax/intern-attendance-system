// In the processCode function's success handler
if (result.success) {
    if (result.needs_registration) {
        // Redirect to visitor registration with QR code
        handleQRRegistration(result.qr_code);
    } else {
        displayScanResult(result);
        updateRecentActivity(result);
        playSuccessSound();
    }
}

