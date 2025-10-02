# CT DSL: Clean Architecture Design

**Date**: 2025-10-02
**Status**: Implementation Starting
**Approach**: TDD + Clean Architecture + Clean Agile

---

## Clean Architecture Layers

### Layer 1: Entities (Innermost - No Dependencies)

**Purpose**: Core business objects representing AST nodes

**Location**: `src/dsl/entities/`

**Components**:
```
src/dsl/entities/
├── __init__.py
├── ast_node.py          # Base AST node (abstract)
├── composition.py       # Composition node (f ∘ g)
├── monad.py             # Monadic bind (f >>= g)
├── functor.py           # Functor application (fmap)
├── product.py           # Product (f × g) - parallel
├── natural_trans.py     # Natural transformation
└── literal.py           # Literals (identifiers, strings)
```

**Design Principles**:
- ✅ **SRP**: Each entity represents one AST node type
- ✅ **Immutable**: Data classes with frozen=True
- ✅ **No external dependencies**: Pure Python dataclasses
- ✅ **Self-contained**: Business logic in entities

**Example**:
```python
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class ASTNode:
    """Base AST node (abstract entity)."""
    pass

@dataclass(frozen=True)
class Composition(ASTNode):
    """Sequential composition: f ∘ g"""
    left: ASTNode   # f
    right: ASTNode  # g

    def __repr__(self) -> str:
        return f"({self.left} ∘ {self.right})"
```

---

### Layer 2: Use Cases (Business Logic)

**Purpose**: DSL interpretation and compilation logic

**Location**: `src/dsl/use_cases/`

**Components**:
```
src/dsl/use_cases/
├── __init__.py
├── interpret_program.py     # Main interpreter use case
├── compile_to_tasks.py      # AST → Task graph compiler
├── optimize_graph.py        # Fusion optimization use case
└── validate_semantics.py    # Type checking, validation
```

**Design Principles**:
- ✅ **SRP**: Each use case handles one business operation
- ✅ **DIP**: Depends on interfaces (IParser, ITaskFactory)
- ✅ **Orchestration**: Coordinates entities, no framework dependencies

**Example**:
```python
class InterpretProgramUseCase:
    """
    Interpret CT DSL program to execution results.

    Use case orchestrates: parse → validate → compile → execute
    """
    def __init__(
        self,
        parser: IParser,
        validator: ISemanticValidator,
        compiler: ITaskCompiler,
        coordinator: IAgentCoordinator
    ):
        self.parser = parser
        self.validator = validator
        self.compiler = compiler
        self.coordinator = coordinator

    async def execute(self, program: str) -> List[ExecutionResult]:
        """Execute DSL program."""
        # Parse (adapter)
        ast = self.parser.parse(program)

        # Validate (use case)
        self.validator.validate(ast)

        # Compile (use case)
        tasks = self.compiler.compile(ast)

        # Execute (existing use case)
        return await self.coordinator.coordinate(tasks)
```

---

### Layer 3: Interfaces (Abstractions)

**Purpose**: Define contracts for adapters

**Location**: `src/dsl/interfaces/`

**Components**:
```
src/dsl/interfaces/
├── __init__.py
├── i_parser.py              # Parser abstraction
├── i_semantic_validator.py  # Validation abstraction
├── i_task_compiler.py       # Compiler abstraction
└── i_optimizer.py           # Optimization abstraction
```

**Design Principles**:
- ✅ **ISP**: Small, focused interfaces
- ✅ **DIP**: Abstractions, not concretions
- ✅ **LSP**: Substitutable implementations

**Example**:
```python
from abc import ABC, abstractmethod
from src.dsl.entities.ast_node import ASTNode

class IParser(ABC):
    """Parser interface (DIP)."""

    @abstractmethod
    def parse(self, program: str) -> ASTNode:
        """Parse DSL program into AST."""
        pass

class ISemanticValidator(ABC):
    """Semantic validation interface."""

    @abstractmethod
    def validate(self, ast: ASTNode) -> None:
        """Validate AST semantics. Raises ValidationError."""
        pass
```

