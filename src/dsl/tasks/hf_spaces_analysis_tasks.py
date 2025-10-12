"""
HuggingFace Spaces Analysis Tasks for DSL

Week 12+: Analyze HF Spaces GPU options for model evaluation.
Compare pricing and ROI for Pro account holders.

Clean Architecture: Use Cases layer (HF Spaces analysis business logic)
SOLID: SRP - each task has single responsibility
"""

import asyncio
from typing import Any, Dict, List


async def analyze_hf_spaces_gpu_options(input_data: Any = None) -> Dict[str, Any]:
    """
    Analyze HuggingFace Spaces GPU hardware options.

    Returns GPU types, specs, and pricing.
    """
    gpu_options = {
        "t4_small": {
            "name": "T4 Small",
            "vcpu": 4,
            "ram_gb": 15,
            "gpu_memory_gb": 16,
            "gpu_type": "Nvidia T4",
            "cost_per_hour": 0.40,
            "recommended_for": "Small models, development"
        },
        "t4_medium": {
            "name": "T4 Medium",
            "vcpu": 8,
            "ram_gb": 30,
            "gpu_memory_gb": 16,
            "gpu_type": "Nvidia T4",
            "cost_per_hour": 0.60,
            "recommended_for": "Medium models, 8B parameter models"
        },
        "a10g_small": {
            "name": "A10G Small",
            "vcpu": 4,
            "ram_gb": 15,
            "gpu_memory_gb": 24,
            "gpu_type": "Nvidia A10G",
            "cost_per_hour": 1.00,
            "recommended_for": "Larger models"
        },
        "a10g_large": {
            "name": "A10G Large",
            "vcpu": 12,
            "ram_gb": 46,
            "gpu_memory_gb": 24,
            "gpu_type": "Nvidia A10G",
            "cost_per_hour": 1.50,
            "recommended_for": "Production workloads"
        },
        "a100": {
            "name": "A100",
            "vcpu": 12,
            "ram_gb": 142,
            "gpu_memory_gb": 80,
            "gpu_type": "Nvidia A100",
            "cost_per_hour": 4.00,
            "recommended_for": "Large models, heavy compute"
        },
        "h100": {
            "name": "H100",
            "vcpu": 24,
            "ram_gb": 250,
            "gpu_memory_gb": 80,
            "gpu_type": "Nvidia H100",
            "cost_per_hour": 10.00,
            "recommended_for": "Highest performance"
        }
    }

    return {
        "task": "analyze_hf_spaces_gpu_options",
        "status": "success",
        "gpu_options": gpu_options,
        "total_options": len(gpu_options)
    }


async def analyze_hf_pro_benefits(input_data: Any = None) -> Dict[str, Any]:
    """
    Analyze HuggingFace Pro subscription benefits for Spaces.

    Returns Pro account perks and cost savings.
    """
    pro_benefits = {
        "subscription_cost_monthly": 9.00,
        "benefits": {
            "zerogpu_quota_multiplier": 8,
            "inference_credits_multiplier": 20,
            "zerogpu_h200_access": True,
            "dev_mode_ssh": True,
            "highest_queue_priority": True,
            "advanced_compute_options": True,
            "pro_badge": True
        },
        "estimated_savings": {
            "monthly_inference_credits": "~$20-50",
            "zerogpu_value": "Significant for H200 access",
            "priority_queue": "Faster iteration cycles"
        }
    }

    return {
        "task": "analyze_hf_pro_benefits",
        "status": "success",
        "pro_benefits": pro_benefits
    }


