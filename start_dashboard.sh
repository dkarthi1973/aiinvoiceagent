#!/bin/bash
"""
Startup script for Streamlit Dashboard
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

print_status "Starting AI Invoice Processing Dashboard..."

# Check if API is running
api_url="http://localhost:8000"
if curl -s "$api_url" > /dev/null 2>&1; then
    print_success "API server is running at $api_url"
else
    print_warning "API server is not running at $api_url"
    print_status "Please start the API server first with: ./start_api.sh"
    print_status "Or run: python3 -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000"
    print_status ""
    print_status "Continuing with dashboard startup..."
fi

# Start the dashboard
print_status "Starting Streamlit dashboard..."
print_status "Dashboard will be available at: http://localhost:8501"
print_status ""
print_status "Press Ctrl+C to stop the dashboard"
print_status ""

# Start Streamlit
streamlit run dashboard/app.py --server.port 8501 --server.address 0.0.0.0

