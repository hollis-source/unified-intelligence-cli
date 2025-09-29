#!/usr/bin/env python3
"""Have Grok verify the GrokSession implementation."""

import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

api_key = os.getenv("XAI_API_KEY")
client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")

# The GrokSession code for review
code_to_verify = '''#!/usr/bin/env python3
"""
Optimized GrokSession class for programmatic interaction with Grok.
Based on Grok's own recommendations for structured outputs and state management.
"""

import asyncio
import json
import os
from typing import Dict, List, Optional, Any, Callable
from dotenv import load_dotenv
from openai import AsyncOpenAI, OpenAI

load_dotenv()

class GrokSession:
    """
    A session class for interacting with Grok via OpenAI-compatible API.
    Maintains conversation state, handles streaming, and returns structured outputs.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "grok-code-fast-1",
        base_url: str = "https://api.x.ai/v1",
        system_prompt: Optional[str] = None
    ):
        self.api_key = api_key or os.getenv("XAI_API_KEY")
        if not self.api_key:
            raise ValueError("XAI_API_KEY not provided or in environment")

        # Initialize clients with xAI base URL
        self.async_client = AsyncOpenAI(api_key=self.api_key, base_url=base_url)
        self.sync_client = OpenAI(api_key=self.api_key, base_url=base_url)
        self.model = model
        self.messages: List[Dict[str, Any]] = []

        # Tool functions registry
        self.tool_functions: Dict[str, Callable] = {
            "calculate_math": self._calculate_math
        }

        # Default tools available
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "calculate_math",
                    "description": "Evaluate a mathematical expression",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "expression": {"type": "string", "description": "Math expression to evaluate"}
                        },
                        "required": ["expression"]
                    }
                }
            }
        ]

        if system_prompt:
            self.messages.append({"role": "system", "content": system_prompt})

    def _calculate_math(self, expression: str) -> str:
        """Built-in math calculation tool."""
        try:
            return str(eval(expression))
        except Exception as e:
            return f"Calculation error: {str(e)}"

    def add_tool(self, tool_definition: Dict, tool_function: Callable) -> None:
        """Add a custom tool to the session."""
        self.tools.append(tool_definition)
        tool_name = tool_definition["function"]["name"]
        self.tool_functions[tool_name] = tool_function

    def clear_history(self, keep_system: bool = True) -> None:
        """Clear message history, optionally keeping system message."""
        if keep_system and self.messages and self.messages[0]["role"] == "system":
            self.messages = [self.messages[0]]
        else:
            self.messages = []

    async def send_message_async(
        self,
        user_message: str,
        stream: bool = True,
        use_tools: bool = True,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """Async method to send a message to Grok."""
        self.messages.append({"role": "user", "content": user_message})

        kwargs = {
            "model": self.model,
            "messages": self.messages,
            "temperature": temperature,
            "stream": stream
        }

        if use_tools and self.tools:
            kwargs["tools"] = self.tools
            kwargs["tool_choice"] = "auto"

        response_text = ""
        tool_calls = []
        tool_results = []

        try:
            if stream:
                stream_response = await self.async_client.chat.completions.create(**kwargs)
                async for chunk in stream_response:
                    if chunk.choices:
                        delta = chunk.choices[0].delta
                        if delta.content:
                            response_text += delta.content
                        if delta.tool_calls:
                            for tc in delta.tool_calls:
                                tool_calls.append(tc)
            else:
                response = await self.async_client.chat.completions.create(**kwargs)
                choice = response.choices[0]
                response_text = choice.message.content or ""
                if choice.message.tool_calls:
                    tool_calls = choice.message.tool_calls

            assistant_message = {"role": "assistant", "content": response_text}
            if tool_calls:
                assistant_message["tool_calls"] = [tc.model_dump() for tc in tool_calls]
            self.messages.append(assistant_message)

            # Execute tools if any
            if tool_calls:
                for tool_call in tool_calls:
                    func_name = tool_call.function.name
                    if func_name in self.tool_functions:
                        func_args = json.loads(tool_call.function.arguments)
                        result = self.tool_functions[func_name](**func_args)
                        tool_results.append({
                            "tool": func_name,
                            "args": func_args,
                            "result": result
                        })
                        self.messages.append({
                            "role": "tool",
                            "content": result,
                            "tool_call_id": tool_call.id
                        })

                # Get final response after tool execution
                follow_up = await self.async_client.chat.completions.create(
                    model=self.model,
                    messages=self.messages,
                    temperature=temperature
                )
                final_text = follow_up.choices[0].message.content
                response_text = final_text if final_text else response_text
                if final_text:
                    self.messages.append({"role": "assistant", "content": final_text})

        except Exception as e:
            response_text = f"Error: {str(e)}"
            tool_calls = []
            tool_results = []

        return {
            "response": response_text,
            "tool_calls": [tc.model_dump() if hasattr(tc, 'model_dump') else tc for tc in tool_calls],
            "tool_results": tool_results,
            "messages": self.messages.copy(),
            "message_count": len(self.messages)
        }

    def send_message_sync(self, user_message: str, use_tools: bool = True, temperature: float = 0.7) -> Dict[str, Any]:
        """Synchronous version for non-async contexts."""
        # Similar implementation but synchronous
        # [Implementation details omitted for brevity but follows same pattern]
        pass

    def send_message(self, user_message: str, async_mode: bool = False, **kwargs) -> Dict[str, Any]:
        """Main programmatic entry point."""
        if async_mode:
            return asyncio.run(self.send_message_async(user_message, **kwargs))
        else:
            return self.send_message_sync(user_message, **kwargs)

    def get_conversation_summary(self) -> str:
        """Get a summary of the conversation so far."""
        summary = []
        for msg in self.messages:
            role = msg["role"]
            content = msg.get("content", "")
            if content:
                preview = content[:100] + "..." if len(content) > 100 else content
                summary.append(f"{role}: {preview}")
        return "\\n".join(summary)
'''

messages = [
    {
        "role": "system",
        "content": "You are Grok. Review this Python code implementation that was based on your recommendations."
    },
    {
        "role": "user",
        "content": f"""Please verify this GrokSession implementation I created based on your earlier recommendations.

Check for:
1. Correct implementation of structured outputs (returning dicts)
2. Proper state management (message history)
3. Streaming support implementation
4. Tool execution flow
5. Any bugs, issues, or improvements needed
6. Whether it properly addresses programmatic and iterative use cases

Here's the code:

```python
{code_to_verify}
```

Please provide specific feedback on whether this correctly implements your recommendations and any issues you see."""
    }
]

response = client.chat.completions.create(
    model="grok-code-fast-1",
    messages=messages,
    temperature=0.7
)

print("=== Grok's Code Verification ===\n")
print(response.choices[0].message.content)