async def calculate_hf_spaces_roi(input_data: Any = None) -> Dict[str, Any]:
    """
    Calculate ROI for HuggingFace Spaces GPU deployment.

    Compares cost vs local CPU and other GPU providers.
    """
    # Assumptions
    examples_count = input_data.get("examples_count", 31) if input_data else 31
    developer_hourly_rate = input_data.get("dev_rate", 100) if input_data else 100
    has_pro_account = input_data.get("has_pro", True) if input_data else True

    # CPU baseline (from previous analysis)
    cpu_time_per_example = 592  # seconds
    cpu_total_time_hours = (cpu_time_per_example * examples_count) / 3600
    cpu_developer_cost = cpu_total_time_hours * developer_hourly_rate
    cpu_total_cost = cpu_developer_cost  # No GPU cost

    # GPU timing assumptions
    gpu_time_per_example = 20  # seconds (baseline)
    setup_time_hours = 0.75  # Docker build + Space setup

    # HuggingFace Spaces options
    hf_options = {
        "t4_small": {
            "name": "HF Spaces T4 Small",
            "gpu_cost_per_hour": 0.40,
            "time_per_example": 20,
            "suitable_for_8b": True
        },
        "t4_medium": {
            "name": "HF Spaces T4 Medium",
            "gpu_cost_per_hour": 0.60,
            "time_per_example": 18,  # Slightly faster with more RAM
            "suitable_for_8b": True
        },
        "a10g_small": {
            "name": "HF Spaces A10G Small",
            "gpu_cost_per_hour": 1.00,
            "time_per_example": 12,  # Faster GPU
            "suitable_for_8b": True
        }
    }

    # Competitor options (from previous analysis)
    competitor_options = {
        "modal_t4": {
            "name": "Modal T4",
            "gpu_cost_per_hour": 0.59,
            "time_per_example": 20,
            "setup_time_hours": 0.5
        },
        "lambda_h100": {
            "name": "Lambda Labs H100",
            "gpu_cost_per_hour": 1.99,
            "time_per_example": 8,
            "setup_time_hours": 0.5
        },
        "together_h100": {
            "name": "Together.ai H100",
            "gpu_cost_per_hour": 1.76,
            "time_per_example": 8,
            "setup_time_hours": 0.25
        }
    }

    all_options = {**hf_options, **competitor_options}

    analysis = {}
    for key, option in all_options.items():
        total_time_hours = (option["time_per_example"] * examples_count) / 3600 + option.get("setup_time_hours", setup_time_hours)
        gpu_compute_cost = total_time_hours * option["gpu_cost_per_hour"]

        # Apply Pro credits if applicable (estimate $0.50 credit for this workload)
        if has_pro_account and key.startswith("t4_") or key.startswith("a10g_"):
            # Pro account gets inference credits - estimate 10% discount
            gpu_compute_cost *= 0.9
            pro_discount = True
        else:
            pro_discount = False

        developer_cost = total_time_hours * developer_hourly_rate
        total_cost = gpu_compute_cost + developer_cost

        time_saved_hours = cpu_total_time_hours - total_time_hours
        cost_saved = cpu_total_cost - total_cost
        roi_multiplier = cost_saved / gpu_compute_cost if gpu_compute_cost > 0 else 0
        speedup = cpu_total_time_hours / total_time_hours

        analysis[key] = {
            "name": option["name"],
            "total_time_hours": round(total_time_hours, 2),
            "gpu_compute_cost": round(gpu_compute_cost, 2),
            "developer_cost": round(developer_cost, 2),
            "total_cost": round(total_cost, 2),
            "time_saved_hours": round(time_saved_hours, 2),
            "cost_saved": round(cost_saved, 2),
            "roi_multiplier": round(roi_multiplier, 2),
            "speedup": round(speedup, 1),
            "pro_discount_applied": pro_discount
        }

    # Find best option (considering Pro account)
    hf_best = max(
        [(k, v) for k, v in analysis.items() if k in hf_options],
        key=lambda x: x[1]["cost_saved"]
    )

    overall_best = max(analysis.items(), key=lambda x: x[1]["cost_saved"])

    return {
        "task": "calculate_hf_spaces_roi",
        "status": "success",
        "has_pro_account": has_pro_account,
        "examples_count": examples_count,
        "developer_rate": developer_hourly_rate,
        "cpu_baseline": {
            "total_time_hours": round(cpu_total_time_hours, 2),
            "total_cost": round(cpu_total_cost, 2)
        },
        "all_options": analysis,
        "hf_best_option": {
            "provider": hf_best[1]["name"],
            "key": hf_best[0],
            "savings": hf_best[1]["cost_saved"],
            "speedup": hf_best[1]["speedup"],
            "cost": hf_best[1]["total_cost"],
            "reason": f"Best HF Spaces option: ${hf_best[1]['cost_saved']:.2f} savings, {hf_best[1]['speedup']}x faster"
        },
        "overall_best_option": {
            "provider": overall_best[1]["name"],
            "key": overall_best[0],
            "savings": overall_best[1]["cost_saved"],
            "speedup": overall_best[1]["speedup"],
            "cost": overall_best[1]["total_cost"],
            "reason": f"Best overall: ${overall_best[1]['cost_saved']:.2f} savings, {overall_best[1]['speedup']}x faster"
        }
    }


