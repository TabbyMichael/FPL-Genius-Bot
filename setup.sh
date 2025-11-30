#!/bin/bash
# Setup script for FPL Bot

echo "Setting up FPL Bot..."

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Initialize database
echo "Initializing database..."
python init_db.py

# Create .env file from example
echo "Creating .env file..."
cp .env.example .env

echo "Setup completed!"
echo "Next steps:"
echo "1. Edit the .env file to add your FPL credentials"
echo "2. Run the bot with: ./run_bot.sh"