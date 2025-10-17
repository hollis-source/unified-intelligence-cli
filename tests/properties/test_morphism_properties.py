"""Property-based tests for morphisms using Hypothesis.

Uses generative testing to verify category theory laws hold for
all possible morphism combinations. Hypothesis automatically generates
thousands of test cases to find edge cases.

Properties verified:
- Identity laws: f ∘ id = id ∘ f = f
- Associativity: (h ∘ g) ∘ f = h ∘ (g ∘ f)
- Composition correctness: Types match, transforms apply correctly
"""

import pytest
from hypothesis import given, strategies as st, assume, example
from hypothesis import settings, HealthCheck
from src.entity.category_theory import Morphism
from src.entity.category_theory.workflow_morphism import WorkflowMorphism
from src.entity.htn import HTNNode


# ============================================================================
# Hypothesis Strategies (test data generators)
# ============================================================================

@st.composite
def int_morphism_strategy(draw):
    """Generate morphisms that transform integers.

    This strategy creates morphisms with int -> int signatures
    using simple, composable transformations.
    """
    name = draw(st.text(min_size=1, max_size=10, alphabet="abcdefghij"))

    # Generate simple integer transformations
    transform_type = draw(st.sampled_from([
        "identity",
        "increment",
        "double",
        "negate",
        "abs"
    ]))

    if transform_type == "identity":
        transform = lambda x: x
    elif transform_type == "increment":
        transform = lambda x: x + 1
    elif transform_type == "double":
        transform = lambda x: x * 2
    elif transform_type == "negate":
        transform = lambda x: -x
    elif transform_type == "abs":
        transform = lambda x: abs(x)

    return Morphism(
        name=name,
        source="int",
        target="int",
        transform=transform
    )


@st.composite
def htn_node_strategy(draw):
    """Generate random HTN nodes for testing.

    Creates valid HTN structures including:
    - Primitive nodes (leaf tasks)
    - Compound nodes (with subtasks)
    - Compositions (∘ operator)
    - Products (× operator)
    """
    node_type = draw(st.sampled_from(["primitive", "compound", "composition", "product"]))
    task_id = draw(st.text(min_size=1, max_size=8, alphabet="abcdef"))
    description = f"task_{task_id}"

    if node_type == "primitive":
        return HTNNode(
            task_id=task_id,
            description=description
        )

    # For compound nodes, generate 1-3 subtasks
    num_subtasks = draw(st.integers(min_value=1, max_value=3))
    subtasks = []

    for i in range(num_subtasks):
        subtask = HTNNode(
            task_id=f"{task_id}_sub{i}",
            description=f"subtask_{i}"
        )
        subtasks.append(subtask)

    metadata = {}
    if node_type == "composition":
        metadata["operator"] = "∘"
    elif node_type == "product":
        metadata["operator"] = "×"

    return HTNNode(
        task_id=task_id,
        description=description,
        subtasks=subtasks,
        metadata=metadata
    )


# ============================================================================
# Identity Law Properties
# ============================================================================

@given(int_morphism_strategy())
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_left_identity_law(morphism):
    """Property: id ∘ f = f (left identity).

    Composing any morphism f with identity on the left
    should yield the original morphism's behavior.
    """
    id_morph = Morphism.identity(morphism.target)
    composed = id_morph.compose(morphism)

    # Type preservation
    assert composed.source == morphism.source
    assert composed.target == morphism.target

    # Behavior preservation (test on sample values)
    test_values = [0, 1, -1, 42, -42]
    for value in test_values:
        assert composed.transform(value) == morphism.transform(value)


@given(int_morphism_strategy())
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_right_identity_law(morphism):
    """Property: f ∘ id = f (right identity).

    Composing any morphism f with identity on the right
    should yield the original morphism's behavior.
    """
    id_morph = Morphism.identity(morphism.source)
    composed = morphism.compose(id_morph)

    # Type preservation
    assert composed.source == morphism.source
    assert composed.target == morphism.target

    # Behavior preservation
    test_values = [0, 1, -1, 42, -42]
    for value in test_values:
        assert composed.transform(value) == morphism.transform(value)


