#!/bin/bash
# Installation script for WWV/WWVH Discrimination Application

set -e  # Exit on error

echo "=========================================="
echo "WWV/WWVH Discrimination App - Installation"
echo "=========================================="
echo

# Check Python version
echo "Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "Found Python $PYTHON_VERSION"
echo

# Create virtual environment
echo "Creating virtual environment..."
if [ -d "venv" ]; then
    echo "Virtual environment already exists. Skipping..."
else
    python3 -m venv venv
    echo "Virtual environment created."
fi
echo

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo

# Upgrade pip, setuptools, and packaging
echo "Upgrading pip, setuptools, and packaging..."
pip install --upgrade pip setuptools packaging
echo

# Install ka9q-python
echo "Installing ka9q-python..."
if [ -d "ka9q-python" ]; then
    echo "ka9q-python directory already exists."
    echo "Reinstalling from existing directory..."
    cd ka9q-python
    pip install -e .
    cd ..
else
    echo "Cloning ka9q-python repository..."
    git clone https://github.com/mijahauan/ka9q-python.git
    cd ka9q-python
    pip install -e .
    cd ..
fi
echo

# Install application requirements
echo "Installing application requirements..."
pip install -r requirements.txt
echo

# Verify installation
echo "Verifying installation..."
python3 -c "from ka9q import RadiodControl; print('✓ ka9q successfully installed')" || echo "✗ ka9q installation failed"
python3 -c "import numpy; print('✓ numpy successfully installed')" || echo "✗ numpy installation failed"
python3 -c "import scipy; print('✓ scipy successfully installed')" || echo "✗ scipy installation failed"
python3 -c "import matplotlib; print('✓ matplotlib successfully installed')" || echo "✗ matplotlib installation failed"
echo

echo "=========================================="
echo "Installation complete!"
echo "=========================================="
echo
echo "To use the application:"
echo "  1. Activate the virtual environment:"
echo "     source venv/bin/activate"
echo
echo "  2. Run the application:"
echo "     python3 main.py --radiod bee1-hf-status.local"
echo
echo "  3. Or try the examples:"
echo "     python3 example_usage.py"
echo
echo "See QUICKSTART.md for more information."
echo
