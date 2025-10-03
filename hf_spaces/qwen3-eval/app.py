"""
Qwen3-8B FP16 Evaluation on ZeroGPU

Evaluates Qwen3-8B (FP16) using Transformers on HuggingFace ZeroGPU (H200).
Batched processing to work within 120s timeout.

Pattern: Lazy model loading (first call) + caching to avoid startup timeout.
"""

import spaces
import gradio as gr
import json
import time
from typing import List, Dict, Any
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM


# Model configuration
MODEL_ID = "Qwen/Qwen3-8B"  # Qwen3 doesn't use -Instruct suffix

# Global cache for model (loaded on first use)
_model = None
_tokenizer = None


def load_model_if_needed():
    """Lazy-load model on first call to avoid startup timeout."""
    global _model, _tokenizer

    if _model is not None:
        return _model, _tokenizer

    print(f"🔧 Loading model (first call): {MODEL_ID}")
    print(f"   Size: 8B parameters (Qwen3)")
    print(f"   Precision: FP16 (torch.float16)")

    _tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)

    _model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        torch_dtype=torch.float16,
        device_map="auto"
    )

    print("✓ Model loaded")
    return _model, _tokenizer


def parse_test_examples(test_data_text: str) -> List[Dict[str, Any]]:
    """Parse JSONL test data (handles both single-line and formatted JSON)."""
    examples = []

    # Try standard JSONL parsing (one JSON per line)
    try:
        for line in test_data_text.strip().split('\n'):
            if line.strip():
                examples.append(json.loads(line))
        return examples
    except json.JSONDecodeError:
        pass  # Fall through to alternative parsing

    # Alternative: Parse as JSON array or handle multi-line JSON
    try:
        # Try parsing as JSON array
        parsed = json.loads(test_data_text)
        if isinstance(parsed, list):
            return parsed
        elif isinstance(parsed, dict):
            return [parsed]
    except json.JSONDecodeError:
        pass

    # Last resort: Use a more robust JSONL parser
    # Split by }{ pattern and reconstruct
    import re
    json_objects = re.split(r'}\s*{', test_data_text.strip())

    for i, obj_str in enumerate(json_objects):
        # Add back braces except for first and last
        if i > 0:
            obj_str = '{' + obj_str
        if i < len(json_objects) - 1:
            obj_str = obj_str + '}'

        try:
            examples.append(json.loads(obj_str.strip()))
        except json.JSONDecodeError as e:
            print(f"Warning: Failed to parse JSON object {i}: {e}")
            continue

    return examples


def extract_prompt_and_expected(example: Dict[str, Any]) -> tuple:
    """Extract prompt and expected response from test example."""
    text = example["text"]
    parts = text.split("<|im_end|>")

    # Build prompt
    system_msg = parts[0] + "<|im_end|>"
    user_msg = parts[1] + "<|im_end|>"
    prompt = system_msg + user_msg + "\n<|im_start|>assistant\n"

    # Extract expected
    assistant_part = parts[2].strip()
    expected_response = assistant_part.replace("<|im_start|>assistant\n", "")

    return prompt, expected_response


def check_success(generated: str, expected: str) -> bool:
    """Check if generation is successful (length heuristic)."""
    if not generated:
        return False

    gen_len = len(generated)
    exp_len = len(expected)

    if exp_len == 0:
        return gen_len > 0

    ratio = gen_len / exp_len
    return 0.5 <= ratio <= 2.0


@spaces.GPU(duration=120)
def evaluate_batch(
    examples: List[Dict[str, Any]],
    batch_start: int,
    batch_size: int
) -> Dict[str, Any]:
    """
    Evaluate a batch of examples on GPU.

    ZeroGPU decorator allocates H200 GPU for 120 seconds.
    Model is lazy-loaded on first call and cached.
    """
    # Lazy-load model (cached after first call)
    model, tokenizer = load_model_if_needed()

    batch_results = []
    batch_end = min(batch_start + batch_size, len(examples))

    print(f"\n🚀 Evaluating batch {batch_start}-{batch_end} on ZeroGPU H200...")

    for i in range(batch_start, batch_end):
        example = examples[i]
        prompt, expected = extract_prompt_and_expected(example)

        # Run inference
        start_time = time.time()

        try:
            # Tokenize
            inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

            # Generate
            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=512,
                    temperature=0.0,
                    do_sample=False,
                    pad_token_id=tokenizer.eos_token_id,
                    eos_token_id=tokenizer.eos_token_id
                )

            # Decode
            full_output = tokenizer.decode(outputs[0], skip_special_tokens=True)
            generated = full_output[len(tokenizer.decode(inputs['input_ids'][0], skip_special_tokens=True)):]
            generated = generated.strip()

            latency = time.time() - start_time

        except Exception as e:
            print(f"Inference error: {e}")
            generated = ""
            latency = time.time() - start_time

        success = check_success(generated, expected)

        result = {
            "example_id": i,
            "agent": example.get("agent", "unknown"),
            "task_id": example.get("task_id", f"task_{i}"),
            "success": success,
            "latency": round(latency, 2),
            "generated_length": len(generated),
            "expected_length": len(expected)
        }

        batch_results.append(result)

        status = "✓" if success else "✗"
        print(f"  {status} Example {i}: {latency:.2f}s, {len(generated)} chars")

    return {
        "batch_start": batch_start,
        "batch_end": batch_end,
        "results": batch_results
    }


