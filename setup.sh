#!/bin/bash

# Install Homebrew (if not installed)
if ! command -v brew &>/dev/null; then
  echo "Homebrew not found. Installing Homebrew..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
else
  echo "Homebrew is already installed."
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

echo "All dependencies installed."

# Ensure pip is up-to-date
python3 -m ensurepip --upgrade
python3 -m pip install --upgrade pip

# Create a virtual environment
echo "Creating a virtual environment..."
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies from requirements.txt..."
pip install -r requirements.txt

echo "Setup completed successfully!"

# Provide a message to start the Streamlit app
echo "You can now run the Streamlit app using:"
echo "source venv/bin/activate && streamlit run app.py"