---

### Layer 4: Adapters (External Integrations)

**Purpose**: Concrete implementations of interfaces

**Location**: `src/dsl/adapters/`

**Components**:
```
src/dsl/adapters/
├── __init__.py
├── lark_parser.py           # Lark-based parser (IParser)
├── type_checker.py          # Type checking validator
├── task_compiler.py         # AST → Task compiler
├── fusion_optimizer.py      # Fusion optimization
└── cli/
    └── dsl_cli.py           # CLI integration
```

**Design Principles**:
- ✅ **OCP**: Extend via new adapters, don't modify interfaces
- ✅ **DIP**: Implement interfaces, inject dependencies
- ✅ **Adapter pattern**: Wrap external libs (lark-parser)

**Example**:
```python
from lark import Lark, Transformer
from src.dsl.interfaces.i_parser import IParser
from src.dsl.entities.ast_node import ASTNode

class LarkParser(IParser):
    """
    Lark-based parser adapter.

    Wraps lark-parser library, implements IParser interface.
    """
    def __init__(self, grammar: str):
        self.lark = Lark(grammar, start='program')
        self.transformer = ASTTransformer()

    def parse(self, program: str) -> ASTNode:
        """Parse using Lark, transform to AST entities."""
        tree = self.lark.parse(program)
        return self.transformer.transform(tree)

class ASTTransformer(Transformer):
    """Transform Lark parse tree to AST entities."""
    def composition(self, children):
        left, right = children
        return Composition(left, right)
    # ... more transformations
```

---

## Directory Structure

```
src/dsl/                          # NEW DSL module
├── __init__.py
├── entities/                     # Layer 1: Pure business objects
│   ├── __init__.py
│   ├── ast_node.py              # Base
│   ├── composition.py
│   ├── monad.py
│   ├── functor.py
│   ├── product.py
│   ├── natural_trans.py
│   └── literal.py
├── use_cases/                    # Layer 2: Business logic
│   ├── __init__.py
│   ├── interpret_program.py
│   ├── compile_to_tasks.py
│   ├── optimize_graph.py
│   └── validate_semantics.py
├── interfaces/                   # Layer 3: Abstractions
│   ├── __init__.py
│   ├── i_parser.py
│   ├── i_semantic_validator.py
│   ├── i_task_compiler.py
│   └── i_optimizer.py
├── adapters/                     # Layer 4: External integrations
│   ├── __init__.py
│   ├── lark_parser.py
│   ├── type_checker.py
│   ├── task_compiler.py
│   ├── fusion_optimizer.py
│   └── cli/
│       └── dsl_cli.py
└── grammar/                      # DSL grammar files
    └── ct_dsl.lark

tests/dsl/                        # TDD tests mirror structure
├── entities/
│   ├── test_composition.py
│   ├── test_monad.py
│   └── ...
├── use_cases/
│   ├── test_interpret_program.py
│   └── ...
├── adapters/
│   ├── test_lark_parser.py
│   └── ...
└── integration/
    └── test_end_to_end.py
```

---

## SOLID Principles Application

### Single Responsibility Principle (SRP)

**Entities**: Each AST node represents one concept
- `Composition`: Only sequential composition
- `Monad`: Only monadic bind
- `Product`: Only parallel execution

**Use Cases**: Each handles one business operation
- `InterpretProgramUseCase`: Program execution only
- `CompileToTasksUseCase`: AST → Tasks only
- `OptimizeGraphUseCase`: Optimization only

### Open-Closed Principle (OCP)

**Extensibility without modification**:
- New AST nodes: Extend `ASTNode`, don't modify parser
- New optimizations: Implement `IOptimizer`, don't modify use case
- New parsers: Implement `IParser`, don't modify interpreter

**Example**: Adding new operator (coproduct `+`)
```python
# 1. New entity (extend, don't modify)
@dataclass(frozen=True)
class Coproduct(ASTNode):
    """Sum type: f + g"""
    left: ASTNode
    right: ASTNode

# 2. Extend grammar (new rule, don't modify existing)
# In ct_dsl.lark: operator ::= "∘" | ">>=" | "×" | "+"

# 3. Extend transformer (new method, don't modify existing)
class ASTTransformer(Transformer):
    def coproduct(self, children):
        return Coproduct(children[0], children[1])
```

