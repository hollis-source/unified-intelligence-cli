#!/bin/bash
# Simple RAG Server Starter
# Avoids event loop issues by running in subprocess

cd /home/ui-cli_jake/unified-intelligence-cli
source venv/bin/activate

# Kill any existing server
pkill -f start_rag_server 2>/dev/null

# Start server in background
python start_rag_server.py > /tmp/rag_server.log 2>&1 &
PID=$!

echo "RAG server starting with PID: $PID"
echo "Waiting for server to be ready..."

# Wait for server to be ready
for i in {1..10}; do
    sleep 1
    if curl -s http://localhost:8888/health > /dev/null 2>&1; then
        echo "✅ RAG server is ready!"
        echo "   Health: http://localhost:8888/health"
        echo "   Metrics: http://localhost:8888/api/rag/metrics"
        echo "   Logs: tail -f /tmp/rag_server.log"
        exit 0
    fi
    echo "   Waiting... ($i/10)"
done

echo "❌ Server failed to start. Check logs:"
echo "   tail -f /tmp/rag_server.log"
exit 1

