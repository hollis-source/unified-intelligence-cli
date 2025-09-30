#!/usr/bin/env python3
"""
Architecture Review Script - Consult Grok on Clean Architecture compliance.
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.grok_session import GrokSession


def main():
    """Conduct architecture review with Grok."""

    # Read current implementation files
    coordinator_code = Path("src/use_cases/coordinator.py").read_text()
    main_code = Path("src/main.py").read_text()
    interfaces_code = Path("src/interfaces/agent_executor.py").read_text()
    composition_code = Path("src/composition.py").read_text()

    # Prepare consultation prompt
    prompt = f"""# Architecture Review Request

I need you to critically review our Clean Architecture implementation against Robert C. Martin's principles.

## The Critique We Received

Someone claimed our implementation has these violations:

1. **SRP Violation**: `CoordinateAgentsUseCase` mixes orchestration with execution; should split into `TaskDistributorUseCase` (planning) and `AgentRunnerUseCase` (execution).

2. **DIP Issue**: Concrete adapters referenced in main.py - should inject via abstractions only.

3. **ISP Weakness**: Interfaces too broad - need further segregation.

4. **Clean Code Gap**: Functions exceed 20 lines - should refactor.

## Our Current Implementation

### CoordinateAgentsUseCase (src/use_cases/coordinator.py)
```python
{coordinator_code}
```

### Main Entry Point (src/main.py)
```python
{main_code}
```

### Interfaces (src/interfaces/agent_executor.py)
```python
{interfaces_code}
```

### Composition Root (src/composition.py)
```python
{composition_code}
```

## My Counter-Analysis

1. **SRP**: The coordinator DOES have one responsibility: "coordinate multi-agent execution with planning." It delegates actual execution to injected `IAgentExecutor`. Planning and coordination are cohesive. Splitting would create artificial separation.

2. **DIP**: We use factories that return interfaces. No concrete adapters in main.py. The critique appears false.

3. **ISP**: Each interface has a single focused method. Already properly segregated.

4. **Clean Code**: Some methods exceed 20 lines, but they're cohesive algorithms (e.g., topological sort for parallel groups).

## Questions for You

**Be critical and data-based. Challenge my assumptions if wrong.**

1. Is the SRP critique valid? Does CoordinateAgentsUseCase violate single responsibility by combining planning + coordination? Should we split it?

2. Does our DIP implementation properly use abstractions, or is there a concrete dependency leak I'm missing?

3. Are our interfaces properly segregated per ISP, or should they be split further?

4. Is the 20-line rule dogmatic, or should we strictly enforce it even for cohesive algorithms?

5. What real improvements (backed by data/evidence) would you recommend?

**Provide specific recommendations with rationale based on Martin's actual writings and industry data (e.g., CrewAI patterns, production practices).**
"""

    # Start Grok session
    session = GrokSession()

    print("=" * 80)
    print("CONSULTING GROK ON ARCHITECTURE REVIEW")
    print("=" * 80)
    print()

    # Send consultation
    response = session.send_message(prompt)

    print(response)
    print()
    print("=" * 80)

    # Save review to file
    output_path = Path("docs/architecture_review_grok.md")
    with open(output_path, "w") as f:
        f.write("# Architecture Review by Grok\n\n")
        f.write("## Consultation Prompt\n\n")
        f.write(prompt)
        f.write("\n\n## Grok's Response\n\n")
        f.write(response)

    print(f"Review saved to: {output_path}")


if __name__ == "__main__":
    main()