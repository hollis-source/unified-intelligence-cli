# Deploy RAG Metrics to syd2 - Updated Instructions

## Project Location Unknown? No Problem!

Since `/root/unified-intelligence-cli` doesn't exist on syd2, here's how to deploy:

---

## Option 1: Find and Deploy Automatically (RECOMMENDED)

```bash
# 1. Transfer deployment package and finder script
scp rag-metrics-deployment.tar.gz root@syd2.jacobhollis.com:/tmp/
scp scripts/find_and_deploy_syd2.sh root@syd2.jacobhollis.com:/tmp/

# 2. SSH to syd2
ssh root@syd2.jacobhollis.com

# 3. Run the finder script (it will locate the project and deploy)
bash /tmp/find_and_deploy_syd2.sh
```

The script will:
- Search for `unified-intelligence-cli` directory
- Extract deployment files there
- Run the deployment automatically

---

## Option 2: Manual - Find Project First

```bash
# SSH to syd2
ssh root@syd2.jacobhollis.com

# Find the project directory
find / -name "unified-intelligence-cli" -type d 2>/dev/null

# Once you find it (e.g., /home/ubuntu/unified-intelligence-cli), use it:
cd /home/ubuntu/unified-intelligence-cli  # or wherever it is

# Extract deployment package
tar -xzf /tmp/rag-metrics-deployment.tar.gz

# Deploy
chmod +x scripts/deploy_syd2_root.sh
./scripts/deploy_syd2_root.sh
```

---

## Option 3: Create Project Directory

If the project doesn't exist on syd2 at all:

```bash
# SSH to syd2
ssh root@syd2.jacobhollis.com

# Create project directory
mkdir -p /opt/unified-intelligence-cli
cd /opt/unified-intelligence-cli

# Extract deployment package
tar -xzf /tmp/rag-metrics-deployment.tar.gz

# Create virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt  # if you have requirements.txt

# Or install minimal dependencies
pip install aiohttp surrealdb

# Deploy
chmod +x scripts/deploy_syd2_root.sh
./scripts/deploy_syd2_root.sh
```

---

## Option 4: Deploy to Custom Location

If you want to deploy to a specific location:

```bash
# Transfer package
scp rag-metrics-deployment.tar.gz root@syd2.jacobhollis.com:/tmp/

# SSH to syd2
ssh root@syd2.jacobhollis.com

# Create directory
mkdir -p /your/custom/path
cd /your/custom/path

# Extract
tar -xzf /tmp/rag-metrics-deployment.tar.gz

# Edit deployment script to use current directory
sed -i 's|/root/unified-intelligence-cli|'$(pwd)'|g' scripts/deploy_syd2_root.sh

# Deploy
chmod +x scripts/deploy_syd2_root.sh
./scripts/deploy_syd2_root.sh
```

---

## Quick Commands to Find Project

```bash
# Search common locations
ls -la /root/unified-intelligence-cli 2>/dev/null
ls -la /home/ubuntu/unified-intelligence-cli 2>/dev/null
ls -la /opt/unified-intelligence-cli 2>/dev/null
ls -la /var/www/unified-intelligence-cli 2>/dev/null

# Search entire filesystem
find / -name "unified-intelligence-cli" -type d 2>/dev/null

# Search for specific files
find / -name "rag_metrics_server.py" 2>/dev/null
```

---

## Minimal Standalone Deployment (No Existing Project)

If you just want to deploy the RAG metrics server without the full project:

```bash
# SSH to syd2
ssh root@syd2.jacobhollis.com

# Create minimal directory structure
mkdir -p /opt/rag-metrics/{scripts,src/adapters/web,src/routing}
cd /opt/rag-metrics

# Extract deployment package
tar -xzf /tmp/rag-metrics-deployment.tar.gz

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install aiohttp surrealdb

# Run server directly (without systemd)
export SURREALDB_URL="ws://localhost:8000"
export HOST="0.0.0.0"
export PORT="8080"
python scripts/rag_metrics_server.py
```

---

## After Finding the Project

Once you know where the project is, update these commands:

```bash
# Replace /path/to/project with actual path
cd /path/to/project
tar -xzf /tmp/rag-metrics-deployment.tar.gz
chmod +x scripts/deploy_syd2_root.sh
./scripts/deploy_syd2_root.sh
```

---

## Troubleshooting

### Can't Find Project
```bash
# Check if it's a git repo
find / -name ".git" -type d 2>/dev/null | grep unified-intelligence

# Check for Python files
find / -name "main.py" -o -name "composition.py" 2>/dev/null
```

### Project Doesn't Exist
- Use **Option 3** to create it
- Or use **Minimal Standalone Deployment**

### Permission Issues
```bash
# Run as root
sudo su -
# Then try again
```

---

## What to Tell Me

After you find the project location, tell me:
1. Where is it? (e.g., `/home/ubuntu/unified-intelligence-cli`)
2. Does it have a `venv` directory?
3. Is SurrealDB installed/running?

Then I can give you exact commands for your setup!

