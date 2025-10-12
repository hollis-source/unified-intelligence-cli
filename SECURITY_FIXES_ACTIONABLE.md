# Security Fixes - Actionable Implementation Guide

**Based on**: SECURITY_REVIEW_TLS_DOCKER_SECRETS.md  
**Status**: Ready to implement  
**Estimated Time**: 2-4 hours

---

## Priority 1 (P1) - CRITICAL - Must Fix Before Production

### 1. Replace Development Certificates with Production Certificates

**Current Issue**:
```yaml
# docker-compose.production.yml:113
volumes:
  - ./certs/dev:/etc/traefik/certs:ro  # ⚠️ Development certs
```

**Option A: Let's Encrypt (Recommended for Public Domains)**

```yaml
# docker-compose.production.yml - Add to traefik service
traefik:
  command:
    # ... existing commands ...
    
    # Let's Encrypt ACME configuration
    - --certificatesresolvers.letsencrypt.acme.email=admin@yourdomain.com
    - --certificatesresolvers.letsencrypt.acme.storage=/acme.json
    - --certificatesresolvers.letsencrypt.acme.httpchallenge.entrypoint=web
    
  volumes:
    # ... existing volumes ...
    - ./traefik/acme.json:/acme.json  # Let's Encrypt cert storage
    
  labels:
    # Update service labels to use Let's Encrypt
    - "traefik.http.routers.surrealdb-http.tls.certresolver=letsencrypt"
    - "traefik.http.routers.grafana.tls.certresolver=letsencrypt"
```

**Setup**:
```bash
# Create acme.json with proper permissions
mkdir -p traefik
touch traefik/acme.json
chmod 600 traefik/acme.json

# Update .gitignore
echo "traefik/acme.json" >> .gitignore
```

**Option B: CA-Signed Certificates (For Internal/Private Domains)**

```yaml
# docker-compose.production.yml
traefik:
  volumes:
    - ./certs/production:/etc/traefik/certs:ro  # Production certs
```

**Setup**:
```bash
# Create production certs directory
mkdir -p certs/production

# Copy your CA-signed certificates
cp /path/to/fullchain.pem certs/production/
cp /path/to/privkey.pem certs/production/

# Set proper permissions
chmod 644 certs/production/fullchain.pem
chmod 600 certs/production/privkey.pem

# Update .gitignore
echo "certs/production/" >> .gitignore
```

---

### 2. Secure Traefik Dashboard

**Current Issue**:
```yaml
# docker-compose.production.yml:137
labels:
  - "traefik.http.routers.traefik.rule=Host(`traefik.dev.local`)"
  # ⚠️ No authentication
```

**Option A: Add BasicAuth (Recommended)**

```bash
# Generate password hash
htpasswd -nb admin your_secure_password
# Output: admin:$apr1$xyz...

# Or use Docker
docker run --rm httpd:alpine htpasswd -nb admin your_secure_password
```

```yaml
# docker-compose.production.yml - Update traefik labels
traefik:
  labels:
    - "traefik.enable=true"
    
    # Create BasicAuth middleware
    - "traefik.http.middlewares.dashboard-auth.basicauth.users=admin:$$apr1$$xyz..."
    
    # Apply middleware to dashboard router
    - "traefik.http.routers.traefik.rule=Host(`traefik.yourdomain.com`)"
    - "traefik.http.routers.traefik.entrypoints=websecure"
    - "traefik.http.routers.traefik.tls=true"
    - "traefik.http.routers.traefik.tls.certresolver=letsencrypt"
    - "traefik.http.routers.traefik.service=api@internal"
    - "traefik.http.routers.traefik.middlewares=dashboard-auth"  # ✅ Add auth
```

**Option B: Disable Dashboard (Most Secure)**

```yaml
# docker-compose.production.yml
traefik:
  command:
    - --api.dashboard=false  # ✅ Disable completely
    # Remove all dashboard-related labels
```

---

## Priority 2 (P2) - HIGH - Fix Within Week 1

### 3. Enforce TLS 1.3 and Secure Cipher Suites

**Create**: `config/traefik/tls-production.yml`

```yaml
# Traefik Dynamic Configuration - Production TLS
# Enforces TLS 1.3 with secure cipher suites

tls:
  options:
    default:
      minVersion: VersionTLS13
      cipherSuites:
        - TLS_AES_256_GCM_SHA384
        - TLS_CHACHA20_POLY1305_SHA256
        - TLS_AES_128_GCM_SHA256
      curvePreferences:
        - CurveP521
        - CurveP384
      sniStrict: true
      
  certificates:
    - certFile: /etc/traefik/certs/fullchain.pem
      keyFile: /etc/traefik/certs/privkey.pem
      
  stores:
    default:
      defaultCertificate:
        certFile: /etc/traefik/certs/fullchain.pem
        keyFile: /etc/traefik/certs/privkey.pem
```