### Liskov Substitution Principle (LSP)

**All IParser implementations substitutable**:
```python
# Can swap parser without breaking interpreter
parser1 = LarkParser(grammar)
parser2 = PEGParser(grammar)  # Future: alternative parser

interpreter = InterpretProgramUseCase(
    parser=parser1,  # Or parser2 - both work
    validator=...,
    compiler=...,
    coordinator=...
)
```

### Interface Segregation Principle (ISP)

**Small, focused interfaces** (not god interfaces):
- `IParser`: Only `parse(program) -> AST`
- `ISemanticValidator`: Only `validate(ast) -> None`
- `ITaskCompiler`: Only `compile(ast) -> List[Task]`
- `IOptimizer`: Only `optimize(ast) -> AST`

Not one big `IDSLEngine` with all methods.

### Dependency Inversion Principle (DIP)

**Depend on abstractions**:
```python
# Use case depends on IParser (abstraction)
class InterpretProgramUseCase:
    def __init__(self, parser: IParser):  # Not LarkParser
        self.parser = parser

# Composition root injects concrete implementation
parser = LarkParser(grammar)  # Concrete
interpreter = InterpretProgramUseCase(parser)  # Injected
```

---

## TDD Cycle

### Red → Green → Refactor

**Phase 1: Entities (TDD)**
1. **Red**: Write failing test for `Composition`
2. **Green**: Implement minimal `Composition` to pass
3. **Refactor**: Apply SOLID, clean up

**Phase 2: Parser (TDD)**
1. **Red**: Write failing test for parsing `f ∘ g`
2. **Green**: Implement minimal parser to pass
3. **Refactor**: Extract grammar, improve error handling

**Phase 3: Compiler (TDD)**
1. **Red**: Write failing test for AST → Task compilation
2. **Green**: Implement minimal compiler to pass
3. **Refactor**: Optimize, apply patterns

---

## Clean Agile Practices

### Small, Frequent Commits

**Commit after each TDD cycle** (~30-60 min intervals):
```
Commit 1: Add Composition entity with tests
Commit 2: Add Monad entity with tests
Commit 3: Add Functor entity with tests
Commit 4: Add parser interface
Commit 5: Implement Lark parser for composition
...
```

### Descriptive Commit Messages

**Format**:
```
Category: Brief summary

Detailed explanation of what and why, not how.

Benefits:
- Benefit 1
- Benefit 2
```

**Example**:
```
DSL: Add Composition entity with TDD tests

Implement sequential composition AST node (f ∘ g) following
Clean Architecture. Entity layer, no dependencies.

Benefits:
- Enables basic task chaining in CT DSL
- TDD ensures correctness from start
- Immutable dataclass prevents bugs
```

### Incremental Development

**Phase 1** (Week 1): Entities + Parser
- Day 1-2: Entities (Composition, Monad, Functor)
- Day 3-4: Parser (grammar + Lark adapter)
- Day 5: Integration tests

**Phase 2** (Week 2): Compiler + Interpreter
- Day 1-2: Compiler (AST → Tasks)
- Day 3-4: Interpreter use case
- Day 5: End-to-end tests

**Phase 3** (Week 3): Optimization + CLI
- Day 1-2: Fusion optimizer
- Day 3-4: CLI integration
- Day 5: Documentation + benchmarks

---

## CI/CD Integration

### Automated Testing

**On every commit**:
```yaml
# .github/workflows/dsl-tests.yml
name: DSL Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt  # lark-parser, pytest
      - name: Run DSL tests
        run: |
          pytest tests/dsl/ --cov=src/dsl --cov-report=term-missing
      - name: Type checking
        run: |
          mypy src/dsl/
```

### Code Quality Gates

**Must pass before merge**:
- ✅ All tests pass (100% for new code)
- ✅ Coverage ≥ 85% (existing standard)
- ✅ Type hints pass mypy
- ✅ Linting passes (flake8, black)

