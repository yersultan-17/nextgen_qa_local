#!/bin/bash

# Install Homebrew (if not installed)
if ! command -v brew &>/dev/null; then
  echo "Homebrew not found. Installing Homebrew..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
else
  echo "Homebrew is already installed."
fi

# Install Python 3.12 if not installed
if ! command -v python3.12 &>/dev/null; then
  echo "Installing Python 3.12..."
  brew install python@3.12
else
  echo "Python 3.12 is already installed."
fi

# Install pipx if not installed
if ! command -v pipx &>/dev/null; then
  echo "Installing pipx..."
  brew install pipx
  pipx ensurepath
else
  echo "pipx is already installed."
fi

# Install streamlit globally using pipx
if ! command -v streamlit &>/dev/null; then
  echo "Installing streamlit globally..."
  pipx install streamlit
else
  echo "streamlit is already installed."
fi

# Install cliclick
if ! command -v cliclick &>/dev/null; then
  echo "Installing cliclick..."
  brew install cliclick
else
  echo "cliclick is already installed."
fi

# Ensure screencapture exists (comes pre-installed on macOS)
if ! command -v screencapture &>/dev/null; then
  echo "screencapture not found. Please make sure you are using macOS."
  exit 1
else
  echo "screencapture is available."
fi

echo "All system dependencies installed."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating new virtual environment..."
    python3.12 -m venv venv
else
    echo "Virtual environment already exists."
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Verify Python version
python_version=$(python --version)
echo "Using $python_version"

# Update pip within the virtual environment
echo "Updating pip in virtual environment..."
python -m pip install --upgrade pip

# Install Python dependencies
echo "Installing Python dependencies from requirements.txt..."
pip install -r requirements.txt

echo "Setup completed successfully!"

# Remind user to restart their shell if pipx was just installed
if [[ $PIPX_WAS_INSTALLED == 1 ]]; then
    echo ""
    echo "NOTE: Since pipx was just installed, you may need to restart your terminal"
    echo "or run 'source ~/.bashrc' (or ~/.zshrc) for the streamlit command to be available."
fi

echo ""
echo "To start the application:"
echo "1. Set your API key:"
echo "   export ANTHROPIC_API_KEY=your_api_key_here"
echo "2. Set display dimensions (recommended):"
echo "   export WIDTH=1280"
echo "   export HEIGHT=800"
echo "3. Run the Streamlit app:"
echo "   streamlit run app.py"