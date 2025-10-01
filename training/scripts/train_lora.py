#!/usr/bin/env python3
"""
LoRA Fine-Tuning Script for Qwen2.5-Coder-7B

Week 9 Phase 3: CPU-based LoRA training on 298 interactions.

Usage:
    python3 train_lora.py --epochs 3 --batch-size 4
"""

import argparse
import json
import torch
from pathlib import Path
from datetime import datetime
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling
)
from peft import LoraConfig, get_peft_model, TaskType
from datasets import load_dataset


def load_training_config():
    """Load LoRA training configuration."""
    return {
        "base_model": "Qwen/Qwen2.5-Coder-7B-Instruct",
        "lora_r": 8,                    # Rank (8 = good balance)
        "lora_alpha": 32,               # Scaling (typically 4×r)
        "lora_dropout": 0.1,            # Regularization
        "target_modules": ["q_proj", "v_proj", "k_proj", "o_proj"],  # Attention layers
        "learning_rate": 2e-4,          # LoRA learning rate (higher than full FT)
        "num_train_epochs": 3,          # Typical for LoRA
        "per_device_train_batch_size": 2,  # Small for CPU
        "gradient_accumulation_steps": 8,   # Effective batch = 2×8 = 16
        "warmup_steps": 50,             # Gradual LR warmup
        "weight_decay": 0.01,           # Regularization
        "max_grad_norm": 1.0,           # Gradient clipping
        "logging_steps": 10,
        "save_steps": 50,
        "eval_steps": 50,
        "save_total_limit": 3,          # Keep only 3 best checkpoints
        "max_length": 2048,             # Context window
    }


def prepare_model_and_tokenizer(config: dict):
    """
    Load base model and apply LoRA adapters.

    Returns: (model, tokenizer, peft_config)
    """
    base_model = config["base_model"]

    print(f"📥 Loading base model: {base_model}")
    print("   This may take several minutes on first run...")

    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(
        base_model,
        trust_remote_code=True,
        padding_side="right"  # Important for training
    )

    # Ensure pad token is set
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # Load model (CPU-only, FP32)
    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        torch_dtype=torch.float32,  # FP32 for CPU
        device_map="cpu",            # CPU-only training
        trust_remote_code=True
    )

    print("✓ Base model loaded")

    # Configure LoRA
    print("\n🔧 Configuring LoRA adapters...")
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=config["lora_r"],
        lora_alpha=config["lora_alpha"],
        lora_dropout=config["lora_dropout"],
        target_modules=config["target_modules"],
        bias="none",
        inference_mode=False
    )

    # Apply LoRA
    model = get_peft_model(model, lora_config)

    # Print trainable parameters
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total_params = sum(p.numel() for p in model.parameters())
    trainable_pct = 100 * trainable_params / total_params

    print(f"✓ LoRA adapters applied")
    print(f"  Trainable params: {trainable_params:,} ({trainable_pct:.2f}%)")
    print(f"  Total params:     {total_params:,}")

    return model, tokenizer, lora_config


def load_and_tokenize_data(data_dir: Path, tokenizer, max_length: int):
    """
    Load training data and tokenize.

    Returns: DatasetDict with train/val splits
    """
    print(f"\n📂 Loading training data from: {data_dir}")

    # Load JSONL files
    dataset = load_dataset(
        "json",
        data_files={
            "train": str(data_dir / "train.jsonl"),
            "validation": str(data_dir / "val.jsonl")
        }
    )

    print(f"✓ Loaded {len(dataset['train'])} training examples")
    print(f"✓ Loaded {len(dataset['validation'])} validation examples")

    # Tokenization function
    def tokenize_function(examples):
        outputs = tokenizer(
            examples["text"],
            truncation=True,
            max_length=max_length,
            padding="max_length",
            return_tensors=None
        )
        # For causal LM, labels = input_ids
        outputs["labels"] = outputs["input_ids"].copy()
        return outputs

    print("\n🔧 Tokenizing dataset...")
    tokenized_dataset = dataset.map(
        tokenize_function,
        batched=True,
        remove_columns=dataset["train"].column_names,
        desc="Tokenizing"
    )

    print("✓ Tokenization complete")

    return tokenized_dataset


