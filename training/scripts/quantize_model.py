#!/usr/bin/env python3
"""
Quantize GGUF Model

Week 9 Phase 4: Quantize f16 GGUF to Q4_K_M for optimal CPU inference.

Usage:
    python3 quantize_model.py --input training/models/qwen3-8b-merged-f16.gguf
"""

import argparse
import subprocess
import sys
from pathlib import Path


# Path to llama.cpp installation
LLAMA_CPP_DIR = Path.home() / "llama.cpp"
QUANTIZE_BIN = LLAMA_CPP_DIR / "llama-quantize"


def quantize_model(
    input_file: str,
    output_file: str,
    quantization_type: str = "Q4_K_M"
):
    """
    Quantize GGUF model.

    Args:
        input_file: Input GGUF file (f16 or f32)
        output_file: Output quantized GGUF file
        quantization_type: Quantization type (Q4_K_M recommended)

    Returns:
        Path to output GGUF file
    """
    input_path = Path(input_file)
    output_path = Path(output_file)

    print("=" * 80)
    print("QUANTIZING GGUF MODEL")
    print("=" * 80)
    print(f"\nInput file:        {input_file}")
    print(f"Output file:       {output_file}")
    print(f"Quantization type: {quantization_type}\n")

    # Verify llama.cpp installation
    if not LLAMA_CPP_DIR.exists():
        print(f"❌ Error: llama.cpp not found at {LLAMA_CPP_DIR}")
        print("   Please install llama.cpp:")
        print("   git clone https://github.com/ggerganov/llama.cpp")
        print("   cd llama.cpp && make")
        return None

    if not QUANTIZE_BIN.exists():
        print(f"❌ Error: Quantize binary not found: {QUANTIZE_BIN}")
        print("   Build llama.cpp first:")
        print("   cd ~/llama.cpp && make")
        return None

    # Verify input file
    if not input_path.exists():
        print(f"❌ Error: Input file not found: {input_path}")
        return None

    input_size_gb = input_path.stat().st_size / (1024 ** 3)
    print(f"📊 Input file size: {input_size_gb:.2f} GB")

    # Create output directory
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Build command
    cmd = [
        str(QUANTIZE_BIN),
        str(input_path),
        str(output_path),
        quantization_type
    ]

    print("\n🔧 Running quantization...")
    print(f"   Command: {' '.join(cmd)}\n")

    # Run quantization
    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=False,  # Show live output
            text=True
        )

        print("\n✅ Quantization complete!")

        # Verify output file
        if output_path.exists():
            output_size_gb = output_path.stat().st_size / (1024 ** 3)
            compression_ratio = (input_size_gb / output_size_gb) if output_size_gb > 0 else 0
            size_reduction_pct = ((input_size_gb - output_size_gb) / input_size_gb) * 100

            print(f"\n📊 Output file: {output_path}")
            print(f"   Input size:      {input_size_gb:.2f} GB")
            print(f"   Output size:     {output_size_gb:.2f} GB")
            print(f"   Compression:     {compression_ratio:.2f}x")
            print(f"   Size reduction:  {size_reduction_pct:.1f}%")
        else:
            print("\n⚠️  Warning: Output file not found (quantization may have failed)")
            return None

        print("\n" + "=" * 80)
        print("✅ QUANTIZATION COMPLETE")
        print("=" * 80)
        print(f"\nQuantized model saved to: {output_path}")
        print("\nNext steps:")
        print("1. Test inference:")
        print(f"   {LLAMA_CPP_DIR}/llama-cli -m {output_path} -p 'Hello'")
        print("2. Run full evaluation:")
        print(f"   python3 training/scripts/evaluate_qwen3.py --model {output_path}")
        print()

        return str(output_path)

    except subprocess.CalledProcessError as e:
        print(f"\n❌ Quantization failed with exit code {e.returncode}")
        return None
    except Exception as e:
        print(f"\n❌ Error during quantization: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Quantize GGUF model")
    parser.add_argument("--input", "-i", type=str, required=True,
                        help="Input GGUF file (f16 or f32)")
    parser.add_argument("--output", "-o", type=str,
                        help="Output GGUF file (default: <input>-q4_k_m.gguf)")
    parser.add_argument("--type", "-t", type=str, default="Q4_K_M",
                        choices=[
                            "Q4_0", "Q4_1", "Q5_0", "Q5_1",
                            "Q8_0", "Q2_K", "Q3_K_S", "Q3_K_M", "Q3_K_L",
                            "Q4_K_S", "Q4_K_M", "Q5_K_S", "Q5_K_M", "Q6_K"
                        ],
                        help="Quantization type (Q4_K_M recommended)")

    args = parser.parse_args()

    # Default output path
    if args.output is None:
        input_path = Path(args.input)
        quant_type_lower = args.type.lower().replace("_", "-")
        args.output = str(input_path.parent / f"{input_path.stem}-{quant_type_lower}.gguf")

    result = quantize_model(
        input_file=args.input,
        output_file=args.output,
        quantization_type=args.type
    )

    return 0 if result else 1


if __name__ == "__main__":
    sys.exit(main())
