#!/usr/bin/env python3
"""Test HF Inference latency with simple tasks."""

import time
import os
from dotenv import load_dotenv
from pathlib import Path

env_file = Path(__file__).parent / ".env"
if env_file.exists():
    load_dotenv(env_file)

from src.adapters.llm.qwen3_hf_inference_adapter import Qwen3HFInferenceAdapter
from src.interfaces import LLMConfig

def test_simple_tasks():
    """Test with simple short-response tasks."""

    adapter = Qwen3HFInferenceAdapter()

    # Very simple tasks that should complete quickly
    tasks = [
        {"messages": [{"role": "user", "content": "Say hi"}], "max_tokens": 10},
        {"messages": [{"role": "user", "content": "What is 1+1?"}], "max_tokens": 5},
        {"messages": [{"role": "user", "content": "Name one color"}], "max_tokens": 5},
        {"messages": [{"role": "user", "content": "Yes or no: is Python a language?"}], "max_tokens": 3},
        {"messages": [{"role": "user", "content": "Say hello"}], "max_tokens": 10},
    ]

    print("Testing HF Inference latency with simple tasks (max_tokens limited)")
    print("="*60)

    latencies = []

    for i, task in enumerate(tasks, 1):
        messages = task["messages"]
        config = LLMConfig(max_tokens=task["max_tokens"], temperature=0.7)

        print(f"\nTask {i}: {messages[0]['content']} (max_tokens={task['max_tokens']})")

        start = time.time()
        try:
            response = adapter.generate(messages, config)
            elapsed = time.time() - start
            latencies.append(elapsed)

            print(f"  Latency: {elapsed:.2f}s")
            print(f"  Response: {response}")
        except Exception as e:
            print(f"  Error: {e}")

    if latencies:
        print("\n" + "="*60)
        print(f"Average latency: {sum(latencies)/len(latencies):.2f}s")
        print(f"Min latency: {min(latencies):.2f}s")
        print(f"Max latency: {max(latencies):.2f}s")
        print("="*60)

if __name__ == "__main__":
    test_simple_tasks()