def run_full_evaluation(test_data_text: str, batch_size: int = 5, progress=gr.Progress()):
    """
    Run full evaluation in batches.

    Each batch runs on ZeroGPU for up to 120s.
    """
    # Parse test data
    progress(0.1, desc="Parsing test data...")
    examples = parse_test_examples(test_data_text)
    total_examples = len(examples)

    if total_examples == 0:
        return "**Error:** No examples found in test data", "{}"

    print(f"\n📊 Evaluating {total_examples} examples in batches of {batch_size}")

    # Run batched evaluation
    all_results = []
    num_batches = (total_examples + batch_size - 1) // batch_size

    for batch_idx in range(num_batches):
        batch_start = batch_idx * batch_size
        progress_pct = 0.1 + (batch_idx / num_batches) * 0.9
        progress(progress_pct, desc=f"Evaluating batch {batch_idx + 1}/{num_batches}...")

        # This call gets GPU allocation via @spaces.GPU decorator
        batch_result = evaluate_batch(
            examples,
            batch_start,
            batch_size
        )

        all_results.extend(batch_result["results"])

    # Compute metrics
    progress(0.95, desc="Computing metrics...")

    total = len(all_results)
    successful = sum(1 for r in all_results if r["success"])
    failed = total - successful

    latencies = [r["latency"] for r in all_results]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0

    success_rate = (successful / total * 100) if total > 0 else 0

    # Agent breakdown
    agent_stats = {}
    for result in all_results:
        agent = result["agent"]
        if agent not in agent_stats:
            agent_stats[agent] = {"total": 0, "successes": 0, "latencies": []}

        agent_stats[agent]["total"] += 1
        if result["success"]:
            agent_stats[agent]["successes"] += 1
        agent_stats[agent]["latencies"].append(result["latency"])

    agent_breakdown = {}
    for agent, stats in agent_stats.items():
        agent_breakdown[agent] = {
            "total": stats["total"],
            "success_rate": round((stats["successes"] / stats["total"] * 100), 2),
            "avg_latency": round(sum(stats["latencies"]) / len(stats["latencies"]), 2)
        }

    # Final results
    results = {
        "model": "Qwen3-8B-FP16",
        "hardware": "ZeroGPU H200",
        "total_examples": total,
        "successful": successful,
        "failed": failed,
        "success_rate": round(success_rate, 2),
        "avg_latency": round(avg_latency, 2),
        "min_latency": round(min(latencies), 2),
        "max_latency": round(max(latencies), 2),
        "agent_breakdown": agent_breakdown,
        "detailed_results": all_results
    }

    progress(1.0, desc="Complete!")

    # Format output
    summary = f"""# Evaluation Results

**Model**: Qwen3-8B-FP16 (ZeroGPU H200)

## Overall Metrics
- **Success Rate**: {success_rate:.2f}% ({successful}/{total} examples)
- **Avg Latency**: {avg_latency:.2f}s
- **Min/Max Latency**: {min(latencies):.2f}s / {max(latencies):.2f}s

## Agent Performance
"""

    for agent, stats in agent_breakdown.items():
        summary += f"\n- **{agent}**: {stats['success_rate']:.1f}% success, {stats['avg_latency']:.2f}s avg"

    return summary, json.dumps(results, indent=2)


# Gradio Interface
with gr.Blocks(title="Qwen3-8B FP16 Evaluation") as demo:
    gr.Markdown("""
    # 🚀 Qwen3-8B FP16 Evaluation on ZeroGPU

    Evaluate Qwen3-8B (FP16) using Transformers on HuggingFace ZeroGPU (H200 GPU).

    **Features:**
    - Runs on **H200 GPU** (FREE with HF Pro)
    - Native Transformers + ZeroGPU integration
    - Batched processing (5-10 examples per batch)
    - Real-time progress tracking
    - Detailed metrics and agent breakdown
    """)

    with gr.Row():
        with gr.Column():
            test_data = gr.Textbox(
                label="Test Data (JSONL)",
                placeholder='Paste your test.jsonl content here...',
                lines=10,
                value=""
            )

            batch_size = gr.Slider(
                minimum=1,
                maximum=10,
                value=5,
                step=1,
                label="Batch Size (examples per GPU call)",
                info="Smaller = safer (more GPU calls), Larger = faster (fewer calls)"
            )

            run_btn = gr.Button("🚀 Run Evaluation", variant="primary")

        with gr.Column():
            summary_output = gr.Markdown(label="Summary")
            json_output = gr.JSON(label="Detailed Results")

    run_btn.click(
        fn=run_full_evaluation,
        inputs=[test_data, batch_size],
        outputs=[summary_output, json_output]
    )

    gr.Markdown("""
    ## How It Works

    1. **Setup** (First Call): Model downloads on first batch (cached afterward)
    2. **Batch Processing** (GPU): Runs 5-10 examples per ZeroGPU call (120s limit)
    3. **Aggregation** (CPU): Combines results and computes metrics

    ## Tips

    - **First batch**: Takes ~3-5 min (model download within GPU context)
    - **Subsequent batches**: Fast (~10-20s per batch)
    - **Batch size**: 5 = safer, 10 = faster but may timeout on slow examples
    - **Free with Pro**: Unlimited usage with HF Pro subscription

    ## Comparison

    - **FP16 (this)**: Best quality, GPU-accelerated, ~16GB VRAM (8B model)
    - **Q5_K_M**: Good quality, 5.5GB (CPU only with llama.cpp)
    - **Q4_K_M**: Fair quality, 4.5GB (CPU only, 48% success baseline)
    """)


if __name__ == "__main__":
    demo.launch(show_error=True)
