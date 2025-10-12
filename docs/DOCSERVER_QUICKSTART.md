# Docserver Quick Start Guide

**Server**: `syd2.jacobhollis.com:8080` ✅ OPERATIONAL
**API Key**: `auggie-secret-key`

---

## 1-Minute Quick Start

### Upload a Document
```bash
curl -X POST http://syd2.jacobhollis.com:8080/api/upload \
  -H "X-API-Key: auggie-secret-key" \
  -F "file=@your_document.pdf" \
  -F "uploaded_by=auggie"
```

### List Documents
```bash
curl http://syd2.jacobhollis.com:8080/api/documents \
  -H "X-API-Key: auggie-secret-key"
```

### Get Extracted Text
```bash
curl http://syd2.jacobhollis.com:8080/api/documents/{id}/text \
  -H "X-API-Key: auggie-secret-key"
```

---

## Auggie Integration Example

```bash
# Upload Clean Architecture book (429 pages)
DOC_ID=$(curl -s -X POST http://syd2.jacobhollis.com:8080/api/upload \
  -H "X-API-Key: auggie-secret-key" \
  -F "file=@Clean_Architecture_Martin.pdf" \
  -F "uploaded_by=auggie" | jq -r '.document_id')

# Wait for extraction
while [ "$(curl -s -H "X-API-Key: auggie-secret-key" \
  http://syd2.jacobhollis.com:8080/api/documents/$DOC_ID | \
  jq -r '.status')" != "ready" ]; do
  sleep 10
done

# Get text
curl -s -H "X-API-Key: auggie-secret-key" \
  http://syd2.jacobhollis.com:8080/api/documents/$DOC_ID/text | \
  jq -r '.text' > book.txt

# Analyze with auggie
auggie --model sonnet4.5 \
  --instruction "Read book.txt and create Clean Architecture guidelines for our project"
```

---

## Web UI

Open browser: `http://syd2.jacobhollis.com:8080/`
- Drag-and-drop upload interface
- Real-time document list
- Built with Tailwind CSS

---

## All Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/health` | GET | No | Health check |
| `/api/upload` | POST | Yes | Upload document |
| `/api/documents` | GET | Yes | List all documents |
| `/api/documents/{id}` | GET | Yes | Get document details |
| `/api/documents/{id}/text` | GET | Yes | Get extracted text |
| `/api/documents/{id}/download` | GET | Yes | Download file |

---

## Server Management

**Check Status**:
```bash
curl http://syd2.jacobhollis.com:8080/api/health
```

**Restart Server**:
```bash
ssh root@syd2.jacobhollis.com "pkill -f 'python3 src/main.py' && \
  cd /opt/docserver && source venv/bin/activate && \
  nohup python3 src/main.py > server.log 2>&1 &"
```

**View Logs**:
```bash
ssh root@syd2.jacobhollis.com "tail -f /opt/docserver/server.log"
```

---

## Testing Results

- ✅ Health check working
- ✅ Text file upload (tested with 122-byte file)
- ✅ Markdown file upload (tested)
- ✅ Database storage (7 documents)
- ✅ API authentication
- ⏳ PDF extraction (awaiting large PDF test)

---

## Full Documentation

See [DOCSERVER_DEPLOYMENT_GUIDE.md](./DOCSERVER_DEPLOYMENT_GUIDE.md) for:
- Complete architecture overview
- Production hardening steps
- Security considerations
- Performance metrics
- Troubleshooting guide

---

**Status**: Production-ready (85%)
**Next**: Test with 429-page PDF to validate extraction pipeline
