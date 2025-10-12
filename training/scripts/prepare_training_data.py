#!/usr/bin/env python3
"""
Prepare training data from collected interactions.

Week 9 Phase 3: Convert 302 interactions to instruction-following format for LoRA.

Format:
    {
        "text": "<|im_start|>system\\nYou are a helpful coding assistant...\\n<|im_end|>\\n<|im_start|>user\\n{task}\\n<|im_end|>\\n<|im_start|>assistant\\n{output}\\n<|im_end|>"
    }
"""

import json
import random
from pathlib import Path
from typing import List, Dict


def load_interactions(jsonl_file: Path) -> List[Dict]:
    """Load collected interactions from JSONL."""
    interactions = []
    with open(jsonl_file, 'r') as f:
        for line in f:
            interactions.append(json.loads(line))
    return interactions


def interaction_to_training_example(interaction: Dict) -> Dict:
    """
    Convert interaction to instruction-following format.

    Qwen2.5 chat template:
    <|im_start|>system
    {system_message}
    <|im_end|>
    <|im_start|>user
    {user_message}
    <|im_end|>
    <|im_start|>assistant
    {assistant_message}
    <|im_end|>
    """
    # Extract components
    task_desc = interaction["task"]["description"]
    agent_role = interaction["agent"]["role"]
    output = interaction["execution"]["output"]

    # System prompt based on agent role
    system_prompts = {
        "coder": "You are an expert software engineer specializing in Clean Architecture and SOLID principles. Write high-quality, well-documented Python code following best practices.",
        "tester": "You are an expert test engineer. Write comprehensive pytest tests with good coverage, clear assertions, and proper fixtures.",
        "reviewer": "You are an expert code reviewer. Analyze code for SOLID violations, security issues, and maintainability problems. Provide constructive feedback.",
        "researcher": "You are an expert technical researcher. Investigate frameworks, compare approaches, and provide evidence-based recommendations.",
        "coordinator": "You are an expert project coordinator. Create clear plans, break down complex tasks, and organize workflows effectively."
    }

    system_message = system_prompts.get(agent_role, system_prompts["coder"])

    # Format as Qwen2.5 chat template
    text = f"""<|im_start|>system
{system_message}
<|im_end|>
<|im_start|>user
{task_desc}
<|im_end|>
<|im_start|>assistant
{output}
<|im_end|>"""

    return {
        "text": text,
        "task_id": interaction["task"]["task_id"],
        "agent": agent_role,
        "status": interaction["execution"]["status"]
    }


def prepare_training_data(
    interactions_file: Path,
    output_dir: Path,
    train_ratio: float = 0.8,
    val_ratio: float = 0.1,
    test_ratio: float = 0.1,
    random_seed: int = 42
):
    """
    Prepare and split training data.

    Args:
        interactions_file: Path to collected interactions JSONL
        output_dir: Directory to save prepared data
        train_ratio: Proportion for training (default: 0.8)
        val_ratio: Proportion for validation (default: 0.1)
        test_ratio: Proportion for test (default: 0.1)
        random_seed: Random seed for reproducibility
    """
    # Load interactions
    print(f"📂 Loading interactions from: {interactions_file}")
    interactions = load_interactions(interactions_file)
    print(f"✓ Loaded {len(interactions)} interactions\n")

    # Filter successful interactions only
    successful = [i for i in interactions if i["execution"]["status"] == "success"]
    print(f"✓ Filtered to {len(successful)} successful interactions\n")

    # Convert to training format
    print("🔧 Converting to instruction-following format...")
    training_examples = []
    for interaction in successful:
        try:
            example = interaction_to_training_example(interaction)
            training_examples.append(example)
        except Exception as e:
            print(f"  ⚠ Skipped interaction {interaction.get('id', 'unknown')}: {e}")

    print(f"✓ Created {len(training_examples)} training examples\n")

    # Shuffle and split
    random.seed(random_seed)
    random.shuffle(training_examples)

    total = len(training_examples)
    train_size = int(total * train_ratio)
    val_size = int(total * val_ratio)

    train_data = training_examples[:train_size]
    val_data = training_examples[train_size:train_size + val_size]
    test_data = training_examples[train_size + val_size:]

    print("📊 Data splits:")
    print(f"  Training:   {len(train_data):3d} ({len(train_data)/total:.1%})")
    print(f"  Validation: {len(val_data):3d} ({len(val_data)/total:.1%})")
    print(f"  Test:       {len(test_data):3d} ({len(test_data)/total:.1%})")
    print()

    # Save to JSONL files
    output_dir.mkdir(parents=True, exist_ok=True)

    def save_jsonl(data: List[Dict], filename: str):
        filepath = output_dir / filename
        with open(filepath, 'w') as f:
            for example in data:
                f.write(json.dumps(example) + "\n")
        print(f"✓ Saved {len(data):3d} examples to: {filepath}")

    save_jsonl(train_data, "train.jsonl")
    save_jsonl(val_data, "val.jsonl")
    save_jsonl(test_data, "test.jsonl")

    # Save metadata
    metadata = {
        "total_interactions": len(interactions),
        "successful_interactions": len(successful),
        "training_examples": len(training_examples),
        "splits": {
            "train": len(train_data),
            "val": len(val_data),
            "test": len(test_data)
        },
        "agent_distribution": {
            agent: len([e for e in training_examples if e["agent"] == agent])
            for agent in ["coder", "tester", "reviewer", "researcher", "coordinator"]
        },
        "random_seed": random_seed
    }

    metadata_file = output_dir / "metadata.json"
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)

    print(f"\n✓ Saved metadata to: {metadata_file}")

    print("\n" + "=" * 80)
    print("DATA PREPARATION COMPLETE ✅")
    print("=" * 80)
    print(f"\n📁 Training data ready at: {output_dir}/")
    print(f"  - train.jsonl ({len(train_data)} examples)")
    print(f"  - val.jsonl ({len(val_data)} examples)")
    print(f"  - test.jsonl ({len(test_data)} examples)")
    print()


def main():
    # Paths
    interactions_file = Path(__file__).parent.parent.parent / "data" / "training" / "interactions_20251001.jsonl"
    output_dir = Path(__file__).parent.parent / "data"

    if not interactions_file.exists():
        print(f"Error: Interactions file not found: {interactions_file}")
        return 1

    # Prepare data
    prepare_training_data(
        interactions_file=interactions_file,
        output_dir=output_dir,
        train_ratio=0.8,
        val_ratio=0.1,
        test_ratio=0.1,
        random_seed=42
    )

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
