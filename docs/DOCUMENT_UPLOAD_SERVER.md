# Document Upload Server for Auggie Integration

**Status**: In Development (Auggie implementing on SYD2)
**Location**: `syd2.jacobhollis.com:/opt/docserver/`
**Purpose**: Upload PDFs, images, and documents for auggie agent to read and analyze

## Executive Summary

A Clean Architecture-based document management server that enables auggie to access uploaded documents (PDFs, images, markdown) for analysis. Primary use case: Upload technical books like "Clean Architecture" (429 pages) for auggie to analyze and create project-specific guidelines.

## Architecture

### Clean Architecture Layers

```
┌─────────────────────────────────────────────────┐
│  Web Layer (FastAPI)                            │
│  - REST API endpoints                           │
│  - Authentication (API keys)                    │
│  - Static file serving (upload UI)              │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│  Use Cases (Business Logic)                     │
│  - UploadDocument                               │
│  - ExtractText (async)                          │
│  - ListDocuments                                │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│  Adapters (External Interfaces)                 │
│  ├─ Storage: Filesystem                         │
│  ├─ Database: SQLite (migrate to PostgreSQL)   │
│  └─ Extractors: PyPDF2 + pdfplumber            │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│  Domain (Entities)                              │
│  - Document (status, metadata)                  │
│  - DocumentType (PDF, IMAGE, TEXT, MARKDOWN)    │
│  - DocumentStatus (UPLOADED, EXTRACTING, READY) │
└─────────────────────────────────────────────────┘
```

### Directory Structure

```
/opt/docserver/
├── src/
│   ├── domain/              # Entities (Document)
│   ├── use_cases/           # Business logic
│   ├── adapters/            # External interfaces
│   │   ├── web/             # FastAPI routes
│   │   ├── storage/         # File storage
│   │   ├── database/        # SQLite/PostgreSQL
│   │   └── extractors/      # PDF text extraction
│   ├── config.py            # Configuration
│   └── main.py              # Entry point
├── static/                  # Upload UI
├── uploads/                 # Document storage
├── tests/                   # Unit + integration tests
├── requirements.txt
└── README.md
```

## API Endpoints

### Upload Document
```http
POST /upload
Content-Type: multipart/form-data
X-API-Key: auggie-secret-key

file: [binary data]
uploaded_by: auggie

Response:
{
  "success": true,
  "document_id": 1,
  "filename": "clean_architecture_a1b2c3.pdf",
  "status": "uploaded"
}
```

### List Documents
```http
GET /documents?page=1&limit=50
X-API-Key: auggie-secret-key

Response:
{
  "documents": [
    {
      "id": 1,
      "filename": "clean_architecture_a1b2c3.pdf",
      "original_filename": "Clean_Architecture_Martin.pdf",
      "document_type": "pdf",
      "file_size": 5242880,
      "status": "ready",
      "uploaded_at": "2025-10-12T00:00:00Z",
      "uploaded_by": "auggie",
      "page_count": 429,
      "has_extracted_text": true
    }
  ],
  "total": 1,
  "page": 1,
  "pages": 1
}
```

### Get Document Details
```http
GET /documents/1
X-API-Key: auggie-secret-key

Response:
{
  "id": 1,
  "filename": "clean_architecture_a1b2c3.pdf",
  "original_filename": "Clean_Architecture_Martin.pdf",
  "document_type": "pdf",
  "file_size": 5242880,
  "status": "ready",
  "uploaded_at": "2025-10-12T00:00:00Z",
  "uploaded_by": "auggie",
  "page_count": 429,
  "has_extracted_text": true
}
```

### Get Extracted Text
```http
GET /documents/1/text
X-API-Key: auggie-secret-key

Response:
{
  "document_id": 1,
  "text": "Clean Architecture: A Craftsman's Guide to Software Structure and Design\n\nBy Robert C. Martin\n\nChapter 1: What is Design?...",
  "page_count": 429,
  "extracted_at": "2025-10-12T00:05:00Z"
}
```

### Download Original File
```http
GET /documents/1/download
X-API-Key: auggie-secret-key

Response:
[binary PDF data]
Content-Disposition: attachment; filename="Clean_Architecture_Martin.pdf"
```

