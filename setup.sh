#!/bin/bash

echo "Setting up Python virtual environment for Docker Monitor..."

# Check if python3 is available
if ! command -v python3 &> /dev/null
then
    echo "Error: python3 is not installed. Please install Python 3.8+ and try again."
    exit 1
fi

# Create virtual environment in a folder named 'venv'
python3 -m venv venv

# Activate the environment and install dependencies
source venv/bin/activate
pip install -r requirements.txt

echo ""
echo "Setup complete!"
echo "To run the application in the future, first activate the environment with:"
echo "  source venv/bin/activate"
echo "Then, run the application with:"
echo "  python3 app_tkinter.py"