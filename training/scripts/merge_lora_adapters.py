#!/usr/bin/env python3
"""
Merge LoRA Adapters into Base Model

Week 9 Phase 4: Merge fine-tuned LoRA adapters with base model.
This is required before GGUF conversion (per Grok recommendations).

Usage:
    python3 merge_lora_adapters.py --lora training/models/qwen3-8b-instruct-lora/final_model
"""

import argparse
import torch
from pathlib import Path
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel


def merge_lora(
    base_model_name: str,
    lora_checkpoint: str,
    output_dir: str
):
    """
    Merge LoRA adapters into base model.

    Args:
        base_model_name: Base model name (e.g., "Qwen/Qwen3-8B")
        lora_checkpoint: Path to LoRA checkpoint directory
        output_dir: Where to save merged model

    Returns:
        Path to merged model
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("MERGING LORA ADAPTERS")
    print("=" * 80)
    print(f"\nBase model:      {base_model_name}")
    print(f"LoRA checkpoint: {lora_checkpoint}")
    print(f"Output dir:      {output_dir}\n")

    # Step 1: Load base model
    print("📥 Step 1/4: Loading base model...")
    base_model = AutoModelForCausalLM.from_pretrained(
        base_model_name,
        torch_dtype=torch.float32,
        device_map="cpu",
        trust_remote_code=True
    )
    print("✓ Base model loaded")

    # Step 2: Load LoRA adapters
    print("\n📥 Step 2/4: Loading LoRA adapters...")
    model = PeftModel.from_pretrained(base_model, lora_checkpoint)
    print("✓ LoRA adapters loaded")

    # Print trainable parameters info
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total_params = sum(p.numel() for p in model.parameters())
    print(f"   Trainable params: {trainable_params:,} ({100*trainable_params/total_params:.2f}%)")
    print(f"   Total params:     {total_params:,}")

    # Step 3: Merge adapters
    print("\n🔧 Step 3/4: Merging adapters into base model...")
    print("   This creates a single fused model (no adapter overhead)")
    merged_model = model.merge_and_unload()
    print("✓ Merge complete")

    # Step 4: Save merged model
    print(f"\n💾 Step 4/4: Saving merged model to {output_dir}...")
    merged_model.save_pretrained(output_dir)
    print("✓ Model saved")

    # Save tokenizer
    print("\n💾 Saving tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(
        base_model_name,
        trust_remote_code=True
    )
    tokenizer.save_pretrained(output_dir)
    print("✓ Tokenizer saved")

    # Verify files
    print("\n📂 Output files:")
    for file in sorted(output_path.glob("*")):
        size_mb = file.stat().st_size / (1024 * 1024) if file.is_file() else 0
        print(f"   - {file.name:40s} ({size_mb:8.2f} MB)")

    print("\n" + "=" * 80)
    print("✅ MERGE COMPLETE")
    print("=" * 80)
    print(f"\nMerged model saved to: {output_dir}")
    print("\nNext steps:")
    print("1. Convert to GGUF:")
    print(f"   python3 training/scripts/convert_to_gguf.py --model {output_dir}")
    print("2. Or evaluate directly:")
    print(f"   python3 training/scripts/evaluate_qwen3.py --model {output_dir} --merged")
    print()

    return output_dir


def main():
    parser = argparse.ArgumentParser(description="Merge LoRA adapters into base model")
    parser.add_argument("--lora", type=str, required=True,
                        help="Path to LoRA checkpoint directory")
    parser.add_argument("--base", type=str, default="Qwen/Qwen3-8B",
                        help="Base model name or path")
    parser.add_argument("--output", type=str, default="training/models/qwen3-8b-merged",
                        help="Output directory for merged model")

    args = parser.parse_args()

    lora_path = Path(args.lora)
    if not lora_path.exists():
        print(f"Error: LoRA checkpoint not found: {lora_path}")
        return 1

    try:
        merge_lora(
            base_model_name=args.base,
            lora_checkpoint=str(lora_path),
            output_dir=args.output
        )
        return 0
    except Exception as e:
        print(f"\n❌ Error during merge: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