### Health Check
```http
GET /health

Response:
{
  "status": "healthy",
  "database": "connected",
  "uploads_dir": "/opt/docserver/uploads/",
  "total_documents": 42
}
```

## Security

### File Upload Validation
- **File types**: PDF, PNG, JPG, GIF, WebP, MD, TXT
- **Size limit**: 50MB (configurable)
- **Filename sanitization**: Remove special characters, add unique ID
- **Path traversal prevention**: Validate all file paths

### Authentication
- **API Key**: Required in `X-API-Key` header
- **Key storage**: Environment variable `API_KEY`
- **Rate limiting**: 100 requests/minute per key (future)

### Database
- **SQLite**: Development (single-file, easy backup)
- **PostgreSQL**: Production (migrate when scaling)
- **Prepared statements**: Prevent SQL injection

## Auggie Integration

### Example 1: Analyze Clean Architecture Book

```bash
# 1. Upload book
BOOK_ID=$(curl -s -X POST http://syd2.jacobhollis.com:8080/upload \
  -H "X-API-Key: auggie-secret-key" \
  -F "file=@Clean_Architecture_Martin.pdf" \
  -F "uploaded_by=auggie" | jq -r '.document_id')

# 2. Wait for extraction (async)
while [ "$(curl -s -H "X-API-Key: auggie-secret-key" \
  http://syd2.jacobhollis.com:8080/documents/$BOOK_ID | jq -r '.status')" != "ready" ]; do
  echo "Extracting text..."
  sleep 5
done

# 3. Get extracted text
curl -H "X-API-Key: auggie-secret-key" \
  http://syd2.jacobhollis.com:8080/documents/$BOOK_ID/text -o clean_arch.txt

# 4. Analyze with auggie
auggie --model gpt5 --instruction "Read clean_arch.txt and create revised Clean Architecture guidelines for our unified-intelligence-cli project. Focus on:
1. Dependency Inversion Principle violations
2. Use case layer improvements
3. Adapter pattern refinements
Output: docs/CLEAN_ARCH_GUIDELINES_REVISED.md"
```

### Example 2: Analyze Screenshots

```bash
# Upload debug screenshot
curl -X POST http://syd2.jacobhollis.com:8080/upload \
  -H "X-API-Key: auggie-secret-key" \
  -F "file=@error_screenshot.png" \
  -F "uploaded_by=auggie"

# Auggie can read the image directly
auggie --model sonnet4.5 --instruction "Read document ID 5 (error_screenshot.png) and diagnose the issue. Provide fix steps."
```

### Example 3: Bulk Document Analysis

```bash
# Upload multiple PDFs
for pdf in books/*.pdf; do
  curl -X POST http://syd2.jacobhollis.com:8080/upload \
    -H "X-API-Key: auggie-secret-key" \
    -F "file=@$pdf" \
    -F "uploaded_by=auggie"
done

# Auggie batch analysis
auggie --model gpt5 --instruction "Analyze all documents from today. Create comparative analysis of software architecture principles across all books. Output: docs/ARCHITECTURE_COMPARISON.md"
```

## Performance

### Benchmarks (Target)

| Operation | Target | Notes |
|-----------|--------|-------|
| Upload 50MB PDF | <5s | Network + validation + save |
| Extract 429-page PDF | <30s | Async processing |
| API response (list) | <100ms | Cached database queries |
| API response (text) | <500ms | Retrieve from database |

### Optimization Strategies

1. **Async extraction**: Background tasks don't block API
2. **Caching**: Redis for frequently accessed text
3. **Pagination**: Limit 50 documents per request
4. **Compression**: Gzip response bodies
5. **Database indexing**: filename, uploaded_by, status

## Deployment

### Development (Local)

```bash
cd /opt/docserver/
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set environment
export API_KEY="dev-test-key"
export UPLOAD_DIR="/opt/docserver/uploads/"
export DB_PATH="/opt/docserver/docserver.db"

# Run server
python3 src/main.py
# Server: http://localhost:8080
```

### Production (SYD2)

