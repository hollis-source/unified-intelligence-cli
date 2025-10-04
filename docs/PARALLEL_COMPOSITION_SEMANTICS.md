# Parallel Composition Semantics

**Status**: Design Decision
**Date**: 2025-10-04
**Issue**: Integration tests revealed semantic gap between product types and broadcast execution

## Problem Statement

The DSL parallel composition operator `×` (or `*`) currently implements **product morphisms** from category theory:

```haskell
f :: A -> B
g :: C -> D
(f × g) :: (A × C) -> (B × D)  -- Current implementation
```

However, documentation and workflow examples suggest **broadcast semantics**:

```haskell
f :: A -> B
g :: A -> C
broadcast(f, g) :: A -> (B × C)  -- Desired for parallel execution
```

## Category Theory Analysis

### Product Morphism (Current)
From category theory, the product of morphisms `f × g` is defined as:
```
f : A → B
g : C → D
f × g : A × C → B × D
```

This is **mathematically correct** but requires **separate inputs** for each function.

### Broadcast Pattern (Desired)
Broadcasting the same input to multiple functions requires **diagonal composition**:
```
Δ : A → A × A           (diagonal functor)
f × g : A × A → B × C   (product morphism)
(f × g) ∘ Δ : A → B × C (broadcast composition)
```

The diagonal functor `Δ` duplicates input: `Δ(x) = (x, x)`.

## Design Decision: Explicit Diagonal Functor

**Rationale**: Keep mathematical correctness while enabling broadcast semantics.

### Solution: Add `duplicate` Operator

```haskell
# Type signature for duplicate (diagonal functor)
duplicate :: a -> (a × a)

# Explicit broadcast composition
f :: FileList -> StyleReport
g :: FileList -> SecurityReport

# Current (INCORRECT - type error):
parallel = (f * g) o get_files
# Error: (FileList × FileList) ≠ FileList

# Correct (with diagonal):
parallel = (f * g) o duplicate o get_files
# Type flow: () → FileList → (FileList × FileList) → (StyleReport × SecurityReport)
```

### Alternative: Broadcast Operator Syntax

Introduce explicit broadcast operator `⊗` (or `**`):

```haskell
# Broadcast operator (syntactic sugar for product ∘ diagonal)
(f ⊗ g) ≡ (f × g) ∘ duplicate

# Usage:
parallel = (f ** g) o get_files
# Type flow: () → FileList → (StyleReport × SecurityReport)
```

## Implementation Plan

### Phase 1: Add Diagonal Functor ✅
1. Add `duplicate` to grammar: `DUPLICATE: "duplicate" | "Δ"`
2. Implement in type checker: `duplicate : a -> (a × a)`
3. Add to interpreter: broadcast input to product tuple
4. Document in TYPE_SAFE_DSL_GUIDE.md

### Phase 2: Add Broadcast Operator (Optional)
1. Add `BROADCAST: "**" | "⊗"` to grammar
2. Desugar `(f ** g)` → `(f * g) ∘ duplicate` during parsing
3. Type inference treats as composition
4. Update examples to use broadcast syntax

### Phase 3: Update Examples & Tests
1. Fix `type_safe_code_review.ct` parallel examples
2. Add `examples/workflows/parallel_broadcast.ct` demonstrating both patterns
3. Add integration tests for parallel execution
4. Update TYPE_SAFE_DSL_GUIDE.md with clarifications

## Migration Guide

### Current Workflows (Broken)
```haskell
# This FAILS type checking:
parallel_analysis = (analyze_style * analyze_security) o get_files
# Error: Expected (FileList × FileList), got FileList
```

### Fix Option 1: Explicit Diagonal
```haskell
# Add duplicate operator:
parallel_analysis = (analyze_style * analyze_security) o duplicate o get_files
```

### Fix Option 2: Broadcast Operator (Future)
```haskell
# Use broadcast syntax:
parallel_analysis = (analyze_style ** analyze_security) o get_files
```

### Fix Option 3: Restructure with Product Inputs
```haskell
# Create separate data sources (rare use case):
get_style_data :: () -> FileList
get_security_data :: () -> FileList

parallel_analysis = (analyze_style * analyze_security) o (get_style_data * get_security_data)
```

## Type Examples

### Sequential Composition (Works Today)
```haskell
f :: A -> B
g :: B -> C
g ∘ f :: A -> C
```

### Product Morphism (Works Today)
```haskell
f :: A -> B
g :: C -> D
(f × g) :: (A × C) -> (B × D)
```

### Broadcast via Diagonal (New)
```haskell
duplicate :: A -> (A × A)
f :: A -> B
g :: A -> C

# Explicit:
(f × g) ∘ duplicate :: A -> (B × C)

# Syntactic sugar (future):
f ** g :: A -> (B × C)
```

## Mathematical Guarantees

### Category Laws Still Hold
1. **Associativity**: `(f ∘ g) ∘ h ≡ f ∘ (g ∘ h)` ✓
2. **Identity**: `id ∘ f ≡ f ≡ f ∘ id` ✓
3. **Product Bifunctor**: `(f × g) ∘ (h × k) ≡ (f ∘ h) × (g ∘ k)` ✓
4. **Diagonal Natural Transformation**: `(f × g) ∘ Δ ≡ Δ ∘ f` (when f = g) ✓

### Type Safety Preserved
- Product types remain structurally sound
- Diagonal functor is total (always defined)
- Broadcast composition is well-typed
- Runtime validation checks maintained

## References

- **Category Theory**: Awodey, "Category Theory", Chapter 6 (Products and Coproducts)
- **Haskell**: Control.Arrow (Arrow tutorial on parallel composition)
- **Type System**: Hindley-Milner type inference with product types
- **Implementation**: `src/dsl/types/type_checker.py:114-144` (check_product function)

## Status

- ✅ **Design Decision**: Add explicit diagonal functor
- ⏳ **Implementation**: Phase 1 in progress
- ⏳ **Migration**: Examples need updating
- ⏳ **Testing**: Integration tests needed

## Future Work

- **Coproduct (Sum Types)**: `Either A B` for error handling
- **Applicative Functors**: Generalized broadcast over functors
- **Monad Transformers**: Composable effects with broadcast semantics
- **Distributed Broadcast**: Zero-copy broadcasting in distributed systems
