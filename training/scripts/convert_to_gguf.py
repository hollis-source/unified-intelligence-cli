#!/usr/bin/env python3
"""
Convert HuggingFace Model to GGUF Format

Week 9 Phase 4: Convert merged model to GGUF for llama.cpp inference.

Usage:
    python3 convert_to_gguf.py --model training/models/qwen3-8b-merged
"""

import argparse
import subprocess
import sys
from pathlib import Path


# Path to llama.cpp installation
LLAMA_CPP_DIR = Path.home() / "llama.cpp"
CONVERT_SCRIPT = LLAMA_CPP_DIR / "convert_hf_to_gguf.py"


def convert_to_gguf(
    model_dir: str,
    output_file: str,
    outtype: str = "f16"
):
    """
    Convert HuggingFace model to GGUF format.

    Args:
        model_dir: Path to HuggingFace model directory
        output_file: Output GGUF file path
        outtype: Output type (f32, f16, q8_0, etc.)

    Returns:
        Path to output GGUF file
    """
    model_path = Path(model_dir)
    output_path = Path(output_file)

    print("=" * 80)
    print("CONVERTING TO GGUF FORMAT")
    print("=" * 80)
    print(f"\nInput model:  {model_dir}")
    print(f"Output file:  {output_file}")
    print(f"Output type:  {outtype}\n")

    # Verify llama.cpp installation
    if not LLAMA_CPP_DIR.exists():
        print(f"❌ Error: llama.cpp not found at {LLAMA_CPP_DIR}")
        print("   Please install llama.cpp:")
        print("   git clone https://github.com/ggerganov/llama.cpp")
        return None

    if not CONVERT_SCRIPT.exists():
        print(f"❌ Error: Convert script not found: {CONVERT_SCRIPT}")
        return None

    # Verify model directory
    if not model_path.exists():
        print(f"❌ Error: Model directory not found: {model_path}")
        return None

    # Check for required model files
    required_files = ["config.json"]
    missing_files = [f for f in required_files if not (model_path / f).exists()]
    if missing_files:
        print(f"❌ Error: Missing required files: {missing_files}")
        return None

    # Create output directory
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Build command
    cmd = [
        sys.executable,  # Use same Python interpreter
        str(CONVERT_SCRIPT),
        str(model_path),
        "--outfile", str(output_path),
        "--outtype", outtype
    ]

    print("🔧 Running conversion...")
    print(f"   Command: {' '.join(cmd)}\n")

    # Run conversion
    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=False,  # Show live output
            text=True
        )

        print("\n✅ Conversion complete!")

        # Verify output file
        if output_path.exists():
            size_gb = output_path.stat().st_size / (1024 ** 3)
            print(f"\n📊 Output file: {output_path}")
            print(f"   Size: {size_gb:.2f} GB")
        else:
            print("\n⚠️  Warning: Output file not found (conversion may have failed)")
            return None

        print("\n" + "=" * 80)
        print("✅ CONVERSION COMPLETE")
        print("=" * 80)
        print(f"\nGGUF file saved to: {output_path}")
        print("\nNext steps:")
        print("1. Quantize to Q4_K_M:")
        print(f"   python3 training/scripts/quantize_model.py --input {output_path}")
        print("2. Or test inference:")
        print(f"   {LLAMA_CPP_DIR}/llama-cli -m {output_path} -p 'Hello'")
        print()

        return str(output_path)

    except subprocess.CalledProcessError as e:
        print(f"\n❌ Conversion failed with exit code {e.returncode}")
        return None
    except Exception as e:
        print(f"\n❌ Error during conversion: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Convert HuggingFace model to GGUF")
    parser.add_argument("--model", type=str, required=True,
                        help="Path to HuggingFace model directory (merged model)")
    parser.add_argument("--output", type=str,
                        help="Output GGUF file path (default: <model>-f16.gguf)")
    parser.add_argument("--outtype", type=str, default="f16",
                        choices=["f32", "f16", "q8_0"],
                        help="Output type (f16 recommended before quantization)")

    args = parser.parse_args()

    # Default output path
    if args.output is None:
        model_name = Path(args.model).name
        args.output = f"training/models/{model_name}-{args.outtype}.gguf"

    result = convert_to_gguf(
        model_dir=args.model,
        output_file=args.output,
        outtype=args.outtype
    )

    return 0 if result else 1


if __name__ == "__main__":
    sys.exit(main())
