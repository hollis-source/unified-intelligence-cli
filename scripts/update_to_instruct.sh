#!/bin/bash
# Update all scripts to use Instruct model instead of Thinking

echo "Updating scripts to use Qwen3-Next-80B-A3B-Instruct..."

# Replace model name in all scripts
find scripts -type f -name "*.py" -exec sed -i 's/Qwen\/Qwen3-Next-80B-A3B-Thinking/Qwen\/Qwen3-Next-80B-A3B-Instruct/g' {} +

# Remove thinking_mode=True or change to False
find scripts -type f -name "*.py" -exec sed -i 's/"thinking_mode": True/"thinking_mode": False/g' {} +
find scripts -type f -name "*.py" -exec sed -i "s/'thinking_mode': True/'thinking_mode': False/g" {} +

# Update comments
find scripts -type f -name "*.py" -exec sed -i 's/Qwen3-Next-80B-A3B-Thinking/Qwen3-Next-80B-A3B-Instruct/g' {} +

echo "✅ Scripts updated successfully!"
echo ""
echo "Updated files:"
find scripts -type f -name "*.py" | xargs grep -l "Qwen3-Next-80B-A3B-Instruct" | head -20
