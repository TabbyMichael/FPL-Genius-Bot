#!/bin/bash

# Update script for FPL Bot enhanced features
echo "Updating FPL Bot requirements..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install new requirements
echo "Installing new requirements..."
pip install optuna shap cryptography

# Update requirements.txt
echo "Updating requirements.txt..."
cat >> requirements.txt << EOF
# Enhanced features dependencies
optuna>=3.0.0
shap>=0.42.0
cryptography>=3.4.0
EOF

echo "Requirements updated successfully!"
echo "To activate the virtual environment, run: source venv/bin/activate"