"""
Qwen3-8B Q5_K_M Evaluation on ZeroGPU

Evaluates GGUF models using llama.cpp on HuggingFace ZeroGPU (H200).
Batched processing to work within 120s timeout.
"""

import spaces
import gradio as gr
import subprocess
import json
import time
import os
from pathlib import Path
from typing import List, Dict, Any
import huggingface_hub


# Model and data paths
MODEL_REPO = "unsloth/Qwen3-8B-GGUF"
MODEL_FILE = "Qwen3-8B-Q5_K_M.gguf"
MODEL_PATH = Path("models") / MODEL_FILE
LLAMA_CLI = Path("llama.cpp/build/bin/llama-cli")


def download_model():
    """Download GGUF model from HuggingFace (cached)."""
    if MODEL_PATH.exists():
        print(f"✓ Model already downloaded: {MODEL_PATH}")
        return str(MODEL_PATH)

    print(f"📥 Downloading {MODEL_FILE}...")
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)

    huggingface_hub.hf_hub_download(
        repo_id=MODEL_REPO,
        filename=MODEL_FILE,
        local_dir=str(MODEL_PATH.parent),
        local_dir_use_symlinks=False
    )

    print(f"✓ Downloaded to {MODEL_PATH}")
    return str(MODEL_PATH)


def setup_llama_cpp():
    """Build llama.cpp with CUDA support (cached)."""
    if LLAMA_CLI.exists():
        print(f"✓ llama.cpp already built: {LLAMA_CLI}")
        return str(LLAMA_CLI)

    print("🔧 Building llama.cpp with CUDA...")

    # Clone if needed
    if not Path("llama.cpp").exists():
        subprocess.run([
            "git", "clone",
            "https://github.com/ggerganov/llama.cpp",
            "llama.cpp"
        ], check=True)

    # Build with CUDA
    subprocess.run([
        "cmake", "-B", "llama.cpp/build",
        "-DGGML_CUDA=ON",
        "llama.cpp"
    ], check=True)

    subprocess.run([
        "cmake", "--build", "llama.cpp/build",
        "--config", "Release"
    ], check=True)

    print(f"✓ Built llama.cpp: {LLAMA_CLI}")
    return str(LLAMA_CLI)


def parse_test_examples(test_data_text: str) -> List[Dict[str, Any]]:
    """Parse JSONL test data."""
    examples = []
    for line in test_data_text.strip().split('\n'):
        if line.strip():
            examples.append(json.loads(line))
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


def run_inference(model_path: str, prompt: str, max_tokens: int = 512) -> tuple:
    """Run inference using llama.cpp. Returns (generated_text, latency)."""
    cmd = [
        str(LLAMA_CLI),
        "-m", model_path,
        "-p", prompt,
        "-n", str(max_tokens),
        "--temp", "0.0",
        "-ngl", "99",  # Offload all layers to GPU
        "-t", "8",     # Use 8 threads
        "--log-disable"
    ]

    start_time = time.time()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,  # 30s per example
            check=False
        )
        latency = time.time() - start_time

        output = result.stdout

        # Extract generated text
        if "<|im_start|>assistant" in output:
            generated = output.split("<|im_start|>assistant")[-1]
            generated = generated.split("<|im_end|>")[0].strip()
        else:
            generated = output.strip()

        return generated, latency

    except subprocess.TimeoutExpired:
        return "", time.time() - start_time
    except Exception as e:
        print(f"Inference error: {e}")
        return "", 0.0


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
    model_path: str,
    examples: List[Dict[str, Any]],
    batch_start: int,
    batch_size: int
) -> Dict[str, Any]:
    """
    Evaluate a batch of examples on GPU.

    ZeroGPU decorator allocates H200 GPU for 120 seconds.
    """
    batch_results = []
    batch_end = min(batch_start + batch_size, len(examples))

    print(f"\n🚀 Evaluating batch {batch_start}-{batch_end} on ZeroGPU H200...")

    for i in range(batch_start, batch_end):
        example = examples[i]
        prompt, expected = extract_prompt_and_expected(example)

        # Run inference
        generated, latency = run_inference(model_path, prompt)
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
    # Setup (runs on CPU, cached)
    progress(0, desc="Setting up llama.cpp...")
    llama_cli = setup_llama_cpp()

    progress(0.1, desc="Downloading model...")
    model_path = download_model()

    # Parse test data
    progress(0.2, desc="Parsing test data...")
    examples = parse_test_examples(test_data_text)
    total_examples = len(examples)

    if total_examples == 0:
        return {"error": "No examples found in test data"}

    print(f"\n📊 Evaluating {total_examples} examples in batches of {batch_size}")

    # Run batched evaluation
    all_results = []
    num_batches = (total_examples + batch_size - 1) // batch_size

    for batch_idx in range(num_batches):
        batch_start = batch_idx * batch_size
        progress_pct = 0.2 + (batch_idx / num_batches) * 0.8
        progress(progress_pct, desc=f"Evaluating batch {batch_idx + 1}/{num_batches}...")

        # This call gets GPU allocation via @spaces.GPU decorator
        batch_result = evaluate_batch(
            model_path,
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
        "model": "Qwen3-8B-Q5_K_M",
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

**Model**: Qwen3-8B-Q5_K_M (ZeroGPU H200)

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
with gr.Blocks(title="Qwen3-8B Q5_K_M Evaluation") as demo:
    gr.Markdown("""
    # 🚀 Qwen3-8B Q5_K_M Evaluation on ZeroGPU

    Evaluate GGUF models using llama.cpp on HuggingFace ZeroGPU (H200 GPU).

    **Features:**
    - Runs on **H200 GPU** (FREE with HF Pro)
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
                value=""  # Will be populated from file
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

    1. **Setup** (CPU): Downloads model and builds llama.cpp (cached after first run)
    2. **Batch Processing** (GPU): Runs 5-10 examples per ZeroGPU call (120s limit)
    3. **Aggregation** (CPU): Combines results and computes metrics

    ## Tips

    - **First run**: Takes ~2-3 min for setup (cached afterward)
    - **Subsequent runs**: Much faster (model and llama.cpp cached)
    - **Batch size**: 5 = safer, 10 = faster but may timeout on slow examples
    - **Free with Pro**: Unlimited usage with HF Pro subscription
    """)


if __name__ == "__main__":
    demo.launch()
