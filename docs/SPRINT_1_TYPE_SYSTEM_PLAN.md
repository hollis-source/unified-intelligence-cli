# Sprint 1: Type-Safe Distributed Workflow Composition

**Story**: Story 1 from AGILE_STORIES_SCALABILITY_DISTRIBUTED_COMPUTE.md
**Effort**: 8 story points
**Duration**: 2-3 sprints (4-6 weeks)
**Status**: Planning → Ready for Implementation

---

## Objective

Implement type-level guarantees for DSL composition operators (∘, ×) ensuring morphism preservation across async boundaries, enabling compile-time validation of distributed workflows.

## Success Criteria (from Story 1)

1. ✅ `.ct` workflow files support type annotations for functor composition
2. ✅ Parser validates that output type of `f` matches input type of `g` in `g ∘ f`
3. ✅ Parallel composition `×` ensures product category laws (projection preservation)
4. ✅ Type errors caught during workflow parsing, not execution
5. ✅ Test suite: 10+ workflows with type mismatches correctly rejected

## Technical Architecture

### Phase 1: Type System Foundation (Week 1-2)

**Goal**: Extend DSL AST with type annotations and basic type inference

**Files to Create**:
- `src/dsl/types/type_system.py` - Core type classes (MonomorphicType, PolymorphicType, TypeVariable)
- `src/dsl/types/type_checker.py` - Hindley-Milner type inference engine
- `src/dsl/types/type_env.py` - Type environment for scope management
- `tests/unit/dsl/types/test_type_system.py` - Type system unit tests

**Key Abstractions**:
```python
class Type(ABC):
    """Base type for all DSL types"""
    @abstractmethod
    def unify(self, other: 'Type') -> Optional['Substitution']:
        """Unification algorithm (Robinson's algorithm)"""
        pass

class FunctionType(Type):
    """Function type: A → B"""
    def __init__(self, input_type: Type, output_type: Type):
        self.input = input_type
        self.output = output_type

class ProductType(Type):
    """Product type for parallel composition: A × B"""
    def __init__(self, left: Type, right: Type):
        self.left = left
        self.right = right
```

**Deliverables**:
- Type system with unification algorithm
- Basic type inference for simple compositions
- Unit tests: 20+ covering type algebra

### Phase 2: AST Integration (Week 2-3)

**Goal**: Integrate type system into existing DSL parser and AST

**Files to Modify**:
- `src/dsl/parser.py` - Add type annotation parsing
- `src/dsl/ast_nodes.py` - Add type fields to AST nodes
- `src/dsl/interpreter.py` - Add type checking before execution

**Type Annotation Syntax**:
```haskell
-- Sequential composition with explicit types
fetch_data :: () -> List[Commit]
analyze_commits :: List[Commit] -> List[Analysis]
aggregate :: List[Analysis] -> Report

-- Workflow composition (types inferred and checked)
aggregate ∘ analyze_commits ∘ fetch_data

-- Type error example (caught at parse time)
save_file :: Report -> FilePath
fetch_data :: () -> List[Commit]
save_file ∘ fetch_data  -- ERROR: Type mismatch
                         -- Expected: Report
                         -- Got: List[Commit]
```

**Deliverables**:
- Parser support for type annotations
- AST nodes with type information
- Integration tests: 10+ workflows with valid/invalid compositions

### Phase 3: Composition Operators (Week 3-4)

**Goal**: Implement type checking for ∘ (sequential) and × (parallel) operators

**Sequential Composition (∘)**:
```python
def check_composition(g: FunctionType, f: FunctionType) -> FunctionType:
    """
    Check g ∘ f composition.

    Category theory law: If f: A → B and g: B → C, then g ∘ f: A → C
    Type checking: g.input must unify with f.output
    """
    subst = f.output.unify(g.input)
    if subst is None:
        raise TypeMismatchError(
            f"Cannot compose {g} ∘ {f}: "
            f"output type {f.output} doesn't match input type {g.input}"
        )
    return FunctionType(f.input, g.output).apply_substitution(subst)
```

**Parallel Composition (×)**:
```python
def check_product(f: FunctionType, g: FunctionType) -> FunctionType:
    """
    Check f × g parallel composition.

    Category theory: Product in category of types
    Type: If f: A → B and g: C → D, then f × g: (A × C) → (B × D)
    """
    input_product = ProductType(f.input, g.input)
    output_product = ProductType(f.output, g.output)
    return FunctionType(input_product, output_product)
```

**Deliverables**:
- Sequential composition type checker
- Parallel composition type checker
- Product category laws validation
- Integration tests: 15+ workflows with mixed operators

### Phase 4: Category Laws Enforcement (Week 4-5)

**Goal**: Verify composition satisfies category theory laws at compile time

**Laws to Enforce**:

1. **Associativity**: `(h ∘ g) ∘ f ≡ h ∘ (g ∘ f)`
   - Type checker ensures types compose correctly regardless of grouping
   - Parser allows parentheses for explicit grouping

2. **Identity**: `id ∘ f ≡ f ≡ f ∘ id`
   - Add identity function `id :: A → A`
   - Type checker validates identity composition

3. **Product Projections**: For `f × g`, projections `π₁` and `π₂` exist
   - `π₁ :: (A × B) → A`
   - `π₂ :: (A × B) → B`

**Implementation**:
```python
# src/dsl/types/category_laws.py
def verify_associativity(h: FunctionType, g: FunctionType, f: FunctionType):
    """Verify (h ∘ g) ∘ f ≡ h ∘ (g ∘ f)"""
    left = check_composition(check_composition(h, g), f)
    right = check_composition(h, check_composition(g, f))
    assert left.input == right.input
    assert left.output == right.output

def verify_identity(f: FunctionType):
    """Verify id ∘ f ≡ f ≡ f ∘ id"""
    id_func = FunctionType(TypeVariable("a"), TypeVariable("a"))
    left = check_composition(id_func, f)
    right = check_composition(f, id_func)
    assert left.input == f.input
    assert left.output == f.output
    assert right.input == f.input
    assert right.output == f.output
```

