# AI Invoice Processing Agent

An enterprise-grade AI agent system for automated invoice processing with image-to-JSON conversion, file management, and real-time monitoring.

## 🚀 Features

- **Automated Invoice Processing**: Converts image-based invoices to structured JSON format using advanced AI
- **Real-time File Monitoring**: Automatically detects and processes new invoice files
- **Intelligent Data Extraction**: Extracts vendor details, amounts, dates, line items, and more
- **File Management**: Automatic file organization with timestamp-based naming and duplicate handling
- **Real-time Dashboard**: Streamlit-based monitoring interface with live statistics
- **Enterprise Logging**: Comprehensive logging with rotation, error tracking, and performance monitoring
- **RESTful API**: FastAPI-based backend with full API documentation and OpenAPI support
- **Scalable Architecture**: Modular design for easy extension and maintenance
- **Local AI Processing**: Uses Ollama for privacy-focused, on-premises AI model deployment

## 🛠️ Tech Stack

- **Backend**: FastAPI, Python 3.11+
- **AI/ML**: LangChain (0.3.22), LangGraph (0.4.7), Ollama
- **Frontend**: Streamlit (1.45.1)
- **File Processing**: Pillow, Watchdog
- **Data Handling**: Pandas, Pydantic
- **Testing**: Pytest, AsyncIO testing

## 📋 Prerequisites

- Python 3.11 or higher
- Ollama (for AI model deployment)
- 8GB+ RAM (16GB recommended for high-volume processing)
- 50GB+ available disk space

## ⚡ Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <repository-url>
cd ai-invoice-agent

# Install dependencies
pip install -r requirements.txt

# Create configuration file
cp .env.template .env
```

### 2. Setup Ollama

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Start Ollama service
ollama serve

# Download the AI model (in another terminal)
ollama pull llama3.2-vision
```

### 3. Start Services

```bash
# Start API server
./start_api.sh

# Start dashboard (in another terminal)
./start_dashboard.sh
```

### 4. Process Invoices

- **API**: http://localhost:8000
- **Dashboard**: http://localhost:8501
- **API Docs**: http://localhost:8000/docs

Place invoice images in the `incoming/` folder and monitor processing via the dashboard.

## 📁 Project Structure

```
ai-invoice-agent/
├── incoming/              # Input folder for invoice images
├── generated/             # Output folder for processed files
├── logs/                  # Application logs
├── src/                   # Source code
│   ├── api/              # FastAPI application
│   ├── services/         # Business logic services
│   ├── models/           # Data models
│   └── utils/            # Utility functions
├── dashboard/            # Streamlit monitoring dashboard
├── tests/               # Test files
├── config/              # Configuration files
├── requirements.txt     # Python dependencies
├── DEPLOYMENT_GUIDE.md  # Comprehensive deployment guide
└── USAGE_GUIDE.md       # Detailed usage instructions
```

## 🔧 Configuration

Key configuration options in `.env`:

```bash
# File Processing
INCOMING_FOLDER=./incoming
GENERATED_FOLDER=./generated
MAX_FILE_SIZE_MB=10
SUPPORTED_FORMATS=jpg,jpeg,png,pdf,tiff

# AI Model
OLLAMA_MODEL=llama3.2-vision
OLLAMA_BASE_URL=http://localhost:11434

# Processing
PROCESSING_INTERVAL_SECONDS=5
BATCH_SIZE=10
MAX_RETRY_ATTEMPTS=3

# Logging
LOG_LEVEL=INFO
LOG_MAX_SIZE_MB=100
```

## 📊 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/status` | GET | System status |
| `/stats` | GET | Processing statistics |
| `/process` | POST | Manual processing trigger |
| `/upload` | POST | File upload |
| `/results` | GET | Processing results |
| `/results/{id}` | DELETE | Delete result |

## 🖥️ Dashboard Features

- **Real-time Monitoring**: Live processing statistics and system health
- **File Upload**: Drag-and-drop interface for manual file uploads
- **Processing History**: Detailed view of all processed invoices
- **Error Analysis**: Comprehensive error tracking and analysis
- **Performance Metrics**: Processing time, success rates, and throughput
- **System Information**: Resource usage and configuration details

## 🧪 Testing

```bash
# Run unit tests
python -m pytest tests/ -v

# Run integration tests
python tests/integration_test.py

# Test specific components
python -m pytest tests/test_invoice_processor.py -v
```

## 🚀 Deployment

### Development
```bash
./start_api.sh
./start_dashboard.sh
```

### Production (Systemd)
```bash
# Install as system services
sudo cp systemd/*.service /etc/systemd/system/
sudo systemctl enable invoice-agent-api invoice-agent-dashboard
sudo systemctl start invoice-agent-api invoice-agent-dashboard
```

### Docker
```bash
# Build and run with Docker Compose
docker-compose up -d
```

See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for comprehensive deployment instructions.

## 📖 Documentation

- **[Deployment Guide](DEPLOYMENT_GUIDE.md)**: Complete deployment instructions for all environments
- **[Usage Guide](USAGE_GUIDE.md)**: Detailed usage instructions and examples
- **[API Documentation](http://localhost:8000/docs)**: Interactive API documentation (when running)

## 🔍 Monitoring

### Dashboard Metrics
- Processing throughput and success rates
- Real-time system health indicators
- Error analysis and troubleshooting
- File processing history and trends

### Log Files
- `logs/invoice_agent.log`: General application logs
- `logs/processing.log`: Invoice processing operations
- `logs/errors.log`: Error and exception tracking
- `logs/performance.log`: Performance metrics

## 🛡️ Security Features

- **File validation**: Format and size checking
- **Error handling**: Comprehensive exception management
- **Audit logging**: Complete operation tracking
- **Resource limits**: Memory and processing constraints
- **Local processing**: No external AI service dependencies

## 🔧 Troubleshooting

### Common Issues

**API won't start:**
```bash
# Check port availability
netstat -tlnp | grep 8000

# Verify configuration
python -c "from config.settings import settings; print('OK')"
```

**Ollama connection issues:**
```bash
# Check Ollama status
curl http://localhost:11434/api/tags

# Verify model installation
ollama list
```

**Processing failures:**
```bash
# Check logs
tail -f logs/processing.log

# Verify file permissions
ls -la incoming/ generated/
```

## 📈 Performance

### Optimization Tips
- Use SSD storage for better I/O performance
- Adjust `BATCH_SIZE` based on available memory
- Monitor system resources during processing
- Use appropriate `PROCESSING_INTERVAL_SECONDS` for your workload

### Benchmarks
- **Processing Speed**: 2-5 seconds per invoice (depending on complexity)
- **Throughput**: 100-500 invoices per hour (hardware dependent)
- **Accuracy**: 95%+ for standard invoice formats
- **Memory Usage**: 2-4GB during active processing

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## 📄 License

Enterprise License - Internal Use Only

## 🆘 Support

For support and questions:
1. Check the [Usage Guide](USAGE_GUIDE.md) and [Deployment Guide](DEPLOYMENT_GUIDE.md)
2. Review application logs for error messages
3. Test with simple invoice files to isolate issues
4. Check system resources and configuration

---

**Built with ❤️ using FastAPI, Streamlit, and LangChain**

