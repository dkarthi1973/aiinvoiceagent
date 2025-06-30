# AI Invoice Processing Agent - Usage Guide

## Quick Start

### Starting the System

1. **Navigate to the project directory:**
   ```bash
   cd ai-invoice-agent
   ```

2. **Start the API server:**
   ```bash
   ./start_api.sh
   ```
   The API will be available at: http://localhost:8000

3. **Start the dashboard (in a new terminal):**
   ```bash
   ./start_dashboard.sh
   ```
   The dashboard will be available at: http://localhost:8501

### Processing Your First Invoice

1. **Place an invoice image in the incoming folder:**
   ```bash
   cp your_invoice.jpg incoming/
   ```

2. **Monitor processing via the dashboard:**
   - Open http://localhost:8501 in your browser
   - Watch the real-time processing statistics
   - View processing results as they complete

3. **Check results:**
   - JSON files will appear in the `generated/` folder
   - Original images will be moved to `generated/` with timestamps
   - Processing logs are available in the `logs/` folder

## Dashboard Features

### Main Dashboard

The Streamlit dashboard provides comprehensive monitoring and control capabilities:

**System Health Section:**
- Real-time system status
- Service health indicators
- Uptime information
- Version details

**Processing Statistics:**
- Total files processed
- Success/failure counts
- Average processing time
- Current processing queue

**File Upload:**
- Direct file upload interface
- Drag-and-drop support
- Format validation
- Upload progress tracking

**Recent Results:**
- Processing history table
- Status indicators
- Error messages
- Download capabilities

### Real-time Monitoring

The dashboard automatically refreshes every 5 seconds (configurable) to provide real-time updates on:
- Processing progress
- System performance
- Error notifications
- Queue status

## API Usage

### Health Check

```bash
curl http://localhost:8000/
```

### Upload File

```bash
curl -X POST "http://localhost:8000/upload" \
     -H "accept: application/json" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@invoice.jpg;type=image/jpeg"
```

### Trigger Processing

```bash
curl -X POST "http://localhost:8000/process" \
     -H "accept: application/json" \
     -H "Content-Type: application/json" \
     -d '{"force_reprocess": false}'
```

### Get Statistics

```bash
curl http://localhost:8000/stats
```

### Get Processing Results

```bash
curl http://localhost:8000/results?limit=10
```

## File Management

### Supported Formats

- **JPEG/JPG**: Standard image format
- **PNG**: Portable Network Graphics
- **PDF**: Portable Document Format (first page processed)
- **TIFF**: Tagged Image File Format

### File Size Limits

- Default maximum: 10MB per file
- Configurable via `MAX_FILE_SIZE_MB` setting
- Larger files will be rejected with error message

### File Naming

**Input files:** Any valid filename with supported extension

**Output files:**
- JSON: `original_name_YYYYMMDD_HHMMSS.json`
- Moved images: `original_name_YYYYMMDD_HHMMSS.ext`

### Folder Structure

```
ai-invoice-agent/
├── incoming/          # Place new invoice files here
├── generated/         # Processed results appear here
│   ├── *.json        # Extracted invoice data
│   └── *.jpg/png     # Original images with timestamps
└── logs/             # Application logs
    ├── invoice_agent.log
    ├── processing.log
    └── errors.log
```

## Configuration

### Environment Variables

Key settings in `.env` file:

```bash
# Processing settings
PROCESSING_INTERVAL_SECONDS=5
BATCH_SIZE=10
MAX_FILE_SIZE_MB=10

# AI Model settings
OLLAMA_MODEL=llama3.2-vision
OLLAMA_BASE_URL=http://localhost:11434

# Logging
LOG_LEVEL=INFO
```

### Customizing Processing

**Adjust processing frequency:**
```bash
# Check for new files every 10 seconds
PROCESSING_INTERVAL_SECONDS=10
```

**Change batch size:**
```bash
# Process 5 files simultaneously
BATCH_SIZE=5
```

**Modify file size limit:**
```bash
# Allow files up to 20MB
MAX_FILE_SIZE_MB=20
```

## Troubleshooting

### Common Issues

**Files not processing:**
1. Check file format is supported
2. Verify file size is within limits
3. Ensure Ollama service is running
4. Check logs for error messages

**Dashboard not loading:**
1. Verify API server is running
2. Check port 8501 is not blocked
3. Clear browser cache
4. Check dashboard logs

**API errors:**
1. Verify all dependencies installed
2. Check configuration file syntax
3. Ensure required directories exist
4. Review error logs

### Log Analysis

**View real-time logs:**
```bash
tail -f logs/invoice_agent.log
```

