# Grok Integration Tools

This directory contains production-ready tools for integrating with Grok (xAI) API.

## Files

### Core Implementation
- **`grok_session.py`** - Full-featured GrokSession class with:
  - Structured outputs (returns dicts)
  - State management (conversation history)
  - Streaming support with proper tool call accumulation
  - Thread safety for concurrent use
  - History persistence (save/load)
  - Retry logic with exponential backoff
  - Comprehensive error handling
  - Custom tool support

### Utilities
- **`consult_grok.py`** - Simple interface for consulting Grok during development:
  ```bash
  # Direct question
  python scripts/consult_grok.py "What's the best pattern for X?"

  # Interactive mode
  python scripts/consult_grok.py --interactive
  ```

- **`grok_chat.py`** - Original chat script with streaming interface

### Testing
- **`test_grok_connection.py`** - Basic connection test
- **`quick_test.py`** - Quick functionality test
- **`test_grok_comprehensive.py`** - Full test suite

## Usage Examples

### Basic Usage
```python
from scripts.grok_session import GrokSession

# Initialize session
session = GrokSession(
    system_prompt="You are a helpful AI assistant.",
    max_history=50
)

# Send message
result = session.send_message("What is 42 * 17?")
print(result['response'])
print(f"Tools used: {result['tool_results']}")
```

### Programmatic Consultation
```python
from scripts.consult_grok import consult_grok

# Get Grok's perspective
response = consult_grok(
    question="How should I implement this feature?",
    context="Current code: ..."
)
```

### Async Streaming
```python
import asyncio
from scripts.grok_session import GrokSession

async def stream_example():
    session = GrokSession()

    # Stream response chunks
    async for chunk in session.stream_message("Tell me a story"):
        print(chunk, end="", flush=True)

asyncio.run(stream_example())
```

### Adding Custom Tools
```python
session = GrokSession()

# Define custom tool
def get_weather(city: str) -> str:
    return f"Weather in {city}: Sunny, 72°F"

tool_def = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get weather for a city",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string"}
            },
            "required": ["city"]
        }
    }
}

# Add to session
session.add_tool(tool_def, get_weather)

# Use it
result = session.send_message("What's the weather in Paris?")
```

### Persistence
```python
# Save conversation
session.save_history("conversation.json")

# Load in new session
new_session = GrokSession()
new_session.load_history("conversation.json")
```

## Key Features Implemented

✅ **All of Grok's Recommendations:**
1. Fixed streaming tool call accumulation by index
2. Fully implemented sync version
3. Fixed asyncio.run for nested event loops
4. Added thread safety with locks
5. Implemented history size limits
6. Added save/load persistence
7. Comprehensive logging system
8. Retry logic with exponential backoff
9. Proper error handling and recovery

## Environment Setup

Make sure your `.env` file contains:
```
XAI_API_KEY=your-xai-api-key-here
```

## Dependencies

- openai
- python-dotenv
- tenacity (for retry logic)
- requests

Install with:
```bash
pip install openai python-dotenv tenacity requests
```

## Notes

- The `eval()` function in math calculations is kept per user request but presents a security risk
- For production use, consider replacing with `numexpr` or `sympy`
- Thread safety is implemented for both sync and async operations
- History is automatically trimmed to prevent unbounded growth
- All API calls include retry logic for resilience