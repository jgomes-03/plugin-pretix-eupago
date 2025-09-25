#!/bin/bash

# Script to set up webhook secret for EuPago payments
# Usage: ./setup_webhook_secret.sh [SECRET]

set -e

# Get the directory of the script
SCRIPT_DIR=$(dirname "$0")
WEBHOOK_SECRET_FILE="$SCRIPT_DIR/eupago/webhook_secret.txt"

# If secret is provided as an argument, use it
if [ $# -eq 1 ]; then
    WEBHOOK_SECRET="$1"
else
    # Otherwise prompt for it
    echo -n "Enter your EuPago webhook secret: "
    read -s WEBHOOK_SECRET
    echo ""
fi

# Validate input
if [ -z "$WEBHOOK_SECRET" ]; then
    echo "Error: Webhook secret cannot be empty"
    exit 1
fi

# Create the file
echo -n "$WEBHOOK_SECRET" > "$WEBHOOK_SECRET_FILE"
chmod 600 "$WEBHOOK_SECRET_FILE" # Secure permissions

echo "✓ Webhook secret saved to $WEBHOOK_SECRET_FILE"
echo "✓ File permissions set to secure mode (600)"
echo ""
echo "You can also set the secret using an environment variable instead:"
echo "export EUPAGO_WEBHOOK_SECRET='$WEBHOOK_SECRET'"
echo ""
echo "Note: Make sure your web server user (www-data, nginx, etc.) can read this file"
echo "      or has the EUPAGO_WEBHOOK_SECRET environment variable set."
