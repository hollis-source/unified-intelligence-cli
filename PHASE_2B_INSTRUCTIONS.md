# Phase 2B: Function Renames - Execution Instructions

## Objective

Rename 12 functions in 3 files with backward-compatible aliases. All renames follow Clean Code verb-noun patterns and align with existing docstrings.

## Rename Specifications

### File 1: src/entities/category_theory/morphism.py (2 functions)

**Function 1: identity() → create_identity()**
- Line: 93
- Reason: Docstring says "Create identity morphism" - align name with docstring
- Implementation:
  ```python
  @staticmethod
  def create_identity(obj_type: str) -> "Morphism[A, A]":
      """Create identity morphism for an object type."""
      # ... existing implementation ...

  # Backward compatibility alias
  @staticmethod
  def identity(obj_type: str) -> "Morphism[A, A]":
      """DEPRECATED: Use create_identity() instead."""
      import warnings
      warnings.warn(
          "identity() is deprecated, use create_identity() instead",
          DeprecationWarning,
          stacklevel=2
      )
      return Morphism.create_identity(obj_type)
  ```

**Function 2: composed_transform() → apply_composed_transform()**
- Line: 77 (inner function inside compose() method)
- Reason: Function applies a composed transformation
- Implementation: Rename inner function only (no alias needed for inner functions)

### File 2: src/entities/category_theory/workflow_morphism.py (4 functions)

**All functions are @staticmethod factory methods**

**Function 1: htn_flatten() → flatten_htn()**
- Line: 25
- Pattern: verb (flatten) + noun (htn)
- Implementation: Rename + add deprecated alias

**Function 2: htn_remove_identity() → remove_htn_identity()**
- Line: 86
- Pattern: verb (remove) + noun phrase (htn_identity)
- Implementation: Rename + add deprecated alias

**Function 3: htn_simplify() → simplify_htn()**
- Line: 143
- Pattern: verb (simplify) + noun (htn)
- Implementation: Rename + add deprecated alias

**Function 4: workflow_optimize() → optimize_workflow()**
- Line: 274
- Pattern: verb (optimize) + noun (workflow)
- Implementation: Rename + add deprecated alias

### File 3: src/entities/graph/graph.py (6 functions)

**All functions are instance methods**

**Function 1: node_count() → count_nodes()**
- Line: 165
- Pattern: verb (count) + plural noun (nodes)
- Reason: More intuitive verb-first ordering
- Implementation: Rename + add deprecated alias

**Function 2: edge_count() → count_edges()**
- Line: 169
- Pattern: verb (count) + plural noun (edges)
- Implementation: Rename + add deprecated alias

**Function 3: dfs() → traverse_dfs()**
- Line: 173
- Reason: Docstring says "Depth-first search traversal"
- Implementation: Rename + add deprecated alias

**Function 4: bfs() → traverse_bfs()**
- Line: 212
- Reason: Docstring says "Breadth-first search traversal"
- Implementation: Rename + add deprecated alias

**Function 5: topological_sort() → sort_topologically()**
- Line: 290
- Pattern: verb (sort) + adverb (topologically)
- Implementation: Rename + add deprecated alias

**Function 6: subgraph() → extract_subgraph()**
- Line: 349
- Reason: Function extracts/creates a new subgraph from existing graph
- Implementation: Rename + add deprecated alias

## Backward Compatibility Pattern

For all public methods (not inner functions), use this pattern:

```python
# New function with correct name
def new_name(self, ...args) -> ReturnType:
    """Docstring (updated if needed)."""
    # existing implementation

# Deprecated alias
def old_name(self, ...args) -> ReturnType:
    """DEPRECATED: Use new_name() instead."""
    import warnings
    warnings.warn(
        "old_name() is deprecated, use new_name() instead",
        DeprecationWarning,
        stacklevel=2
    )
    return self.new_name(...args)
```

## Success Criteria

1. ✅ All 12 functions renamed to verb-noun patterns
2. ✅ Backward compatibility aliases in place for public methods
3. ✅ Deprecation warnings added
4. ✅ All tests pass
5. ✅ No breaking changes (both old and new names work)

## Testing

After refactoring:
```bash
# Run full test suite
python3 -m pytest tests/ -v

# Verify imports still work
python3 -c "from src.entities.category_theory.morphism import Morphism; print(Morphism.create_identity('test'))"
python3 -c "from src.entities.category_theory.morphism import Morphism; print(Morphism.identity('test'))"  # Deprecated but works

# Verify graph methods
python3 -c "from src.entities.graph.graph import Graph; g = Graph(); print(g.count_nodes())"
python3 -c "from src.entities.graph.graph import Graph; g = Graph(); print(g.node_count())"  # Deprecated but works
```

## Notes

- Inner functions (like composed_transform) don't need aliases
- Static methods use class name in alias: `return ClassName.new_name()`
- Instance methods use self: `return self.new_name()`
- All aliases should have deprecation warnings
- Update docstrings to reflect new names where appropriate

## Estimated Time

- Script creation: 30 minutes
- Execution: 15 minutes
- Testing: 15 minutes
- Total: ~1 hour

**Complexity**: Medium (backward compatibility + multiple files)