**Update**: `docker-compose.production.yml`

```yaml
traefik:
  volumes:
    - ./config/traefik:/etc/traefik/dynamic:ro  # ✅ Already configured
```

**Test**:
```bash
# Test TLS 1.3 enforcement
openssl s_client -connect localhost:443 -tls1_3  # Should work
openssl s_client -connect localhost:443 -tls1_2  # Should fail
```

---

### 4. Implement Log Sanitization

**Create**: `src/utils/log_sanitizer.py`

```python
"""
Log Sanitizer - Redacts sensitive data from logs.

Prevents accidental exposure of API keys, tokens, passwords in logs.
"""

import re
import logging


class SanitizingFormatter(logging.Formatter):
    """Logging formatter that redacts sensitive data."""

    SENSITIVE_PATTERNS = [
        # API keys and tokens
        (r'(api[_-]?key[\s:=]+)[^\s]+', r'\1[REDACTED]'),
        (r'(token[\s:=]+)[^\s]+', r'\1[REDACTED]'),
        (r'(password[\s:=]+)[^\s]+', r'\1[REDACTED]'),
        (r'(secret[\s:=]+)[^\s]+', r'\1[REDACTED]'),
        
        # Bearer tokens
        (r'Bearer\s+[A-Za-z0-9\-._~+/]+=*', r'Bearer [REDACTED]'),
        
        # Specific API key formats
        (r'xai-[A-Za-z0-9]+', r'xai-[REDACTED]'),
        (r'hf_[A-Za-z0-9]+', r'hf_[REDACTED]'),
        (r'sk-[A-Za-z0-9]+', r'sk-[REDACTED]'),
        (r'ghp_[A-Za-z0-9]+', r'ghp_[REDACTED]'),
        
        # Connection strings
        (r'(redis://[^:]+:)[^@]+(@)', r'\1[REDACTED]\2'),
        (r'(postgresql://[^:]+:)[^@]+(@)', r'\1[REDACTED]\2'),
    ]

    def format(self, record):
        """Format log record with sensitive data redacted."""
        original = super().format(record)
        sanitized = original

        for pattern, replacement in self.SENSITIVE_PATTERNS:
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)

        return sanitized


def configure_sanitized_logging(log_level: str = "INFO"):
    """
    Configure logging with sanitization.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    logging.config.dictConfig({
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'sanitized': {
                '()': 'src.utils.log_sanitizer.SanitizingFormatter',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            },
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'sanitized',
                'level': log_level,
            },
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': 'logs/app.log',
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5,
                'formatter': 'sanitized',
                'level': log_level,
            },
        },
        'root': {
            'level': log_level,
            'handlers': ['console', 'file'],
        },
    })
```

**Update**: Application entry points

```python
# src/main.py (or wherever logging is configured)
from src.utils.log_sanitizer import configure_sanitized_logging

# Configure logging with sanitization
configure_sanitized_logging(log_level=os.getenv("LOG_LEVEL", "INFO"))
```

**Test**:
```python
# Test sanitization
import logging
from src.utils.log_sanitizer import configure_sanitized_logging

configure_sanitized_logging()
logger = logging.getLogger(__name__)

# These should be redacted
logger.info("API key: xai-abc123xyz")  # → "API key: xai-[REDACTED]"
logger.info("Token: hf_xyz789abc")     # → "Token: hf_[REDACTED]"
logger.info("Password: secret123")     # → "Password: [REDACTED]"
```

---

### 5. Fix Redis Healthcheck Password Exposure

**Current Issue**:
```yaml
# docker-compose.production.yml:308
healthcheck:
  test: ["CMD", "sh", "-c", "redis-cli -a $$(cat /run/secrets/redis_password) ping | grep PONG"]
  # ⚠️ Password visible in process list
```

**Fix**:
```yaml
# docker-compose.production.yml - Update redis healthcheck
redis:
  healthcheck:
    test: ["CMD", "sh", "-c", "REDISCLI_AUTH=$$(cat /run/secrets/redis_password) redis-cli ping | grep PONG"]
    interval: 5s
    timeout: 2s
    retries: 10
    start_period: 5s
```

**Why**: `REDISCLI_AUTH` environment variable is used by redis-cli internally, so password doesn't appear in command line.

---

## Priority 3 (P3) - MEDIUM - Fix Within Week 2

### 6. Add Rate Limiting

**Create**: `config/traefik/middlewares.yml`