async def generate_hf_deployment_guide(input_data: Any = None) -> Dict[str, Any]:
    """
    Generate deployment guide for HuggingFace Spaces.

    Returns step-by-step instructions for deploying evaluation to Spaces.
    """
    if not input_data or "hf_best_option" not in input_data:
        roi_data = await calculate_hf_spaces_roi()
        recommended_option = roi_data["hf_best_option"]
    else:
        recommended_option = input_data["hf_best_option"]

    guide_lines = [
        "# HuggingFace Spaces Deployment Guide",
        "",
        f"**Recommended**: {recommended_option['provider']}",
        f"**Cost**: ${recommended_option['cost']:.2f} total",
        f"**Savings**: ${recommended_option['savings']:.2f} vs CPU",
        f"**Speedup**: {recommended_option['speedup']}x faster",
        "",
        "## Prerequisites",
        "",
        "1. HuggingFace Pro account (✓ you have this)",
        "2. Hugging Face CLI installed: `pip install huggingface_hub`",
        "3. Login: `huggingface-cli login`",
        "",
        "## Deployment Steps",
        "",
        "### 1. Create Space",
        "",
        "```bash",
        "# Create new Space via web UI or CLI",
        "# https://huggingface.co/new-space",
        "# Name: qwen3-8b-evaluation",
        "# SDK: Docker",
        "```",
        "",
        "### 2. Create Dockerfile",
        "",
        "```dockerfile",
        "FROM python:3.10-slim",
        "",
        "# Install dependencies",
        "RUN apt-get update && apt-get install -y \\",
        "    git \\",
        "    cmake \\",
        "    build-essential",
        "",
        "# Install Python packages",
        "RUN pip install huggingface_hub",
        "",
        "# Copy evaluation script",
        "COPY training/scripts/evaluate_gguf.py /app/evaluate.py",
        "COPY training/data/test.jsonl /app/test.jsonl",
        "",
        "# Download model",
        "RUN huggingface-cli download unsloth/Qwen3-8B-GGUF Qwen3-8B-Q5_K_M.gguf --local-dir /app/models",
        "",
        "# Install llama.cpp",
        "RUN git clone https://github.com/ggerganov/llama.cpp /app/llama.cpp && \\",
        "    cd /app/llama.cpp && \\",
        "    cmake -B build -DGGML_CUDA=ON && \\",
        "    cmake --build build",
        "",
        "# Run evaluation",
        "CMD python /app/evaluate.py --model /app/models/Qwen3-8B-Q5_K_M.gguf --test-data /app/test.jsonl",
        "```",
        "",
        "### 3. Push to Space",
        "",
        "```bash",
        "git clone https://huggingface.co/spaces/YOUR_USERNAME/qwen3-8b-evaluation",
        "cd qwen3-8b-evaluation",
        "cp training/scripts/evaluate_gguf.py .",
        "cp training/data/test.jsonl .",
        "# Create Dockerfile (see above)",
        "git add .",
        'git commit -m "Add evaluation pipeline"',
        "git push",
        "```",
        "",
        "### 4. Upgrade to GPU",
        "",
        f"1. Go to Space settings",
        f"2. Select **{recommended_option['provider']}**",
        "3. Start Space",
        "4. Monitor logs for results",
        "",
        "### 5. Download Results",
        "",
        "```bash",
        "# Results will be in Space logs or you can output to HF dataset",
        "huggingface-cli download spaces/YOUR_USERNAME/qwen3-8b-evaluation results.json",
        "```",
        "",
        "## Alternative: ZeroGPU (Pro Account Benefit)",
        "",
        "With your Pro account, you get 8x ZeroGPU quota. Consider:",
        "",
        "```python",
        "# Use @spaces.GPU decorator for automatic GPU allocation",
        "import spaces",
        "",
        "@spaces.GPU",
        "def run_evaluation():",
        '    """Evaluation runs on H200 for free with Pro account"""',
        "    # Your evaluation code",
        "```",
        "",
        "## Cost Estimate",
        "",
        f"- Setup time: ~0.75 hours",
        f"- Evaluation time: ~{recommended_option['speedup'] / 10:.1f} hours",
        f"- GPU cost: ${recommended_option['cost']:.2f}",
        "- Pro account discount: Applied",
        "",
        "## Benefits",
        "",
        "1. **Version Control**: All code in git",
        "2. **Reproducibility**: Docker ensures consistent environment",
        "3. **Shareable**: Public or private Space",
        "4. **Persistent**: Re-run anytime without setup",
        "5. **Pro Benefits**: Priority queue, credits, ZeroGPU access"
    ]

    guide = "\n".join(guide_lines)

    return {
        "task": "generate_hf_deployment_guide",
        "status": "success",
        "guide": guide,
        "recommended_gpu": recommended_option["provider"]
    }


async def save_hf_deployment_guide(input_data: Any = None) -> Dict[str, Any]:
    """Save HF Spaces deployment guide to file."""
    if not input_data or "guide" not in input_data:
        guide_data = await generate_hf_deployment_guide()
        guide = guide_data["guide"]
    else:
        guide = input_data["guide"]

    output_file = "docs/HF_SPACES_DEPLOYMENT_GUIDE.md"

    with open(output_file, 'w') as f:
        f.write(guide)

    return {
        "task": "save_hf_deployment_guide",
        "status": "success",
        "file": output_file,
        "size_bytes": len(guide)
    }