---

## Example: TDD Workflow for Composition Entity

### Step 1: Red (Failing Test)

```python
# tests/dsl/entities/test_composition.py
import pytest
from src.dsl.entities.composition import Composition
from src.dsl.entities.literal import Identifier

def test_composition_creation():
    """Test Composition entity creation."""
    # Arrange
    left = Identifier("task_a")
    right = Identifier("task_b")

    # Act
    comp = Composition(left, right)

    # Assert
    assert comp.left == left
    assert comp.right == right

def test_composition_immutable():
    """Test Composition is immutable (frozen dataclass)."""
    # Arrange
    comp = Composition(Identifier("a"), Identifier("b"))

    # Act & Assert
    with pytest.raises(AttributeError):
        comp.left = Identifier("c")  # Should fail (frozen)

def test_composition_repr():
    """Test Composition string representation."""
    # Arrange
    comp = Composition(Identifier("f"), Identifier("g"))

    # Act
    result = repr(comp)

    # Assert
    assert result == "(f ∘ g)"
```

**Run test**: `pytest tests/dsl/entities/test_composition.py`
**Result**: ❌ FAIL (module doesn't exist yet)

### Step 2: Green (Minimal Implementation)

```python
# src/dsl/entities/composition.py
from dataclasses import dataclass
from src.dsl.entities.ast_node import ASTNode

@dataclass(frozen=True)
class Composition(ASTNode):
    """
    Sequential composition: f ∘ g

    Represents categorical composition where output of g feeds into f.
    Associative: (f ∘ g) ∘ h = f ∘ (g ∘ h)
    """
    left: ASTNode
    right: ASTNode

    def __repr__(self) -> str:
        return f"({self.left} ∘ {self.right})"
```

**Run test**: `pytest tests/dsl/entities/test_composition.py`
**Result**: ✅ PASS

### Step 3: Refactor (Apply Clean Code)

```python
# src/dsl/entities/composition.py (refactored)
from dataclasses import dataclass
from typing import Optional
from src.dsl.entities.ast_node import ASTNode

@dataclass(frozen=True)
class Composition(ASTNode):
    """
    Sequential composition: f ∘ g (categorical morphism composition).

    Semantics: Execute right, then left (right-to-left composition).
    Laws: Associative, identity preserving.

    Example:
        test ∘ code ∘ plan
        Execute: plan → code → test
    """
    left: ASTNode   # f (executed second)
    right: ASTNode  # g (executed first)

    def __post_init__(self):
        """Validate composition."""
        if not isinstance(self.left, ASTNode):
            raise TypeError(f"left must be ASTNode, got {type(self.left)}")
        if not isinstance(self.right, ASTNode):
            raise TypeError(f"right must be ASTNode, got {type(self.right)}")

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"({self.left} ∘ {self.right})"

    def is_associative_with(self, other: 'Composition') -> bool:
        """Check if can be composed associatively."""
        return isinstance(other, Composition)
```

**Run tests again**: ✅ PASS (still passing after refactor)

**Commit**:
```bash
git add src/dsl/entities/composition.py tests/dsl/entities/test_composition.py
git commit -m "DSL: Add Composition entity with TDD tests

Implement sequential composition AST node (f ∘ g) following
Clean Architecture entity layer.

Benefits:
- Enables task chaining in CT DSL
- Immutable dataclass prevents bugs
- TDD ensures correctness
- Validation catches type errors early"
```

---

## Success Criteria

### Phase 1 Complete When:
- ✅ All 5 AST entities implemented with tests
- ✅ Parser parses all example programs from research
- ✅ 100% test coverage for entities
- ✅ All tests pass in CI/CD
- ✅ Committed to git with clean history

### Overall Project Complete When:
- ✅ End-to-end: DSL program → executed tasks
- ✅ All 5 example programs execute correctly
- ✅ Performance: 20%+ improvement in benchmarks
- ✅ Documentation complete
- ✅ User acceptance testing passed

---

**Next**: Begin TDD implementation starting with entities