**Deliverables**:
- Category laws verification module
- Property-based tests using Hypothesis
- Formal proof sketches in comments

### Phase 5: Error Reporting & Integration (Week 5-6)

**Goal**: Production-ready error messages and full integration

**Error Message Format**:
```
Type Error in workflow: examples/workflows/performance_analysis.ct
Line 15: save_report ∘ fetch_commits

Cannot compose functions:
  save_report  :: Report → FilePath
  fetch_commits :: () → List[Commit]

Expected: save_report input type should match fetch_commits output type
  Expected: Report
  Got:      List[Commit]

Hint: Add intermediate function to transform List[Commit] → Report
      aggregate_commits :: List[Commit] → Report
```

**Files to Create**:
- `src/dsl/types/error_reporting.py` - Rich error formatting
- `src/dsl/types/type_hints.py` - Suggested fixes for common errors

**Deliverables**:
- User-friendly error messages with hints
- Integration with existing error handling
- Full end-to-end test suite: 25+ workflows

---

## Test Strategy

### Unit Tests (40+ tests)
- Type unification algorithm (Robinson's algorithm correctness)
- Type inference for simple/complex compositions
- Product types and projections
- Category laws (associativity, identity)

### Integration Tests (20+ tests)
- Valid `.ct` workflows with correct types
- Invalid workflows with type mismatches (caught at parse time)
- Mixed sequential and parallel composition
- Edge cases: recursive types, polymorphic functions

### Property-Based Tests (10+ properties)
Using Hypothesis for generative testing:
- `∀ f, g, h: (h ∘ g) ∘ f ≡ h ∘ (g ∘ f)` (associativity)
- `∀ f: id ∘ f ≡ f ≡ f ∘ id` (identity)
- `∀ f, g: π₁ ∘ (f × g) ≡ f ∘ π₁` (product laws)

### Performance Tests
- Type checking overhead: <10ms for 100-function workflows
- Memory usage: O(n) where n = number of functions

---

## Dependencies

**Python Packages**:
- `typing_extensions` - Advanced type hints
- `hypothesis` - Property-based testing
- `pytest` - Test framework

**Internal Dependencies**:
- Existing DSL parser (`src/dsl/parser.py`)
- AST nodes (`src/dsl/ast_nodes.py`)
- Interpreter (`src/dsl/interpreter.py`)

**External Research**:
- Hindley-Milner type inference (Damas-Milner algorithm)
- Robinson's unification algorithm
- Category theory: functor composition, product categories

---

## Risk Mitigation

**Risk 1**: Type inference too slow for large workflows
- **Mitigation**: Incremental type checking, caching inferred types
- **Contingency**: Fall back to explicit type annotations

**Risk 2**: Complex error messages confuse users
- **Mitigation**: Iterate on error message format with user feedback
- **Contingency**: Add `--explain` flag for verbose error explanations

**Risk 3**: Integration breaks existing workflows
- **Mitigation**: Backward compatibility mode (disable type checking)
- **Contingency**: Feature flag: `ENABLE_TYPE_CHECKING=false`

---

## Success Metrics

**Code Quality**:
- ✅ All functions <20 lines (Clean Code)
- ✅ Type checker module <500 lines total
- ✅ 100% test coverage for type system

**Performance**:
- ✅ Type checking <10ms for typical workflows
- ✅ Zero runtime overhead (type checking at parse time)

**Usability**:
- ✅ 10+ test workflows run without modification
- ✅ Type errors caught with helpful error messages
- ✅ Documentation with 5+ examples

**Correctness**:
- ✅ Property-based tests pass 10,000+ generated test cases
- ✅ Zero false positives (valid workflows rejected)
- ✅ Zero false negatives (invalid workflows accepted)

---

## Timeline

**Week 1-2**: Phase 1 - Type System Foundation
**Week 3**: Phase 2 - AST Integration
**Week 4**: Phase 3 - Composition Operators
**Week 5**: Phase 4 - Category Laws
**Week 6**: Phase 5 - Error Reporting & Integration

**Total**: 6 weeks (matches 8 story point estimate for 2-3 sprints)

---

## Next Steps (Ready to Start)

1. **Create type system module structure**:
   ```bash
   mkdir -p src/dsl/types
   touch src/dsl/types/__init__.py
   touch src/dsl/types/type_system.py
   touch src/dsl/types/type_checker.py
   touch src/dsl/types/type_env.py
   ```

2. **Set up test infrastructure**:
   ```bash
   mkdir -p tests/unit/dsl/types
   touch tests/unit/dsl/types/test_type_system.py
   touch tests/unit/dsl/types/test_type_checker.py
   touch tests/unit/dsl/types/test_composition.py
   ```

3. **Implement Type base class** (first task):
   - Define `Type` abstract base class
   - Implement `MonomorphicType` and `PolymorphicType`
   - Add `unify()` method with Robinson's algorithm

4. **Write first unit test**:
   - Test type unification for simple types
   - TDD: Write failing test, then implement

---

**Generated**: 2025-10-03
**Status**: Ready for Implementation
**Owner**: Category Theory & DSL Teams (collaborative)
**Foundation**: Story 1 from AGILE_STORIES_SCALABILITY_DISTRIBUTED_COMPUTE.md
**Research Base**: Phase 1 & Phase 2 (100% routing accuracy validated)
