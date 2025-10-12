#!/usr/bin/env bash
#
# Install Docker (one-time sudo requirement)
# After this runs, all deployment can proceed without sudo
#
# Run once: ./INSTALL_DOCKER.sh
# Then use: ./scripts/deploy_llamacpp_docker.sh
#

set -e

echo "========================================"
echo "Installing Docker & Dependencies"
echo "========================================"
echo ""
echo "This will install:"
echo "  - docker.io (Docker engine)"
echo "  - docker-compose (optional)"
echo "  - python3-pip (for HuggingFace CLI)"
echo ""
echo "After this, no more sudo needed!"
echo ""

# Install Docker and Python dependencies
sudo apt update
sudo apt install -y docker.io docker-compose python3-pip

# Allow current user to run Docker without sudo
echo ""
echo "Adding $USER to docker group..."
sudo usermod -aG docker "$USER"

echo ""
echo "✓ Docker installed!"
echo ""
echo "Verify installation:"
docker --version
docker compose version

echo ""
echo "⚠️  IMPORTANT: You must logout and login for group membership to take effect"
echo ""
echo "After logout/login, verify with:"
echo "  docker ps"
echo ""
echo "Then run: ./scripts/deploy_llamacpp_docker.sh"
echo ""