**Search for errors:**
```bash
grep -i error logs/*.log
```

**Monitor processing:**
```bash
tail -f logs/processing.log
```

## Best Practices

### File Organization

1. **Use descriptive filenames** for easy identification
2. **Organize by date or vendor** in incoming folder
3. **Regular cleanup** of processed files
4. **Backup important results** before deletion

### Performance Optimization

1. **Process during off-peak hours** for large batches
2. **Monitor system resources** during heavy processing
3. **Adjust batch size** based on available memory
4. **Use SSD storage** for better I/O performance

### Security

1. **Restrict folder permissions** to authorized users only
2. **Regular security updates** for all components
3. **Monitor access logs** for unauthorized activity
4. **Encrypt sensitive invoice data** if required

### Maintenance

1. **Regular log rotation** to prevent disk space issues
2. **Monitor disk usage** in generated folder
3. **Update AI models** periodically for better accuracy
4. **Backup configuration** before making changes

## Integration Examples

### Automated Workflow

**Email integration example:**
```bash
#!/bin/bash
# Process email attachments
for attachment in /path/to/email/attachments/*.{jpg,png,pdf}; do
    if [ -f "$attachment" ]; then
        cp "$attachment" incoming/
        echo "Queued: $(basename "$attachment")"
    fi
done
```

**Scheduled processing:**
```bash
# Add to crontab for hourly processing
0 * * * * /path/to/ai-invoice-agent/trigger_processing.sh
```

### Custom Scripts

**Batch upload script:**
```python
import requests
import os

def upload_invoices(folder_path):
    api_url = "http://localhost:8000/upload"
    
    for filename in os.listdir(folder_path):
        if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.pdf')):
            file_path = os.path.join(folder_path, filename)
            
            with open(file_path, 'rb') as f:
                files = {'file': (filename, f, 'image/jpeg')}
                response = requests.post(api_url, files=files)
                
                if response.status_code == 200:
                    print(f"✅ Uploaded: {filename}")
                else:
                    print(f"❌ Failed: {filename}")

# Usage
upload_invoices("/path/to/invoice/folder")
```

**Results export script:**
```python
import requests
import json
import csv

def export_results_to_csv():
    api_url = "http://localhost:8000/results"
    response = requests.get(api_url)
    
    if response.status_code == 200:
        results = response.json()
        
        with open('invoice_results.csv', 'w', newline='') as csvfile:
            fieldnames = ['filename', 'status', 'vendor_name', 'total_amount', 'date']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for result in results:
                if result['invoice_data']:
                    writer.writerow({
                        'filename': result['original_filename'],
                        'status': result['status'],
                        'vendor_name': result['invoice_data'].get('vendor_name', ''),
                        'total_amount': result['invoice_data'].get('total_amount', ''),
                        'date': result['invoice_data'].get('date', '')
                    })

export_results_to_csv()
```

## Advanced Features

### Custom AI Models

To use different AI models:

1. **Install alternative model:**
   ```bash
   ollama pull llama3.1:8b
   ```

2. **Update configuration:**
   ```bash
   OLLAMA_MODEL=llama3.1:8b
   ```

3. **Restart services:**
   ```bash
   sudo systemctl restart invoice-agent-api
   ```

### Webhook Integration

Configure webhooks for processing notifications:

```python
# Add to configuration
WEBHOOK_URL=https://your-system.com/webhook
WEBHOOK_EVENTS=processing_complete,processing_failed
```

### Database Integration

For enterprise deployments, integrate with databases:

```python
# Example database configuration
DATABASE_URL=postgresql://user:pass@localhost/invoices
ENABLE_DATABASE_STORAGE=true
```

## Support and Maintenance

### Regular Maintenance Tasks

**Weekly:**
- Review processing statistics
- Check error logs
- Monitor disk usage
- Verify backup integrity

**Monthly:**
- Update dependencies
- Review security logs
- Performance optimization
- Clean old log files

**Quarterly:**
- Update AI models
- Security audit
- Capacity planning
- Documentation updates

### Getting Help

1. **Check logs first** for error messages
2. **Review configuration** for typos or invalid values
3. **Test with simple files** to isolate issues
4. **Monitor system resources** during processing
5. **Consult documentation** for configuration options

### Performance Monitoring

Monitor these key metrics:
- **Processing throughput** (files per hour)
- **Success rate** (percentage of successful processing)
- **Average processing time** per file
- **Error frequency** and types
- **System resource usage**

This usage guide provides comprehensive information for effectively operating the AI Invoice Processing Agent in various scenarios and environments.