```yaml
# Traefik Middlewares - Rate Limiting and Security Headers

http:
  middlewares:
    # Rate limiting for API endpoints
    rate-limit:
      rateLimit:
        average: 100  # 100 requests per second
        burst: 50     # Allow bursts up to 50
        period: 1s
        
    # Rate limiting for authentication endpoints
    auth-rate-limit:
      rateLimit:
        average: 10   # 10 requests per second
        burst: 5
        period: 1s
        
    # Security headers
    security-headers:
      headers:
        sslRedirect: true
        stsSeconds: 31536000
        stsIncludeSubdomains: true
        stsPreload: true
        forceSTSHeader: true
        frameDeny: true
        contentTypeNosniff: true
        browserXssFilter: true
        referrerPolicy: "strict-origin-when-cross-origin"
        customResponseHeaders:
          X-Robots-Tag: "noindex, nofollow"
          Server: ""  # Hide server version
```

**Update**: Service labels

```yaml
# docker-compose.production.yml - Add to service labels
surrealdb:
  labels:
    # ... existing labels ...
    - "traefik.http.routers.surrealdb-http.middlewares=rate-limit,security-headers"
    
grafana:
  labels:
    # ... existing labels ...
    - "traefik.http.routers.grafana.middlewares=rate-limit,security-headers"
```

---

### 7. Improve Error Messages in Secrets Utility

**Update**: `src/utils/secrets.py`

```python
def read_secret(secret_name: str) -> Optional[str]:
    """Read secret from Docker secret file or environment variable."""
    # Strategy 1: Check for *_FILE environment variable
    file_env_var = f"{secret_name}_FILE"
    file_path_str = os.getenv(file_env_var)
    
    if file_path_str:
        try:
            file_path = Path(file_path_str)
            if file_path.exists() and file_path.is_file():
                return file_path.read_text().strip()
        except (OSError, PermissionError) as e:
            # ✅ IMPROVED: Don't expose file path
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                "Failed to read secret file",
                extra={
                    "secret_name": secret_name,
                    "error_type": type(e).__name__
                }
            )
    
    # ... rest of function unchanged ...
```

---

### 8. Add Security Headers via Traefik

**Already covered in #6 above** - See `security-headers` middleware.

---

## Testing Checklist

After implementing fixes, verify:

- [ ] **TLS 1.3 Enforcement**
  ```bash
  openssl s_client -connect yourdomain.com:443 -tls1_3  # Should work
  openssl s_client -connect yourdomain.com:443 -tls1_2  # Should fail
  ```

- [ ] **Dashboard Authentication**
  ```bash
  curl https://traefik.yourdomain.com  # Should return 401 Unauthorized
  curl -u admin:password https://traefik.yourdomain.com  # Should work
  ```

- [ ] **Rate Limiting**
  ```bash
  # Send 200 requests rapidly
  for i in {1..200}; do curl https://yourdomain.com & done
  # Should see 429 Too Many Requests
  ```

- [ ] **Log Sanitization**
  ```bash
  # Check logs for exposed secrets
  docker-compose logs | grep -iE "xai-[a-z0-9]+|hf_[a-z0-9]+"
  # Should only see [REDACTED]
  ```

- [ ] **Redis Healthcheck**
  ```bash
  # Check process list inside container
  docker-compose exec redis ps aux | grep redis-cli
  # Should NOT see password in command line
  ```

- [ ] **Security Headers**
  ```bash
  curl -I https://yourdomain.com
  # Should see: Strict-Transport-Security, X-Frame-Options, etc.
  ```

---

## Deployment Steps

1. **Backup Current Configuration**
   ```bash
   cp docker-compose.production.yml docker-compose.production.yml.backup
   cp -r config/traefik config/traefik.backup
   ```

2. **Implement P1 Fixes** (Critical)
   - Replace certificates
   - Secure dashboard

3. **Test in Staging**
   ```bash
   docker-compose -f docker-compose.production.yml up -d
   # Run all tests above
   ```

4. **Implement P2 Fixes** (High Priority)
   - TLS 1.3 enforcement
   - Log sanitization
   - Redis healthcheck fix

5. **Implement P3 Fixes** (Medium Priority)
   - Rate limiting
   - Security headers
   - Error message improvements

6. **Final Security Scan**
   ```bash
   # Scan for secrets
   docker run --rm -v $(pwd):/path trufflesecurity/trufflehog:latest filesystem /path
   
   # Scan containers
   docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy image project-builder:latest
   ```

7. **Deploy to Production**
   ```bash
   docker-compose -f docker-compose.production.yml up -d
   ```

---

## Estimated Timeline

| Priority | Tasks | Time | Deadline |
|----------|-------|------|----------|
| P1 | Certificates + Dashboard | 2 hours | Before production |
| P2 | TLS 1.3 + Logging + Redis | 2 hours | Week 1 |
| P3 | Rate Limiting + Headers | 1 hour | Week 2 |
| **Total** | | **5 hours** | **2 weeks** |

---

## Success Criteria

✅ All P1 fixes implemented and tested  
✅ All P2 fixes implemented and tested  
✅ Security scan shows no critical vulnerabilities  
✅ All tests passing  
✅ Production deployment successful  

**Status**: Ready to implement  
**Next Step**: Start with P1 fixes (certificates + dashboard)

