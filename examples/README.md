# Examples

Comprehensive examples for using Unified Intelligence CLI in various scenarios.

## Directory Structure

```
examples/
├── README.md                           # This file
├── deployment/                         # Production deployment examples
│   ├── docker-deployment.md            # Docker, K8s, Swarm deployments
│   ├── cicd-integration.md             # CI/CD pipeline integrations
│   └── systemd-service.md              # Linux systemd service setup
└── usage/                              # Usage examples
    ├── basic-tasks.sh                  # Simple task examples
    ├── advanced-orchestration.sh       # Complex multi-task workflows
    └── integration-examples.py         # Python integration examples
```

## Quick Links

### Deployment Examples

- **[Docker Deployment](deployment/docker-deployment.md)** - Docker, Kubernetes, and Swarm deployments
- **[CI/CD Integration](deployment/cicd-integration.md)** - GitHub Actions, GitLab CI, Jenkins, CircleCI, Azure DevOps
- **[Systemd Service](deployment/systemd-service.md)** - Run as a Linux system service

### Usage Examples

- **[Basic Tasks](usage/basic-tasks.sh)** - Simple single and multi-task examples
- **[Advanced Orchestration](usage/advanced-orchestration.sh)** - Complex workflows and patterns
- **[Python Integration](usage/integration-examples.py)** - Integrate UI-CLI into Python applications

## Getting Started

1. **Install UI-CLI:** See [INSTALL.md](../INSTALL.md)
2. **Configure API Key:** Get your xAI API key from https://x.ai/
3. **Try Basic Examples:** Start with `usage/basic-tasks.sh`
4. **Explore Deployments:** Choose your deployment method from `deployment/`

## Example Categories

### By Complexity

- **Beginner:** `usage/basic-tasks.sh`
- **Intermediate:** `usage/advanced-orchestration.sh`, `deployment/docker-deployment.md`
- **Advanced:** `deployment/cicd-integration.md`, `deployment/systemd-service.md`

### By Use Case

- **Development:** `usage/` directory
- **Production:** `deployment/docker-deployment.md`, `deployment/systemd-service.md`
- **CI/CD:** `deployment/cicd-integration.md`
- **Integration:** `usage/integration-examples.py`

## Running Examples

### Shell Scripts

```bash
# Make executable
chmod +x examples/usage/basic-tasks.sh

# Set API key
export XAI_API_KEY=your_key_here

# Run
./examples/usage/basic-tasks.sh
```

### Python Examples

```bash
# Install dependencies
pip install unified-intelligence-cli

# Run
python examples/usage/integration-examples.py
```

### Docker Examples

```bash
# Follow docker-deployment.md instructions
cd examples/deployment
cat docker-deployment.md
```

## Contributing

To add new examples:

1. Create example file in appropriate directory
2. Add clear comments and documentation
3. Test the example thoroughly
4. Update this README with link to new example
5. Submit PR with description

## Support

- **Documentation:** [Main README](../README.md)
- **Installation:** [INSTALL.md](../INSTALL.md)
- **Quickstart:** [QUICKSTART.md](../QUICKSTART.md)
- **Issues:** https://github.com/yourusername/unified-intelligence-cli/issues

---

**Last Updated:** 2025-09-30
**Version:** 1.0.0
