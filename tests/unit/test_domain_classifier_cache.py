"""
Unit tests for DomainClassifier caching functionality (Week 14, Priority 1).

Tests cache hit/miss behavior, LRU eviction, and performance improvements.
"""

import pytest
from src.entity import Task
from src.routing.domain_classifier import DomainClassifier


def create_task(description: str, task_id: str = None) -> Task:
    """Helper to create Task with correct parameter names."""
    return Task(description=description, task_id=task_id)


class TestDomainClassifierCache:
    """Test suite for DomainClassifier caching (Week 14)."""

    def test_cache_enabled_by_default(self):
        """Cache should be enabled by default."""
        classifier = DomainClassifier()
        assert classifier.enable_cache is True
        assert classifier.cache_size == 1000

    def test_cache_can_be_disabled(self):
        """Cache can be explicitly disabled."""
        classifier = DomainClassifier(enable_cache=False)
        assert classifier.enable_cache is False

    def test_cache_hit_on_repeated_task(self):
        """Repeated classification of same task should hit cache."""
        classifier = DomainClassifier(cache_size=10)
        task = create_task("Profile src/routing/rag_team_router.py using cProfile", "task1")

        # First call - cache miss
        domain1 = classifier.classify(task)
        assert domain1 == "performance"
        assert classifier.cache_hits == 0
        assert classifier.cache_misses == 1

        # Second call - cache hit
        domain2 = classifier.classify(task)
        assert domain2 == "performance"
        assert classifier.cache_hits == 1
        assert classifier.cache_misses == 1

        # Third call - another cache hit
        domain3 = classifier.classify(task)
        assert domain3 == "performance"
        assert classifier.cache_hits == 2
        assert classifier.cache_misses == 1

    def test_cache_hit_for_identical_descriptions(self):
        """Different tasks with identical descriptions should hit cache."""
        classifier = DomainClassifier(cache_size=10)

        task1 = create_task("Write unit tests for pattern quality manager", "task1")
        task2 = create_task("Write unit tests for pattern quality manager", "task2")  # Same description

        # First task - cache miss
        domain1 = classifier.classify(task1)
        assert domain1 == "testing"
        assert classifier.cache_misses == 1
        assert classifier.cache_hits == 0

        # Second task with same description - cache hit
        domain2 = classifier.classify(task2)
        assert domain2 == "testing"
        assert classifier.cache_misses == 1
        assert classifier.cache_hits == 1

    def test_cache_miss_for_different_descriptions(self):
        """Different task descriptions should miss cache."""
        classifier = DomainClassifier(cache_size=10)

        task1 = create_task("Profile performance bottlenecks", "task1")
        task2 = create_task("Write BDD acceptance tests", "task2")

        domain1 = classifier.classify(task1)
        assert domain1 == "performance"
        assert classifier.cache_misses == 1

        domain2 = classifier.classify(task2)
        assert domain2 == "qa"
        assert classifier.cache_misses == 2

    def test_lru_eviction(self):
        """Cache should evict oldest entries when exceeding size limit."""
        classifier = DomainClassifier(cache_size=3)  # Small cache for testing

        tasks = [
            create_task("Profile performance", "task1"),
            create_task("Write unit tests", "task2"),
            create_task("Deploy to production", "task3"),
            create_task("Document API endpoints", "task4"),
        ]

        # Fill cache to capacity
        for i in range(3):
            classifier.classify(tasks[i])

        assert classifier.cache_misses == 3
        assert len(classifier._classification_cache) == 3

        # Add 4th task - should evict oldest (task1)
        classifier.classify(tasks[3])
        assert classifier.cache_misses == 4
        assert len(classifier._classification_cache) == 3  # Still at capacity

        # Re-classify task1 - should be cache miss (was evicted)
        classifier.classify(tasks[0])
        assert classifier.cache_misses == 5  # New miss
        assert classifier.cache_hits == 0

        # Cache now contains: task2, task3, task4, task1 (task2 was evicted when task1 was re-added)
        # Re-classify task3 - should be cache hit (still in cache)
        classifier.classify(tasks[2])
        assert classifier.cache_hits == 1

        # Re-classify task4 - should be cache hit (still in cache)
        classifier.classify(tasks[3])
        assert classifier.cache_hits == 2

    def test_cache_preserves_observability_state(self):
        """Cache hit should restore last_classification_score and last_top3_scores."""
        classifier = DomainClassifier(cache_size=10)
        task = create_task("Optimize database queries and add caching", "task1")

        # First classification
        domain1 = classifier.classify(task)
        original_score = classifier.last_classification_score
        original_top3 = classifier.last_top3_scores

        assert original_score > 0
        assert len(original_top3) > 0

        # Classify different task (changes observability state)
        other_task = create_task("Write BDD tests", "task2")
        classifier.classify(other_task)

        # Re-classify original task - should restore original state
        domain2 = classifier.classify(task)
        assert domain2 == domain1
        assert classifier.last_classification_score == original_score
        assert classifier.last_top3_scores == original_top3

    def test_get_cache_statistics(self):
        """get_cache_statistics should return accurate metrics."""
        classifier = DomainClassifier(cache_size=100)

        # Initially empty
        stats = classifier.get_cache_statistics()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["total_requests"] == 0
        assert stats["size"] == 0
        assert stats["max_size"] == 100
        assert stats["hit_rate"] == 0.0
        assert stats["enabled"] is True

        # After some classifications
        task1 = create_task("Profile performance", "task1")
        task2 = create_task("Write tests", "task2")

        classifier.classify(task1)  # Miss
        classifier.classify(task1)  # Hit
        classifier.classify(task2)  # Miss
        classifier.classify(task1)  # Hit

        stats = classifier.get_cache_statistics()
        assert stats["hits"] == 2
        assert stats["misses"] == 2
        assert stats["total_requests"] == 4
        assert stats["size"] == 2
        assert stats["hit_rate"] == 0.5  # 50% hit rate

    def test_clear_cache(self):
        """clear_cache should reset cache and statistics."""
        classifier = DomainClassifier(cache_size=10)

        task = create_task("Profile performance", "task1")
        classifier.classify(task)
        classifier.classify(task)  # Cache hit

        assert classifier.cache_hits == 1
        assert classifier.cache_misses == 1
        assert len(classifier._classification_cache) > 0

        # Clear cache
        classifier.clear_cache()

        assert classifier.cache_hits == 0
        assert classifier.cache_misses == 0
        assert len(classifier._classification_cache) == 0

        # Next classification should be cache miss
        classifier.classify(task)
        assert classifier.cache_misses == 1
        assert classifier.cache_hits == 0

    def test_cache_disabled_behavior(self):
        """When cache disabled, should not cache results."""
        classifier = DomainClassifier(cache_size=10, enable_cache=False)

        task = create_task("Profile performance", "task1")

        # Multiple calls should all be "misses" (no caching)
        classifier.classify(task)
        classifier.classify(task)
        classifier.classify(task)

        # No cache statistics when disabled
        assert classifier.cache_hits == 0
        assert classifier.cache_misses == 0
        assert len(classifier._classification_cache) == 0

    def test_cache_case_insensitive(self):
        """Cache should treat descriptions as case-insensitive."""
        classifier = DomainClassifier(cache_size=10)

        task1 = create_task("Profile PERFORMANCE bottlenecks", "task1")
        task2 = create_task("profile performance bottlenecks", "task2")  # Same, different case

        domain1 = classifier.classify(task1)
        domain2 = classifier.classify(task2)

        # Should be cache hit (case-insensitive)
        assert domain1 == domain2
        assert classifier.cache_hits == 1
        assert classifier.cache_misses == 1

    def test_cache_with_large_workload(self):
        """Cache should improve performance with realistic workload."""
        classifier = DomainClassifier(cache_size=100)

        # Simulate 200 tasks with repeated patterns (modulo 50 = 50 unique patterns)
        tasks = []
        for i in range(100):
            tasks.append(create_task(f"Profile performance bottleneck {i % 50}", f"task_{i}"))
            tasks.append(create_task(f"Profile performance bottleneck {i % 50}", f"task_dup_{i}"))  # Duplicate

        # Classify all tasks
        for task in tasks:
            classifier.classify(task)

        stats = classifier.get_cache_statistics()

        # With i % 50, we have only 50 unique descriptions out of 200 tasks
        # Expected: 50 misses (first occurrence), 150 hits (duplicates)
        # Hit rate = 150/200 = 75%
        assert stats["total_requests"] == 200
        assert stats["hit_rate"] >= 0.70  # Allow some margin
        assert stats["hit_rate"] <= 0.80
        assert stats["size"] == 50  # Exactly 50 unique patterns cached

    def test_cache_key_normalization(self):
        """Cache should normalize whitespace and case."""
        classifier = DomainClassifier(cache_size=10)

        task1 = create_task("  Profile   PERFORMANCE   ", "task1")
        task2 = create_task("profile performance", "task2")

        classifier.classify(task1)
        classifier.classify(task2)

        # Both should map to same cache key (normalized)
        assert classifier.cache_hits == 1
        assert classifier.cache_misses == 1


