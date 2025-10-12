#!/bin/bash
# Setup Production Secrets and Certificates
# Purpose: Generate Docker secrets and TLS certificates for production deployment
# Usage: ./scripts/setup-production-secrets.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Directories
SECRETS_DIR="./secrets"
CERTS_DIR="./certs/dev"
CONFIG_DIR="./config/traefik"

echo -e "${GREEN}=== Project Builder Production Setup ===${NC}"
echo ""

# ============================================================================
# Step 1: Create directories
# ============================================================================
echo -e "${YELLOW}Step 1: Creating directories...${NC}"

mkdir -p "$SECRETS_DIR"
mkdir -p "$CERTS_DIR"
mkdir -p "$CONFIG_DIR"

echo -e "${GREEN}✓ Directories created${NC}"
echo ""

# ============================================================================
# Step 2: Generate secrets
# ============================================================================
echo -e "${YELLOW}Step 2: Generating secrets...${NC}"

# Function to generate random password
generate_password() {
    openssl rand -base64 32 | tr -d "=+/" | cut -c1-32
}

# Function to create secret file
create_secret() {
    local secret_name=$1
    local secret_value=$2
    local secret_file="$SECRETS_DIR/$secret_name"
    
    if [ -f "$secret_file" ]; then
        echo -e "${YELLOW}  ⚠ $secret_name already exists, skipping...${NC}"
    else
        echo -n "$secret_value" > "$secret_file"
        chmod 600 "$secret_file"
        echo -e "${GREEN}  ✓ Created $secret_name${NC}"
    fi
}

# Generate database credentials
echo "Generating database credentials..."
create_secret "surrealdb_root_user" "root"
create_secret "surrealdb_root_password" "$(generate_password)"

# Generate Redis password
echo "Generating Redis password..."
create_secret "redis_password" "$(generate_password)"

# Generate Grafana admin password
echo "Generating Grafana admin password..."
create_secret "grafana_admin_password" "$(generate_password)"

# API keys (placeholder - user must update these)
echo "Creating API key placeholders..."
create_secret "xai_api_key" "REPLACE_WITH_YOUR_XAI_API_KEY"
create_secret "huggingface_token" "REPLACE_WITH_YOUR_HUGGINGFACE_TOKEN"
create_secret "github_token" "REPLACE_WITH_YOUR_GITHUB_TOKEN"
create_secret "replicate_api_token" "REPLACE_WITH_YOUR_REPLICATE_API_TOKEN"

echo -e "${GREEN}✓ Secrets generated${NC}"
echo ""

# ============================================================================
# Step 3: Generate TLS certificates (development)
# ============================================================================
echo -e "${YELLOW}Step 3: Generating TLS certificates (development)...${NC}"

CERT_FILE="$CERTS_DIR/cert.pem"
KEY_FILE="$CERTS_DIR/key.pem"

if [ -f "$CERT_FILE" ] && [ -f "$KEY_FILE" ]; then
    echo -e "${YELLOW}  ⚠ TLS certificates already exist, skipping...${NC}"
else
    # Generate self-signed certificate for *.dev.local
    openssl req -x509 -newkey rsa:4096 -nodes \
        -keyout "$KEY_FILE" \
        -out "$CERT_FILE" \
        -days 365 \
        -subj "/C=US/ST=Development/L=Local/O=ProjectBuilder/CN=*.dev.local" \
        -addext "subjectAltName=DNS:*.dev.local,DNS:dev.local,DNS:db.dev.local,DNS:grafana.dev.local,DNS:traefik.dev.local"
    
    chmod 600 "$KEY_FILE"
    chmod 644 "$CERT_FILE"
    
    echo -e "${GREEN}  ✓ TLS certificates generated${NC}"
fi

echo -e "${GREEN}✓ TLS certificates ready${NC}"
echo ""

# ============================================================================
# Step 4: Set permissions
# ============================================================================
echo -e "${YELLOW}Step 4: Setting permissions...${NC}"

# Secrets directory: owner read-only
chmod 700 "$SECRETS_DIR"
chmod 600 "$SECRETS_DIR"/*

# Certificates: owner read-only for key, world-readable for cert
chmod 700 "$CERTS_DIR"
chmod 600 "$KEY_FILE"
chmod 644 "$CERT_FILE"

echo -e "${GREEN}✓ Permissions set${NC}"
echo ""

# ============================================================================
# Step 5: Display summary
# ============================================================================
echo -e "${GREEN}=== Setup Complete ===${NC}"
echo ""
echo -e "${YELLOW}Generated Secrets:${NC}"
echo "  - SurrealDB root password: $(cat $SECRETS_DIR/surrealdb_root_password)"
echo "  - Redis password: $(cat $SECRETS_DIR/redis_password)"
echo "  - Grafana admin password: $(cat $SECRETS_DIR/grafana_admin_password)"
echo ""
echo -e "${RED}⚠ IMPORTANT: Update API keys in $SECRETS_DIR/${NC}"
echo "  - xai_api_key"
echo "  - huggingface_token"
echo "  - github_token"
echo "  - replicate_api_token"
echo ""
echo -e "${YELLOW}TLS Certificates (Development):${NC}"
echo "  - Certificate: $CERT_FILE"
echo "  - Private Key: $KEY_FILE"
echo "  - Valid for: *.dev.local (365 days)"
echo ""
echo -e "${RED}⚠ For production: Replace with CA-signed certificates or use Let's Encrypt${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "  1. Update API keys in $SECRETS_DIR/"
echo "  2. Add *.dev.local to /etc/hosts:"
echo "     127.0.0.1 db.dev.local grafana.dev.local traefik.dev.local"
echo "  3. Start services:"
echo "     docker-compose -f docker-compose.production.yml up -d"
echo "  4. Access services:"
echo "     - SurrealDB: wss://db.dev.local"
echo "     - Grafana: https://grafana.dev.local"
echo "     - Traefik Dashboard: https://traefik.dev.local"
echo ""
echo -e "${GREEN}Setup complete! 🚀${NC}"

