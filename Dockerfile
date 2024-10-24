FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh | bash

# Install cliclick using Homebrew (if available on macOS alternative)
RUN bash -c "$(brew install cliclick)"

# Copy project files into the container
WORKDIR /app
COPY . /app

# Create a virtual environment and install dependencies
RUN python3 -m venv /app/venv && \
    /app/venv/bin/pip install --upgrade pip && \
    /app/venv/bin/pip install -r requirements.txt

# Set entry point to run Streamlit
ENTRYPOINT ["/app/venv/bin/streamlit", "run", "app.py"]