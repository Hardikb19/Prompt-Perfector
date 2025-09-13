#!/bin/bash
# Setup script for Prompt Perfector on MacOS
set -e

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install requirements
pip install -r requirements.txt

# Initialize database
python3 -m promptperfector.logic

echo "Setup complete. To run: source venv/bin/activate && python3 -m promptperfector.main"
