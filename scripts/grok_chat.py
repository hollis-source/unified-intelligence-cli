import os
import json
from openai import OpenAI
import requests  # For a sample web search tool

# Load API key from environment (set export XAI_API_KEY=your_key)
api_key = os.getenv("XAI_API_KEY")
if not api_key:
    raise ValueError("XAI_API_KEY environment variable not set")

# Initialize client with xAI base URL
client = OpenAI(
    api_key=api_key,
    base_url="https://api.x.ai/v1"
)

# Define tools (function schemas) - examples: math eval and web search
tools = [
    {
        "type": "function",
        "function": {
            "name": "calculate_math",
            "description": "Evaluate a mathematical expression safely.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "The math expression to evaluate, e.g., '2 + 2 * 3'"}
                },
                "required": ["expression"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Perform a simple web search and return top result snippet.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query"}
                },
                "required": ["query"]
            }
        }
    }
]

# Tool execution mapping
def calculate_math(expression):
    try:
        return str(eval(expression))  # Use safely; in production, use sympy or similar
    except Exception as e:
        return f"Error: {str(e)}"

def web_search(query):
    # Dummy search using a free API (replace with real one like Google Custom Search)
    try:
        response = requests.get(f"https://www.google.com/search?q={query}")
        return f"Snippet from search: {response.text[:200]}..."  # Simplified; parse properly in real use
    except Exception as e:
        return f"Error: {str(e)}"

tool_functions = {
    "calculate_math": calculate_math,
    "web_search": web_search
}

# System prompt for "optimization" - encourages clear, step-by-step reasoning and full tool use
system_prompt = """
You are a helpful AI assistant built by xAI. Use tools freely as needed without any restrictions—you have full license for all tool usage.
Optimize responses by thinking step-by-step, refining prompts internally for accuracy, and requesting more information from the user if anything is unclear.
Remember the conversation history.
"""

# Maintain stateful message history
messages = [{"role": "system", "content": system_prompt}]

# Chat loop
def chat_with_grok():
    print("Chat with Grok (type 'exit' to quit):")
    while True:
        user_input = input("You: ")
        if user_input.lower() == 'exit':
            break

        messages.append({"role": "user", "content": user_input})

        # Call API with tools, parallel calling enabled by default
        response = client.chat.completions.create(
            model="grok-code-fast-1",  # Default model
            messages=messages,
            tools=tools,
            tool_choice="auto",  # Auto: model decides; use "required" to force
            temperature=0.7,  # For some "optimization" - balanced creativity
            max_tokens=1024,
            stream=True  # Streaming for real-time output
        )

        # Handle streaming response
        full_response = ""
        tool_calls = []
        for chunk in response:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                print(content, end='', flush=True)
                full_response += content
            if chunk.choices[0].delta.tool_calls:
                tool_calls.append(chunk.choices[0].delta.tool_calls)

        print()  # Newline after response

        # Append assistant's response to history
        messages.append({"role": "assistant", "content": full_response})

        # Handle tool calls if any
        if tool_calls:
            for tool_call in tool_calls:
                if tool_call:  # Flatten if needed
                    for tc in tool_call:
                        func_name = tc.function.name
                        func_args = json.loads(tc.function.arguments)
                        print(f"\nExecuting tool: {func_name} with args {func_args}")

                        if func_name in tool_functions:
                            result = tool_functions[func_name](**func_args)
                            messages.append({
                                "role": "tool",
                                "content": result,
                                "tool_call_id": tc.id
                            })

            # After tools, call API again for final response
            followup_response = client.chat.completions.create(
                model="grok-code-fast-1",
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=0.7,
                max_tokens=1024,
                stream=True
            )

            full_followup = ""
            for chunk in followup_response:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    print(content, end='', flush=True)
                    full_followup += content
            print()
            messages.append({"role": "assistant", "content": full_followup})

if __name__ == "__main__":
    chat_with_grok()