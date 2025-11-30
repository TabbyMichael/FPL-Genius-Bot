#!/bin/bash
# Script to run the FPL bot

echo "Activating virtual environment..."
source venv/bin/activate

echo "Running FPL bot..."
python bot.py

echo "FPL bot execution completed."