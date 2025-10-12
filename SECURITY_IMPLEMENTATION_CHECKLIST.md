# Security Implementation Checklist

**Project**: Unified Intelligence CLI - Production Security Hardening
**Target**: Production-ready deployment by Week 5
**Last Updated**: October 6, 2025

---

## Week 1: Critical Security Fixes (P0)

### Day 1-2: Secret Audit & Rotation
- [ ] Run trufflehog scan: `docker run trufflesecurity/trufflehog:latest filesystem . --json > audit.json`
- [ ] Run gitleaks scan: `docker run zricethezav/gitleaks:latest detect --source . --report-path report.json`
- [ ] Review scan results for exposed secrets
- [ ] If secrets found: Document all exposed keys
- [ ] Rotate Grok API key (https://console.x.ai)
- [ ] Rotate HuggingFace token (https://huggingface.co/settings/tokens)
- [ ] Rotate Tongyi API key
- [ ] Update all `.env` files with new keys (temporary)
- [ ] Add `.env*` to .gitignore if not already
- [ ] Test all providers with new keys

### Day 3-4: AWS Secrets Manager Integration
- [ ] Create AWS Secrets Manager secrets:
  ```bash
  aws secretsmanager create-secret \
      --name unified-intelligence/grok/api-key \
      --secret-string '{"api_key":"NEW_KEY"}'
  ```
- [ ] Create secrets for HuggingFace, Tongyi
- [ ] Implement `src/security/secrets_manager.py`
- [ ] Update all LLM adapters to use SecretsManager
- [ ] Test secret retrieval in dev environment
- [ ] Remove all `.env` files from repository
- [ ] Update deployment docs with Secrets Manager setup

### Day 5-7: Code Execution Sandboxing
- [ ] Install gVisor on deployment hosts
- [ ] Create `Dockerfile.project-builder-secure` with gVisor
- [ ] Implement `src/project_builder/execution/sandboxed_executor.py`
- [ ] Add resource limits (CPU, memory, disk, network)
- [ ] Test sandbox with malicious code examples
- [ ] Deploy network policies for egress filtering
- [ ] Create `k8s/project-builder-deployment-secure.yaml`
- [ ] Test in staging environment

**Week 1 Validation**:
- [ ] Zero secrets in git history or environment
- [ ] All API keys rotated and in Secrets Manager
- [ ] Code execution sandboxed (gVisor working)
- [ ] Resource limits enforced
- [ ] Network egress restricted

---

## Week 2: Authentication & Authorization (P0-P1)

### Day 8-9: OAuth2 + JWT Implementation
- [ ] Install dependencies: `fastapi-users`, `python-jose`, `passlib`
- [ ] Create `src/security/auth.py` with OAuth2 implementation
- [ ] Generate JWT secret key, store in Secrets Manager
- [ ] Implement user database schema (SQLite or PostgreSQL)
- [ ] Create `/token` login endpoint
- [ ] Create `/users` registration endpoint
- [ ] Implement `get_current_user()` dependency
- [ ] Test authentication flow

### Day 10-11: RBAC & Rate Limiting
- [ ] Define user roles: Admin, Developer, User
- [ ] Implement `require_role()` decorator
- [ ] Protect all Project Builder endpoints with auth
- [ ] Set up Redis for rate limiting
- [ ] Implement `src/security/rate_limiter.py`
- [ ] Add rate limit middleware to FastAPI
- [ ] Configure limits: Free (10/hr), Developer (100/hr), Enterprise (unlimited)
- [ ] Test rate limiting with load tests

### Day 12-14: Static Code Analysis
- [ ] Implement `src/project_builder/security/code_analyzer.py`
- [ ] Define forbidden imports (os.system, subprocess, eval, etc.)
- [ ] Define forbidden patterns (rm -rf, curl|sh, etc.)
- [ ] Add AST-based analysis
- [ ] Integrate analyzer into execution pipeline
- [ ] Test with malicious code samples
- [ ] Document blocked patterns

**Week 2 Validation**:
- [ ] Authentication required for all endpoints
- [ ] RBAC working (3 roles)
- [ ] Rate limiting active and tested
- [ ] Static code analysis blocking dangerous code
- [ ] All tests passing

---

## Week 3: Data Security & Dependencies (P1-P2)

### Day 15-17: Database Encryption
- [ ] Install SQLCipher: `pip install pysqlcipher3`
- [ ] Create database encryption key in Secrets Manager
- [ ] Implement `src/security/encrypted_db.py`
- [ ] Migrate existing SQLite database to SQLCipher
- [ ] Test encrypted database operations
- [ ] Implement encrypted backup functionality
- [ ] Test backup/restore procedures

### Day 18-19: Log Sanitization
- [ ] Implement `src/security/log_sanitizer.py`
- [ ] Define sensitive patterns (API keys, tokens, passwords)
- [ ] Configure sanitizing formatter
- [ ] Update logging config to use sanitizer
- [ ] Test with various log messages
- [ ] Verify no secrets in logs

### Day 20-21: Dependency Security
- [ ] Set up Snyk account and integration
- [ ] Configure GitHub Actions security scan workflow
- [ ] Run `safety check --file requirements.txt`
- [ ] Fix any high/critical CVEs found
- [ ] Pin all dependencies with exact versions
- [ ] Generate dependency hashes: `pip-compile --generate-hashes`
- [ ] Create SBOM: `cyclonedx-py -r -i requirements.txt -o sbom.json`
- [ ] Set up Dependabot alerts

**Week 3 Validation**:
- [ ] Database encrypted (SQLCipher)
- [ ] Logs sanitized (no sensitive data)
- [ ] All dependencies scanned
- [ ] Zero high/critical CVEs
- [ ] SBOM generated

---

## Week 4: Network Security & Hardening (P2)

### Day 22-24: TLS & Container Security
- [ ] Generate TLS certificates (Let's Encrypt)
- [ ] Configure HTTPS enforcement
- [ ] Add security headers (HSTS, CSP, X-Frame-Options)
- [ ] Update Docker containers to run as non-root
- [ ] Add seccomp profile to containers
- [ ] Drop all capabilities in securityContext
- [ ] Enable read-only root filesystem
- [ ] Test container security

### Day 25-26: Input Validation Framework
- [ ] Create Pydantic models for all inputs
- [ ] Add validation for project IDs (alphanumeric only)
- [ ] Add validation for project goals (length, content)
- [ ] Implement XSS prevention
- [ ] Add CSRF tokens (if using web UI)
- [ ] Test with malicious inputs

### Day 27-28: Security Testing
- [ ] Run OWASP ZAP scan
- [ ] Run Burp Suite security scan
- [ ] Test for common vulnerabilities (OWASP Top 10)
- [ ] Fix any issues found
- [ ] Document security test results

**Week 4 Validation**:
- [ ] TLS enforced (HTTPS only)
- [ ] Container security hardened
- [ ] Input validation comprehensive
- [ ] Security scan results: 0 high, <5 medium findings
- [ ] Ready for limited production deployment

---

## Week 5-6: Monitoring & Compliance (P3)

### Week 5: Security Monitoring
- [ ] Deploy Prometheus for metrics
- [ ] Configure Grafana security dashboard
- [ ] Set up centralized logging (ELK stack or equivalent)
- [ ] Configure security alerts (PagerDuty/Slack)
- [ ] Implement anomaly detection rules
- [ ] Test alerting with simulated incidents

### Week 6: Penetration Testing & Compliance
- [ ] Contract external penetration testing firm
- [ ] Conduct penetration test
- [ ] Fix findings from pentest
- [ ] Document compliance posture (SOC 2 controls)
- [ ] Test incident response plan
- [ ] Create disaster recovery runbook
- [ ] Final security review

**Week 6 Validation**:
- [ ] Penetration test passed
- [ ] Incident response plan tested
- [ ] Security monitoring operational
- [ ] Compliance documentation complete
- [ ] APPROVED FOR PRODUCTION

---

## Pre-Production Final Checklist

### Code Security
- [ ] ✅ Sandboxed execution (gVisor)
- [ ] ✅ Resource limits enforced
- [ ] ✅ Static code analysis
- [ ] ✅ Network egress filtering
- [ ] ✅ Environment scrubbing

### Secrets Management
- [ ] ✅ No secrets in code/git
- [ ] ✅ AWS Secrets Manager integrated
- [ ] ✅ All keys rotated
- [ ] ✅ 90-day rotation policy
- [ ] ✅ Audit trail enabled

### Authentication & Authorization
- [ ] ✅ OAuth2 + JWT
- [ ] ✅ RBAC (3 roles)
- [ ] ✅ Rate limiting
- [ ] ✅ Session management
- [ ] ✅ Password requirements

### Data Security
- [ ] ✅ Database encrypted
- [ ] ✅ Backups encrypted
- [ ] ✅ Logs sanitized
- [ ] ✅ Data retention policy
- [ ] ✅ PII handling compliant

### Network Security
- [ ] ✅ TLS 1.3 enforced
- [ ] ✅ Security headers
- [ ] ✅ Network policies
- [ ] ✅ Firewall rules
- [ ] ✅ DDoS protection (if applicable)

### Dependencies
- [ ] ✅ All deps scanned
- [ ] ✅ Versions pinned
- [ ] ✅ SBOM generated
- [ ] ✅ Auto-updates configured
- [ ] ✅ Zero critical CVEs

### Monitoring & Response
- [ ] ✅ Security monitoring
- [ ] ✅ Centralized logging
- [ ] ✅ Alerting configured
- [ ] ✅ Incident response plan
- [ ] ✅ Runbooks documented

### Compliance
- [ ] ✅ Security policy published
- [ ] ✅ Privacy policy published
- [ ] ✅ Terms of service updated
- [ ] ✅ GDPR compliance (if applicable)
- [ ] ✅ SOC 2 controls (if applicable)

### Testing
- [ ] ✅ Security scan passed
- [ ] ✅ Penetration test passed
- [ ] ✅ Load testing completed
- [ ] ✅ Disaster recovery tested
- [ ] ✅ Incident response drilled

---

## Sign-Off Requirements

**Security Team**: _________________ Date: _______
- [ ] All critical vulnerabilities fixed
- [ ] Security architecture approved
- [ ] Penetration test passed

**DevOps Team**: _________________ Date: _______
- [ ] Infrastructure hardened
- [ ] Monitoring operational
- [ ] Runbooks complete

**Compliance Team**: _________________ Date: _______
- [ ] Privacy requirements met
- [ ] Regulatory compliance verified
- [ ] Documentation complete

**Engineering Lead**: _________________ Date: _______
- [ ] Code security validated
- [ ] Tests passing
- [ ] Ready for production

**FINAL APPROVAL**: _________________ Date: _______

---

## Risk Acceptance

For any items not completed:

| Item | Risk Level | Justification | Accepted By | Date |
|------|------------|---------------|-------------|------|
|      |            |               |             |      |

---

**Version**: 1.0
**Status**: In Progress
**Target Completion**: Week 6
**Production Go-Live**: Week 5 (limited), Week 6 (full)
