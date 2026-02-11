#!/bin/bash

echo "Setting up University WiFi Quality Monitoring System..."
echo

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python3 is not installed. Please install Python 3.7 or higher."
    exit 1
fi

# Install Python packages
echo "Installing required Python packages..."
pip3 install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "Failed to install Python packages. Please check requirements.txt"
    exit 1
fi

echo
echo "Setup completed successfully!"
echo
echo "To start the system, run: python3 run_system.py"
echo