# Quickstart Guide

Get started with Autonomous Task-Agent Dev Orchestration (ATADO) in 5 minutes.

## Prerequisites

- Installed `atado` (see [INSTALL.md](INSTALL.md))
- xAI API key (get from https://x.ai/)

## 1. Configure API Key

```bash
# Option A: Environment variable
export XAI_API_KEY=your_api_key_here

# Option B: Create .env file (recommended)
cat > .env <<EOF
XAI_API_KEY=your_api_key_here
EOF
```

## 2. Your First Task

```bash
atado "Explain what clean architecture is in 3 sentences"
```

**Expected Output:**
```
╔══════════════════════════════════════════════════════════════════════════════╗
║ Task: Explain what clean architecture is in 3 sentences                     ║
╚══════════════════════════════════════════════════════════════════════════════╝

Clean architecture is a software design philosophy that separates concerns
into independent layers, with business logic at the core, isolated from
frameworks and external dependencies. It emphasizes the dependency rule,
where dependencies point inward toward the core domain, making the system
easier to test, maintain, and adapt to change. The architecture promotes
flexibility by allowing you to swap out infrastructure components without
affecting the core business rules.

✓ Task completed successfully
```

## 3. Multi-Task Orchestration

Run multiple tasks in sequence:

```bash
atado \
  "Research: What are the key principles of clean code?" \
  "Summarize: List the top 5 principles from the research" \
  "Apply: Give an example of applying one principle"
```

**How it works:**
- Tasks execute in order
- Each task can build on previous results
- Results are aggregated at the end

## 4. Parallel Execution

Run tasks simultaneously for faster results:

```bash
atado --parallel \
  "Explain dependency injection" \
  "Explain dependency inversion" \
  "Explain interface segregation"
```

**Use cases:**
- Independent research tasks
- Comparing multiple approaches
- Gathering diverse perspectives

## 5. Provider Selection

Use different AI providers (currently supports Grok):

```bash
# Explicit provider selection
atado --provider grok "Analyze SOLID principles"

# Specify model
atado --provider grok --model grok-beta "Your task here"
```

## Common Use Cases

### Use Case 1: Code Review

```bash
atado "Review this Python function for clean code principles:
def calc(a,b,c):
    if c==1:
        return a+b
    elif c==2:
        return a-b
    else:
        return a*b
"
```

### Use Case 2: Architecture Analysis

```bash
atado \
  "Analyze: Describe the current state of microservices architecture" \
  "Pros/Cons: List advantages and disadvantages" \
  "Recommendation: Should a startup use microservices?"
```

### Use Case 3: Problem Solving

```bash
atado --parallel \
  "Solution A: How to implement caching with Redis?" \
  "Solution B: How to implement caching with Memcached?" \
  "Compare: Which caching solution is better for a Python web app?"
```

### Use Case 4: Research & Summary

```bash
atado \
  "Research: What is the difference between REST and GraphQL?" \
  "Synthesize: Create a comparison table" \
  "Decide: Which should I use for a mobile app backend?"
```

## Advanced Features

### Custom Configuration

Create `config.json` for persistent settings:

```json
{
  "provider": "grok",
  "model": "grok-beta",
  "provider_config": {
    "api_key": "${XAI_API_KEY}",
    "timeout": 30,
    "max_retries": 3
  }
}
```

Use with:
```bash
atado --config config.json "Your task here"
```

### Output Formatting

```bash
# JSON output (for scripting)
atado --output json "List 3 design patterns" > output.json

# Verbose mode (show details)
atado --verbose "Complex analysis task"

# Quiet mode (minimal output)
atado --quiet "Simple task"
```

### Error Handling

```bash
# Retry on failure
atado --max-retries 5 "Task that might fail"

# Timeout control
atado --timeout 60 "Long-running task"
```

## Best Practices

### 1. Task Design

**Good:**
```bash
atado "Explain SOLID principles with a Python example for Single Responsibility"
```

**Better:**
```bash
atado \
  "Explain: What is the Single Responsibility Principle?" \
  "Example: Provide a Python code example violating SRP" \
  "Refactor: Show how to refactor the example to follow SRP"
```

### 2. Use Descriptive Task Names

**Good:**
```bash
atado "Task 1: Research" "Task 2: Analyze"
```

**Better:**
```bash
atado \
  "Research: Gather information on clean architecture" \
  "Analyze: Identify key patterns in the research" \
  "Synthesize: Create a summary of findings"
```

### 3. Chain Related Tasks

```bash
atado \
  "Define: What is technical debt?" \
  "Identify: List 5 common causes of technical debt" \
  "Prevent: Suggest strategies to avoid each cause"
```

### 4. Use Parallel for Independent Tasks

```bash
atado --parallel \
  "Research topic A independently" \
  "Research topic B independently" \
  "Research topic C independently"
```

## Integration Examples

### Shell Scripts

```bash
#!/bin/bash
# analyze.sh

export XAI_API_KEY="your_key"

echo "Analyzing codebase..."
atado \
  "Analyze: Review the code structure in $(pwd)" \
  "Recommendations: Suggest improvements" \
  "Prioritize: Rank improvements by impact"

echo "Analysis complete!"
```

### Python Integration

```python
import subprocess
import json
import os

os.environ['XAI_API_KEY'] = 'your_key'

def run_analysis(tasks):
    """Run UI-CLI analysis tasks."""
    result = subprocess.run(
        ['atado', '--output', 'json'] + tasks,
        capture_output=True,
        text=True
    )
    return json.loads(result.stdout)

# Example usage
tasks = [
    "Research: What is clean architecture?",
    "Summarize: Key principles in 5 points"
]

results = run_analysis(tasks)
print(results)
```

### CI/CD Integration

```yaml
# .github/workflows/ai-review.yml
name: AI Code Review

on: [pull_request]

jobs:
  ai-review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Install UI-CLI
        run: pip install autonomous-task-agent-dev-orchestration
      
      - name: Run AI Review
        env:
          XAI_API_KEY: ${{ secrets.XAI_API_KEY }}
        run: |
          atado \
            "Review: Analyze the code changes in this PR" \
            "Quality: Rate code quality (1-10)" \
            "Suggestions: List 3 improvements"
```

### Docker Integration

```bash
# Run in Docker with volume mount
docker run --rm \
  -v $(pwd):/workspace \
  -w /workspace \
  -e XAI_API_KEY=$XAI_API_KEY \
  autonomous-task-agent-dev-orchestration:latest \
  "Analyze the project structure in /workspace"
```

## Performance Tips

### 1. Use Parallel Execution

```bash
# Slow (sequential): ~30 seconds
atado "Task A" "Task B" "Task C"

# Fast (parallel): ~10 seconds
atado --parallel "Task A" "Task B" "Task C"
```

### 2. Optimize Task Granularity

**Too granular (10 API calls):**
```bash
atado "What is X?" "What is Y?" "What is Z?" ...
```

**Optimal (1 API call):**
```bash
atado "Explain X, Y, and Z in detail"
```

### 3. Cache Responses

```bash
# Save response for reuse
atado "Complex research task" > research.txt

# Reuse saved research
cat research.txt
```

## Troubleshooting

### Issue: "No API key found"

```bash
# Check if key is set
echo $XAI_API_KEY

# Set key
export XAI_API_KEY=your_key
```

### Issue: "Rate limit exceeded"

```bash
# Add delay between tasks
atado "Task 1"
sleep 2
atado "Task 2"
```

### Issue: "Command not found: atado"

```bash
# Use full command
autonomous-task-agent-dev-orchestration --help

# Or run via Python
python -m src.main --help
```

## Next Steps

1. **Read Documentation:**
   - [Installation Guide](INSTALL.md) - Detailed installation instructions
   - [Release Process](RELEASE.md) - For contributors
   - [Implementation Details](IMPLEMENTATION_COMPLETE.md) - Architecture deep dive

2. **Explore Examples:**
   - Check `examples/` directory for sample scripts
   - Review `tests/` for usage patterns

3. **Join Community:**
   - Report issues: https://github.com/yourusername/autonomous-task-agent-dev-orchestration/issues
   - Contribute: See CONTRIBUTING.md

4. **Advanced Topics:**
   - Custom providers (extend the framework)
   - Plugin development (add new features)
   - Performance optimization (tune for your use case)

## Quick Reference

```bash
# Basic usage
atado "Your task"

# Multiple tasks
atado "Task 1" "Task 2" "Task 3"

# Parallel execution
atado --parallel "Task 1" "Task 2"

# Provider selection
atado --provider grok "Task"

# Configuration file
atado --config config.json "Task"

# Output format
atado --output json "Task"

# Help
atado --help

# Version
atado --version
```

---

**Last Updated:** 2025-09-30
**Version:** 1.0.0
**For Support:** See [INSTALL.md](INSTALL.md#support)
