#!/usr/bin/env python3
"""
Post-Training Pipeline for Qwen3-8B LoRA

Week 9 Phase 4: Automated pipeline from LoRA checkpoint to deployable GGUF.

Steps:
    1. Merge LoRA adapters into base model
    2. Convert merged model to GGUF (f16)
    3. Quantize to Q4_K_M
    4. Evaluate on test set
    5. Generate deployment recommendation

Usage:
    python3 post_training_pipeline.py --lora training/models/qwen3-8b-instruct-lora/final_model

    # Skip steps if already completed:
    python3 post_training_pipeline.py --lora ... --skip-merge --skip-convert
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional


# Import individual pipeline scripts
sys.path.insert(0, str(Path(__file__).parent))
from merge_lora_adapters import merge_lora
from convert_to_gguf import convert_to_gguf
from quantize_model import quantize_model


def print_section(title: str):
    """Print section header."""
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def print_checkpoint(step: int, total: int, description: str, status: str = "START"):
    """Print checkpoint marker."""
    icon = "🚀" if status == "START" else "✅" if status == "DONE" else "❌"
    print(f"\n{icon} [{step}/{total}] {description}")


def run_pipeline(
    lora_checkpoint: str,
    base_model: str = "Qwen/Qwen3-8B",
    output_dir: str = "training/models",
    test_data: str = "training/data/test.jsonl",
    skip_merge: bool = False,
    skip_convert: bool = False,
    skip_quantize: bool = False,
    skip_eval: bool = False
) -> dict:
    """
    Run complete post-training pipeline.

    Returns:
        Dictionary with pipeline results and recommendation
    """
    start_time = time.time()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Paths for pipeline artifacts
    merged_dir = output_dir / "qwen3-8b-merged"
    gguf_f16 = output_dir / "qwen3-8b-merged-f16.gguf"
    gguf_q4 = output_dir / "qwen3-8b-merged-q4-k-m.gguf"
    results_file = Path("training/evaluation_results.json")

    print_section("POST-TRAINING PIPELINE")
    print(f"\nLoRA checkpoint:  {lora_checkpoint}")
    print(f"Base model:       {base_model}")
    print(f"Output directory: {output_dir}")
    print(f"Test data:        {test_data}\n")

    pipeline_results = {
        "lora_checkpoint": str(lora_checkpoint),
        "base_model": base_model,
        "steps": {},
        "start_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "recommendation": None
    }

    # Step 1: Merge LoRA adapters
    print_checkpoint(1, 4, "Merge LoRA adapters into base model", "START")
    if skip_merge and merged_dir.exists():
        print(f"⏭️  Skipping merge (using existing: {merged_dir})")
        pipeline_results["steps"]["merge"] = {"status": "skipped", "path": str(merged_dir)}
    else:
        try:
            merge_result = merge_lora(
                base_model_name=base_model,
                lora_checkpoint=lora_checkpoint,
                output_dir=str(merged_dir)
            )
            pipeline_results["steps"]["merge"] = {"status": "success", "path": merge_result}
            print_checkpoint(1, 4, "Merge complete", "DONE")
        except Exception as e:
            print(f"\n❌ Step 1 FAILED: {e}")
            pipeline_results["steps"]["merge"] = {"status": "failed", "error": str(e)}
            return pipeline_results

    # Step 2: Convert to GGUF (f16)
    print_checkpoint(2, 4, "Convert merged model to GGUF (f16)", "START")
    if skip_convert and gguf_f16.exists():
        print(f"⏭️  Skipping conversion (using existing: {gguf_f16})")
        pipeline_results["steps"]["convert"] = {"status": "skipped", "path": str(gguf_f16)}
    else:
        try:
            convert_result = convert_to_gguf(
                model_dir=str(merged_dir),
                output_file=str(gguf_f16),
                outtype="f16"
            )
            if not convert_result:
                raise Exception("Conversion returned None (failed)")
            pipeline_results["steps"]["convert"] = {"status": "success", "path": convert_result}
            print_checkpoint(2, 4, "Conversion complete", "DONE")
        except Exception as e:
            print(f"\n❌ Step 2 FAILED: {e}")
            pipeline_results["steps"]["convert"] = {"status": "failed", "error": str(e)}
            return pipeline_results

    # Step 3: Quantize to Q4_K_M
    print_checkpoint(3, 4, "Quantize to Q4_K_M", "START")
    if skip_quantize and gguf_q4.exists():
        print(f"⏭️  Skipping quantization (using existing: {gguf_q4})")
        pipeline_results["steps"]["quantize"] = {"status": "skipped", "path": str(gguf_q4)}
    else:
        try:
            quantize_result = quantize_model(
                input_file=str(gguf_f16),
                output_file=str(gguf_q4),
                quantization_type="Q4_K_M"
            )
            if not quantize_result:
                raise Exception("Quantization returned None (failed)")
            pipeline_results["steps"]["quantize"] = {"status": "success", "path": quantize_result}
            print_checkpoint(3, 4, "Quantization complete", "DONE")
        except Exception as e:
            print(f"\n❌ Step 3 FAILED: {e}")
            pipeline_results["steps"]["quantize"] = {"status": "failed", "error": str(e)}
            return pipeline_results

    # Step 4: Evaluate on test set
    print_checkpoint(4, 4, "Evaluate on test set", "START")
    if skip_eval:
        print("⏭️  Skipping evaluation (as requested)")
        pipeline_results["steps"]["evaluate"] = {"status": "skipped"}
    else:
        try:
            # Run evaluation script (merged model, not GGUF - HF inference)
            eval_cmd = [
                sys.executable,
                str(Path(__file__).parent / "evaluate_qwen3.py"),
                "--model", str(merged_dir),
                "--test-data", test_data,
                "--merged",
                "--output", str(results_file)
            ]

            print(f"   Command: {' '.join(eval_cmd)}\n")
            result = subprocess.run(eval_cmd, check=False, capture_output=False)

            if result.returncode == 0:
                # Load results
                with open(results_file, 'r') as f:
                    eval_results = json.load(f)

                pipeline_results["steps"]["evaluate"] = {
                    "status": "success",
                    "results": eval_results,
                    "passed": True
                }
                print_checkpoint(4, 4, "Evaluation complete - PASS", "DONE")
            else:
                # Evaluation ran but failed targets
                with open(results_file, 'r') as f:
                    eval_results = json.load(f)

                pipeline_results["steps"]["evaluate"] = {
                    "status": "completed_with_failures",
                    "results": eval_results,
                    "passed": False
                }
                print_checkpoint(4, 4, "Evaluation complete - FAIL", "DONE")

        except Exception as e:
            print(f"\n❌ Step 4 FAILED: {e}")
            pipeline_results["steps"]["evaluate"] = {"status": "failed", "error": str(e)}
            return pipeline_results

    # Final summary
    elapsed_time = time.time() - start_time
    pipeline_results["end_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    pipeline_results["elapsed_minutes"] = elapsed_time / 60

    print_section("PIPELINE COMPLETE")
    print(f"\n⏱️  Total time: {elapsed_time / 60:.1f} minutes")
    print(f"\n📦 Artifacts:")
    print(f"   Merged model:  {merged_dir}")
    print(f"   GGUF (f16):    {gguf_f16} ({gguf_f16.stat().st_size / (1024**3):.2f} GB)")
    print(f"   GGUF (Q4_K_M): {gguf_q4} ({gguf_q4.stat().st_size / (1024**3):.2f} GB)")

    if not skip_eval and "evaluate" in pipeline_results["steps"]:
        eval_data = pipeline_results["steps"]["evaluate"]
        if eval_data["status"] in ["success", "completed_with_failures"]:
            metrics = eval_data["results"]["evaluation_metrics"]
            comparison = eval_data["results"]["baseline_comparison"]

            print(f"\n📊 Evaluation Results:")
            print(f"   Success Rate:  {metrics['success_rate']:.1f}% (target: ≥98%)")
            print(f"   Avg Latency:   {metrics['avg_latency']:.1f}s (target: <12s)")

            print(f"\n📈 vs Baseline:")
            print(f"   Success Delta: {comparison['success_delta']:+.1f}%")
            print(f"   Latency Delta: {comparison['latency_delta']:+.1f}s")
            print(f"   Speed Improvement: {comparison['latency_improvement_pct']:+.1f}%")

            # Recommendation
            if comparison["overall_pass"]:
                recommendation = "✅ DEPLOY: Model meets both success and latency targets"
            elif comparison["meets_success_target"]:
                recommendation = "⚠️  ITERATE: Quality good, latency needs improvement"
            elif comparison["meets_latency_target"]:
                recommendation = "⚠️  ITERATE: Speed good, quality needs improvement"
            else:
                recommendation = "❌ ABORT: Neither target met"

            pipeline_results["recommendation"] = recommendation
            print(f"\n💡 Recommendation: {recommendation}")

    print("\n" + "=" * 80)

    # Save pipeline results
    pipeline_file = Path("training/pipeline_results.json")
    with open(pipeline_file, 'w') as f:
        json.dump(pipeline_results, f, indent=2)
    print(f"\n💾 Pipeline results saved to: {pipeline_file}")

    return pipeline_results


def main():
    parser = argparse.ArgumentParser(
        description="Post-training pipeline: LoRA → GGUF → Evaluation"
    )
    parser.add_argument("--lora", type=str, required=True,
                        help="Path to LoRA checkpoint directory")
    parser.add_argument("--base", type=str, default="Qwen/Qwen3-8B",
                        help="Base model name or path")
    parser.add_argument("--output", type=str, default="training/models",
                        help="Output directory for artifacts")
    parser.add_argument("--test-data", type=str, default="training/data/test.jsonl",
                        help="Test data JSONL file")
    parser.add_argument("--skip-merge", action="store_true",
                        help="Skip merge step (use existing merged model)")
    parser.add_argument("--skip-convert", action="store_true",
                        help="Skip GGUF conversion (use existing f16 GGUF)")
    parser.add_argument("--skip-quantize", action="store_true",
                        help="Skip quantization (use existing Q4_K_M GGUF)")
    parser.add_argument("--skip-eval", action="store_true",
                        help="Skip evaluation step")

    args = parser.parse_args()

    lora_path = Path(args.lora)
    if not lora_path.exists():
        print(f"Error: LoRA checkpoint not found: {lora_path}")
        return 1

    try:
        results = run_pipeline(
            lora_checkpoint=str(lora_path),
            base_model=args.base,
            output_dir=args.output,
            test_data=args.test_data,
            skip_merge=args.skip_merge,
            skip_convert=args.skip_convert,
            skip_quantize=args.skip_quantize,
            skip_eval=args.skip_eval
        )

        # Exit code: 0 if deploy, 1 if iterate/abort
        if results.get("recommendation", "").startswith("✅"):
            return 0
        else:
            return 1

    except Exception as e:
        print(f"\n❌ Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
