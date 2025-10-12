#!/bin/bash
# Parallel Chunked Upload to Replicate
# Bypasses single TCP stream limitation

MODEL_FILE="$1"
CHUNK_SIZE_MB="${2:-500}"  # 500MB chunks default
MAX_PARALLEL="${3:-8}"     # 8 parallel uploads

if [ -z "$MODEL_FILE" ]; then
    echo "Usage: $0 <model_file> [chunk_size_mb] [max_parallel]"
    exit 1
fi

FILE_SIZE=$(stat -f%z "$MODEL_FILE" 2>/dev/null || stat -c%s "$MODEL_FILE")
CHUNK_SIZE=$((CHUNK_SIZE_MB * 1024 * 1024))
NUM_CHUNKS=$(( (FILE_SIZE + CHUNK_SIZE - 1) / CHUNK_SIZE ))

echo "📦 Parallel Upload Optimizer"
echo "  File: $MODEL_FILE"
echo "  Size: $((FILE_SIZE / 1024 / 1024 / 1024))GB"
echo "  Chunks: $NUM_CHUNKS × ${CHUNK_SIZE_MB}MB"
echo "  Parallel: $MAX_PARALLEL streams"
echo ""

# Split file into chunks
echo "🔪 Splitting file..."
split -b ${CHUNK_SIZE} -d "$MODEL_FILE" /tmp/model_chunk_

# Upload chunks in parallel using xargs
echo "⚡ Uploading $NUM_CHUNKS chunks with $MAX_PARALLEL parallel streams..."
ls /tmp/model_chunk_* | xargs -n 1 -P $MAX_PARALLEL -I {} bash -c '
    CHUNK={}
    echo "  ⬆️  Uploading $(basename $CHUNK)..."
    # Replicate upload would go here
    # For now, test with httpbin
    curl -X POST -F "file=@$CHUNK" https://httpbin.org/post -o /dev/null -s -w "    ✓ $(basename $CHUNK): %{speed_upload} bytes/sec\n"
    rm "$CHUNK"
'

echo "✅ Upload complete!"
