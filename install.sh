#!/bin/bash

# EuPago Installation Script for Pretix
# Usage: ./install.sh [environment]
# Environment: development | production (default: development)

set -e

ENVIRONMENT=${1:-development}
PRETIX_PATH=${PRETIX_PATH:-/opt/pretix}
PLUGIN_PATH=$(pwd)

echo "🚀 EuPago Plugin Installation"
echo "================================="
echo "Environment: $ENVIRONMENT"
echo "Pretix Path: $PRETIX_PATH"
echo "Plugin Path: $PLUGIN_PATH"
echo ""

# Check if Pretix installation exists
if [ ! -d "$PRETIX_PATH" ]; then
    echo "❌ Pretix installation not found at $PRETIX_PATH"
    echo "Please set PRETIX_PATH environment variable or ensure Pretix is installed."
    exit 1
fi

# Check if we're in the correct directory
if [ ! -f "setup.py" ] || [ ! -d "eupago" ]; then
    echo "❌ Please run this script from the EuPago plugin root directory."
    exit 1
fi

echo "📦 Installing Python dependencies..."
if [ "$ENVIRONMENT" = "production" ]; then
    pip install -r requirements.txt --no-dev
else
    pip install -r requirements.txt
fi

echo "🔧 Installing plugin..."
if [ "$ENVIRONMENT" = "development" ]; then
    pip install -e .
else
    pip install .
fi

echo "🌍 Compiling translations..."
cd eupago
find . -name "*.po" -exec msgfmt {} -o {}.mo \;
cd ..

echo "📁 Collecting static files..."
if [ -d "$PRETIX_PATH/src" ]; then
    cd $PRETIX_PATH/src
    python manage.py collectstatic --noinput
    cd $PLUGIN_PATH
fi

echo "🔄 Updating database..."
if [ -d "$PRETIX_PATH/src" ]; then
    cd $PRETIX_PATH/src
    python manage.py migrate --run-syncdb
    cd $PLUGIN_PATH
fi

echo ""
echo "✅ EuPago v2 plugin installed successfully!"
echo ""
echo "Next steps:"
echo "1. Add 'eupago' to your INSTALLED_APPS or enable in Pretix admin"
echo "2. Configure EuPago API credentials in Event Settings"
echo "3. Enable desired payment methods"
echo "4. Set up webhook URL in EuPago dashboard:"
echo "   https://yourdomain.com/_eupago/webhook/"
echo ""

if [ "$ENVIRONMENT" = "development" ]; then
    echo "Development mode:"
    echo "- Plugin installed in editable mode"
    echo "- Use 'pip install -e .' to update"
    echo "- Enable DEBUG logging for detailed information"
fi

echo ""
echo "📚 Documentation:"
echo "- README.md - Overview and features"
echo "- INTEGRATION_GUIDE.md - Detailed integration guide"
echo "- DEVELOPMENT.md - Development setup"
echo ""
echo "Happy payments! 💳"
