#!/bin/bash
"""
Startup script for AI Invoice Processing Agent
"""

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "requirements.txt" ]; then
    print_error "Please run this script from the ai-invoice-agent directory"
    exit 1
fi

print_status "Starting AI Invoice Processing Agent..."

# Check if .env file exists
if [ ! -f ".env" ]; then
    print_warning ".env file not found. Creating from template..."
    cp .env.template .env
    print_status "Please edit .env file with your configuration before continuing"
    print_status "Press Enter to continue after editing .env file..."
    read
fi

# Check Python version
python_version=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
required_version="3.11"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    print_warning "Python $required_version or higher is recommended. Current version: $python_version"
fi

# Install dependencies
print_status "Installing Python dependencies..."
pip3 install -r requirements.txt

# Create necessary directories
print_status "Creating necessary directories..."
mkdir -p incoming generated logs

# Check if Ollama is running (optional)
if command -v ollama &> /dev/null; then
    if ! pgrep -x "ollama" > /dev/null; then
        print_warning "Ollama is not running. Please start Ollama service for AI processing."
        print_status "You can start Ollama with: ollama serve"
    else
        print_success "Ollama is running"
    fi
else
    print_warning "Ollama not found. Please install Ollama for AI processing functionality."
    print_status "Visit: https://ollama.ai for installation instructions"
fi

# Start the API server
print_status "Starting FastAPI server..."
print_status "API will be available at: http://localhost:8000"
print_status "API documentation at: http://localhost:8000/docs"
print_status ""
print_status "To start the dashboard, run in another terminal:"
print_status "streamlit run dashboard/app.py --server.port 8501"
print_status ""
print_status "Press Ctrl+C to stop the server"
print_status ""

# Start the server
python3 -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

