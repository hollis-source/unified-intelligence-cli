#!/bin/bash
# Deploy RAG tables to SurrealDB running in Docker

echo "================================================================================"
echo "DEPLOYING RAG TABLES TO SURREALDB"
echo "================================================================================"

# Read the schema file
SCHEMA_FILE="scripts/add_rag_tables.surql"

if [ ! -f "$SCHEMA_FILE" ]; then
    echo "❌ Schema file not found: $SCHEMA_FILE"
    exit 1
fi

echo "Reading schema from: $SCHEMA_FILE"
echo ""

# Copy schema file into container
echo "Copying schema file to container..."
docker cp "$SCHEMA_FILE" project-builder-db:/tmp/add_rag_tables.surql

if [ $? -ne 0 ]; then
    echo "❌ Failed to copy schema file to container"
    exit 1
fi

echo "✅ Schema file copied"
echo ""

# Execute SQL statements one by one
echo "Executing SQL statements..."
echo ""

# Extract non-comment, non-empty lines and execute
grep -v "^--" "$SCHEMA_FILE" | grep -v "^$" | while IFS= read -r line; do
    # Skip lines that are just comments
    if [[ "$line" =~ ^[[:space:]]*-- ]]; then
        continue
    fi
    
    # Accumulate lines until we hit a semicolon
    if [[ ! "$line" =~ \;$ ]]; then
        continue
    fi
    
    echo "Executing: ${line:0:60}..."
    
    # Execute the SQL statement
    docker exec project-builder-db /surreal sql \
        --endpoint http://localhost:8000 \
        --username root \
        --password root \
        --namespace atado \
        --database rag \
        --command "$line" 2>&1 | grep -v "^$"
    
    if [ $? -eq 0 ]; then
        echo "  ✅ Success"
    else
        echo "  ⚠️  Warning (might already exist)"
    fi
    echo ""
done

echo "================================================================================"
echo "VERIFYING TABLES"
echo "================================================================================"

# Verify agent_performance table
echo "Checking agent_performance table..."
docker exec project-builder-db /surreal sql \
    --endpoint http://localhost:8000 \
    --username root \
    --password root \
    --namespace atado \
    --database rag \
    --command "INFO FOR TABLE agent_performance;" 2>&1 | head -5

echo ""

# Verify routing_decisions table
echo "Checking routing_decisions table..."
docker exec project-builder-db /surreal sql \
    --endpoint http://localhost:8000 \
    --username root \
    --password root \
    --namespace atado \
    --database rag \
    --command "INFO FOR TABLE routing_decisions;" 2>&1 | head -5

echo ""
echo "================================================================================"
echo "DEPLOYMENT COMPLETE ✅"
echo "================================================================================"