def train_lora(
    output_dir: Path,
    data_dir: Path,
    config: dict,
    resume_from_checkpoint: str = None
):
    """
    Main training function.

    Args:
        output_dir: Where to save trained model
        data_dir: Directory with train.jsonl, val.jsonl
        config: Training configuration
        resume_from_checkpoint: Path to checkpoint (optional)
    """
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save config
    config_file = output_dir / "training_config.json"
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    print(f"💾 Training config saved to: {config_file}\n")

    # Load model and tokenizer
    model, tokenizer, lora_config = prepare_model_and_tokenizer(config)

    # Load and tokenize data
    tokenized_dataset = load_and_tokenize_data(data_dir, tokenizer, config["max_length"])

    # Data collator (handles batching)
    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False  # Causal LM (not masked LM)
    )

    # Training arguments
    training_args = TrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=config["num_train_epochs"],
        per_device_train_batch_size=config["per_device_train_batch_size"],
        per_device_eval_batch_size=config["per_device_train_batch_size"],
        gradient_accumulation_steps=config["gradient_accumulation_steps"],
        learning_rate=config["learning_rate"],
        weight_decay=config["weight_decay"],
        max_grad_norm=config["max_grad_norm"],
        warmup_steps=config["warmup_steps"],
        logging_dir=str(output_dir / "logs"),
        logging_steps=config["logging_steps"],
        save_steps=config["save_steps"],
        eval_steps=config["eval_steps"],
        eval_strategy="steps",  # Changed from evaluation_strategy (transformers 4.56+)
        save_strategy="steps",
        save_total_limit=config["save_total_limit"],
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        report_to="none",  # Disable wandb/tensorboard
        fp16=False,        # FP32 for CPU
        dataloader_num_workers=4,  # Parallel data loading
        remove_unused_columns=False
    )

    # Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset["train"],
        eval_dataset=tokenized_dataset["validation"],
        data_collator=data_collator,
    )

    # Print training summary
    print("\n" + "=" * 80)
    print("TRAINING CONFIGURATION")
    print("=" * 80)
    print(f"Base model:          {config['base_model']}")
    print(f"LoRA rank:           {config['lora_r']}")
    print(f"LoRA alpha:          {config['lora_alpha']}")
    print(f"Learning rate:       {config['learning_rate']}")
    print(f"Epochs:              {config['num_train_epochs']}")
    print(f"Batch size:          {config['per_device_train_batch_size']}")
    print(f"Gradient accum:      {config['gradient_accumulation_steps']}")
    print(f"Effective batch:     {config['per_device_train_batch_size'] * config['gradient_accumulation_steps']}")
    print(f"Training examples:   {len(tokenized_dataset['train'])}")
    print(f"Validation examples: {len(tokenized_dataset['validation'])}")
    print(f"Max length:          {config['max_length']} tokens")
    print(f"Output directory:    {output_dir}")
    print("=" * 80)

    # Estimate training time
    steps_per_epoch = len(tokenized_dataset['train']) // (config['per_device_train_batch_size'] * config['gradient_accumulation_steps'])
    total_steps = steps_per_epoch * config['num_train_epochs']
    print(f"\n⏱  Estimated steps: {total_steps} ({steps_per_epoch} per epoch)")
    print(f"   CPU training: expect 12-24 hours for completion\n")

    # Start training
    print("🚀 Starting LoRA training...")
    print(f"   Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    trainer.train(resume_from_checkpoint=resume_from_checkpoint)

    print(f"\n✅ Training complete!")
    print(f"   End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Save final model
    final_model_dir = output_dir / "final_model"
    trainer.save_model(str(final_model_dir))
    tokenizer.save_pretrained(str(final_model_dir))

    print(f"\n💾 Model saved to: {final_model_dir}")
    print("   - adapter_config.json")
    print("   - adapter_model.safetensors")
    print("   - tokenizer files")

    return trainer


def main():
    parser = argparse.ArgumentParser(description="LoRA fine-tuning for Qwen2.5-Coder-7B")
    parser.add_argument("--data-dir", type=str, default="training/data",
                        help="Directory with train/val JSONL files")
    parser.add_argument("--output-dir", type=str, default="training/models/qwen2.5-coder-7b-lora",
                        help="Output directory for trained model")
    parser.add_argument("--epochs", type=int, help="Number of training epochs (overrides config)")
    parser.add_argument("--batch-size", type=int, help="Per-device batch size (overrides config)")
    parser.add_argument("--resume", type=str, help="Resume from checkpoint")

    args = parser.parse_args()

    # Load config
    config = load_training_config()

    # Override config from args
    if args.epochs:
        config["num_train_epochs"] = args.epochs
    if args.batch_size:
        config["per_device_train_batch_size"] = args.batch_size

    # Paths
    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)

    if not data_dir.exists():
        print(f"Error: Data directory not found: {data_dir}")
        return 1

    # Train
    train_lora(
        output_dir=output_dir,
        data_dir=data_dir,
        config=config,
        resume_from_checkpoint=args.resume
    )

    print("\n" + "=" * 80)
    print("NEXT STEPS")
    print("=" * 80)
    print("1. Evaluate on test set:")
    print(f"   python3 training/scripts/evaluate_lora.py --model {output_dir}/final_model")
    print("\n2. Convert to GGUF for llama.cpp:")
    print(f"   python3 training/scripts/convert_to_gguf.py --model {output_dir}/final_model")
    print()

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