class TestCachePerformanceImprovements:
    """Test cache performance benefits (Week 14, Priority 1)."""

    def test_cache_reduces_regex_overhead(self):
        """Cache should skip regex matching on hits."""
        classifier = DomainClassifier(cache_size=1000)

        # Create task with many keywords (expensive to match)
        task = create_task(
            "Profile src/routing/rag_team_router.py route_with_rag() method using cProfile, "
            "identify bottlenecks in pattern retrieval and embedding generation, "
            "implement caching for frequently-used embeddings, optimize SurrealDB queries with indexes",
            "task1"
        )

        # First call - full regex matching
        classifier.classify(task)

        # Subsequent calls should be much faster (cache hit, no regex)
        for _ in range(100):
            classifier.classify(task)

        stats = classifier.get_cache_statistics()
        assert stats["hit_rate"] == 100/101  # ~99% hit rate

    def test_cache_statistics_tracking(self):
        """Cache statistics should accurately track hit/miss ratio."""
        classifier = DomainClassifier(cache_size=50)

        # Workload: 10 unique tasks, each repeated 5 times
        unique_tasks = [
            create_task(f"Task type {i % 10}", f"task_{i}")
            for i in range(10)
        ]

        workload = unique_tasks * 5  # 50 total tasks

        for task in workload:
            classifier.classify(task)

        stats = classifier.get_cache_statistics()

        # Should have 10 misses (unique), 40 hits (repeats)
        assert stats["misses"] == 10
        assert stats["hits"] == 40
        assert stats["hit_rate"] == 0.8  # 80% hit rate
        assert stats["size"] == 10  # 10 unique cached


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