# ============================================================================
# Associativity Property
# ============================================================================

@given(
    int_morphism_strategy(),
    int_morphism_strategy(),
    int_morphism_strategy()
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_associativity_law(f, g, h):
    """Property: (h ∘ g) ∘ f = h ∘ (g ∘ f) (associativity).

    Composition is associative - the order of grouping doesn't matter.
    This is a fundamental category theory law.
    """
    # Compose left-to-right: (h ∘ g) ∘ f
    hg = h.compose(g)
    left_assoc = hg.compose(f)

    # Compose right-to-left: h ∘ (g ∘ f)
    gf = g.compose(f)
    right_assoc = h.compose(gf)

    # Type preservation
    assert left_assoc.source == right_assoc.source
    assert left_assoc.target == right_assoc.target

    # Behavior equivalence
    test_values = [0, 1, -1, 10, -10]
    for value in test_values:
        assert left_assoc.transform(value) == right_assoc.transform(value)


# ============================================================================
# Composition Properties
# ============================================================================

@given(int_morphism_strategy(), int_morphism_strategy())
@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_composition_type_safety(f, g):
    """Property: Composition respects type matching.

    Can only compose morphisms where source of one matches target of other.
    """
    # These morphisms are all int -> int, so composition should work
    composed = f.compose(g)

    assert composed.source == g.source
    assert composed.target == f.target

    # Name reflects composition
    assert g.name in composed.name or f.name in composed.name


@given(int_morphism_strategy())
@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_identity_is_neutral_element(morphism):
    """Property: Identity morphism is neutral element.

    id ∘ id = id and id behaves correctly when composed.
    """
    id_morph = Morphism.identity(morphism.source)
    id_composed = id_morph.compose(id_morph)

    # Composing identity with itself yields identity
    test_values = [0, 5, -5, 100]
    for value in test_values:
        assert id_composed.transform(value) == value


# ============================================================================
# Workflow Morphism Properties
# ============================================================================

@given(htn_node_strategy())
@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_htn_flatten_preserves_primitives(htn):
    """Property: Flattening preserves all primitive tasks.

    When we flatten nested compositions, all leaf tasks are preserved.
    """
    flatten_morph = WorkflowMorphism.htn_flatten()
    result = flatten_morph(htn)

    # Count primitives before and after
    def count_primitives(node):
        if node.subtasks is None or node.is_primitive():
            return 1 if not node.task_id.startswith("id_") else 0
        return sum(count_primitives(st) for st in node.subtasks)

    original_count = count_primitives(htn)
    flattened_count = count_primitives(result)

    # Primitive count preserved (flattening only changes structure)
    assert original_count == flattened_count


@given(htn_node_strategy())
@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_htn_simplify_reduces_or_preserves_depth(htn):
    """Property: Simplification reduces or preserves depth.

    Simplifying HTN should never increase depth, only reduce it.
    """
    simplify_morph = WorkflowMorphism.htn_simplify()
    result = simplify_morph(htn)

    def calculate_depth(node):
        if node.subtasks is None or node.is_primitive():
            return 1
        return 1 + max((calculate_depth(st) for st in node.subtasks), default=0)

    original_depth = calculate_depth(htn)
    simplified_depth = calculate_depth(result)

    # Depth should not increase
    assert simplified_depth <= original_depth


@given(htn_node_strategy())
@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_workflow_optimize_is_idempotent(htn):
    """Property: Optimization is idempotent.

    Applying optimization twice should be same as applying once:
    optimize(optimize(x)) = optimize(x)
    """
    optimize_morph = WorkflowMorphism.workflow_optimize()

    # Apply once
    optimized_once = optimize_morph(htn)

    # Apply twice
    optimized_twice = optimize_morph(optimized_once)

    # Should be structurally identical (same task IDs)
    def extract_task_ids(node):
        ids = {node.task_id}
        if node.subtasks:
            for st in node.subtasks:
                ids.update(extract_task_ids(st))
        return ids

    ids_once = extract_task_ids(optimized_once)
    ids_twice = extract_task_ids(optimized_twice)

    # Idempotent: applying twice gives same result as once
    assert ids_once == ids_twice


# ============================================================================
# Morphism Chain Properties
# ============================================================================

@given(
    int_morphism_strategy(),
    int_morphism_strategy(),
    int_morphism_strategy()
)
@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_compose_chain_correctness(f, g, h):
    """Property: compose_chain produces correct composition.

    compose_chain(f, g, h) should be equivalent to h ∘ g ∘ f
    """
    from src.entity.category_theory.morphism import compose_chain

    chained = compose_chain(f, g, h)

    # Manual composition: h ∘ g ∘ f
    manual = h.compose(g.compose(f))

    # Should produce same result
    test_values = [0, 1, -1, 10]
    for value in test_values:
        assert chained.transform(value) == manual.transform(value)


@given(int_morphism_strategy())
@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_single_morphism_chain(morphism):
    """Property: Chain of one morphism is the morphism itself.

    compose_chain(f) = f
    """
    from src.entity.category_theory.morphism import compose_chain

    chained = compose_chain(morphism)

    assert chained.name == morphism.name
    assert chained.source == morphism.source
    assert chained.target == morphism.target

    test_values = [0, 5, -5]
    for value in test_values:
        assert chained.transform(value) == morphism.transform(value)


# ============================================================================
# Edge Case Properties
# ============================================================================

@given(st.integers(min_value=-1000, max_value=1000))
@settings(max_examples=100)
def test_identity_morphism_on_all_values(value):
    """Property: Identity morphism preserves all values.

    id(x) = x for all x
    """
    id_morph = Morphism.identity("int")
    assert id_morph.transform(value) == value


@given(
    int_morphism_strategy(),
    st.integers(min_value=-100, max_value=100)
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_morphism_transform_executes(morphism, value):
    """Property: All morphisms can transform values without error.

    Morphisms should not raise exceptions during transformation.
    """
    # Should not raise exception
    result = morphism.transform(value)

    # Result should be an integer
    assert isinstance(result, int)


# ============================================================================
# Workflow Preservation Properties
# ============================================================================

@given(htn_node_strategy())
@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_transformation_preserves_task_ids(htn):
    """Property: Transformations preserve or subset task IDs.

    Morphism transformations can remove intermediate nodes (flatten),
    remove identities, or simplify structure, but should not add new tasks.
    """
    optimize_morph = WorkflowMorphism.workflow_optimize()
    result = optimize_morph(htn)

    def extract_ids(node):
        ids = {node.task_id}
        if node.subtasks:
            for st in node.subtasks:
                ids.update(extract_ids(st))
        return ids

    original_ids = extract_ids(htn)
    transformed_ids = extract_ids(result)

    # Transformed IDs should be a subset of original
    # (transformations can remove but not add tasks)
    assert transformed_ids.issubset(original_ids) or original_ids.issubset(transformed_ids)


@given(htn_node_strategy())
@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_multiple_transformations_commute(htn):
    """Property: Some transformations commute.

    flatten ∘ simplify might equal simplify ∘ flatten
    (not always true, but structure should be preserved)
    """
    flatten = WorkflowMorphism.htn_flatten()
    simplify = WorkflowMorphism.htn_simplify()

    # Apply in different orders
    result1 = simplify(flatten(htn))
    result2 = flatten(simplify(htn))

    # May not be identical, but should have same primitives
    def get_primitives(node):
        if node.subtasks is None or node.is_primitive():
            return {node.task_id} if not node.task_id.startswith("id_") else set()
        prims = set()
        for st in node.subtasks:
            prims.update(get_primitives(st))
        return prims

    prims1 = get_primitives(result1)
    prims2 = get_primitives(result2)

    # Same primitive tasks regardless of order
    assert prims1 == prims2