```bash
# 1. Create systemd service
cat > /etc/systemd/system/docserver.service << 'EOF'
[Unit]
Description=Document Upload Server for Auggie
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/docserver
Environment="API_KEY=<production-key>"
Environment="UPLOAD_DIR=/opt/docserver/uploads/"
Environment="DB_PATH=/opt/docserver/docserver.db"
ExecStart=/opt/docserver/venv/bin/python3 /opt/docserver/src/main.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 2. Enable and start
systemctl daemon-reload
systemctl enable docserver
systemctl start docserver
systemctl status docserver

# 3. Check logs
journalctl -u docserver -f
```

### Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name docs.syd2.jacobhollis.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        # Allow large file uploads
        client_max_body_size 50M;
        client_body_timeout 300s;
    }
}
```

## Monitoring

### Health Checks

```bash
# Check server status
curl http://syd2.jacobhollis.com:8080/health

# Check document count
curl -H "X-API-Key: auggie-secret-key" \
  http://syd2.jacobhollis.com:8080/documents | jq '.total'

# Check extraction backlog
curl -H "X-API-Key: auggie-secret-key" \
  "http://syd2.jacobhollis.com:8080/documents?status=extracting" | jq '.total'
```

### Metrics (Future)

- Upload rate (documents/hour)
- Extraction duration (p50, p95, p99)
- API latency (p50, p95, p99)
- Error rate (5xx responses)
- Storage usage (disk space)

## Testing

### Unit Tests

```bash
cd /opt/docserver/
pytest tests/test_upload.py -v
pytest tests/test_extraction.py -v
pytest tests/test_api.py -v
```

### Integration Tests

```bash
# Upload test PDF
curl -X POST http://localhost:8080/upload \
  -H "X-API-Key: dev-test-key" \
  -F "file=@tests/fixtures/sample.pdf" \
  -F "uploaded_by=test"

# Verify extraction
sleep 10
curl -H "X-API-Key: dev-test-key" \
  http://localhost:8080/documents/1/text | jq '.text' | head -20
```

## Roadmap

### Phase 1: MVP (Current - Auggie implementing)
- ✓ Clean Architecture structure
- ✓ File upload API
- ⏳ PDF text extraction
- ⏳ Simple web UI
- ⏳ SQLite database

### Phase 2: Production Hardening
- PostgreSQL migration
- Redis caching
- Rate limiting
- Metrics (Prometheus)
- Automated backups

### Phase 3: Advanced Features
- OCR for scanned PDFs
- Image text extraction (Tesseract)
- Document similarity search
- Version control for documents
- Collaborative annotations

### Phase 4: Auggie Deep Integration
- Auggie can upload documents directly via API
- Auggie can query documents by content
- Auggie can create document summaries
- Auggie can link documents to tasks

## Troubleshooting

### Issue: PDF extraction fails

```bash
# Check PDF is valid
pdfinfo /opt/docserver/uploads/document_xyz.pdf

# Manual extraction test
python3 -c "
from src.adapters.extractors.pdf_extractor import extract_text
text, pages = extract_text('/opt/docserver/uploads/document_xyz.pdf')
print(f'Pages: {pages}, Text length: {len(text)}')
"
```

### Issue: Server won't start

```bash
# Check port availability
netstat -tuln | grep 8080

# Check permissions
ls -la /opt/docserver/uploads/
chown -R www-data:www-data /opt/docserver/uploads/

# Check Python dependencies
pip list | grep fastapi
```

### Issue: Database locked

```bash
# Check SQLite processes
lsof /opt/docserver/docserver.db

# Reset database (DESTRUCTIVE)
rm /opt/docserver/docserver.db
python3 src/main.py  # Re-creates schema
```

## Contributing

### Code Standards
- Follow PEP 8 style guide
- Type hints for all functions
- Docstrings (Google style)
- 90%+ test coverage
- Clean Architecture principles

### Pull Request Checklist
- [ ] Tests pass (`pytest`)
- [ ] Code formatted (`black src/`)
- [ ] Type checks pass (`mypy src/`)
- [ ] Documentation updated
- [ ] Clean Architecture layers respected

---

**Status**: Auggie implementing on SYD2 (PID 3207229)
**Next**: Wait for auggie completion, review implementation, deploy server
**ETA**: ~15-20 minutes for full implementation
