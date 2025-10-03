"""
Domain Classifier - Classifies tasks by domain for hierarchical routing.

Clean Architecture: Strategy pattern for domain detection.
Week 11: Part of hierarchical agent scaling infrastructure.
Week 13: Added metrics collection (Priority 3).
"""

import re
import logging
from typing import Dict, List, Optional
from src.entities import Task


logger = logging.getLogger(__name__)


class DomainClassifier:
    """
    Classifies tasks into software development domains.

    Strategy: Pattern-based classification using regex keyword matching.
    Purpose: Route tasks to appropriate Tier 2 domain leads.

    Clean Code: Single responsibility - domain detection only.
    """

    # Domain patterns: Map domain to keyword patterns
    DOMAIN_PATTERNS: Dict[str, List[str]] = {
        "frontend": [
            r"\bui\b", r"\bux\b", r"user interface", r"user experience",
            r"\breact\b", r"\bvue\b", r"\bangular\b", r"svelte",
            r"\bcss\b", r"\bhtml\b", r"component", r"responsive",
            r"accessibility", r"frontend", r"front-end", r"client-side",
            r"state management", r"redux", r"mobx", r"dashboard",
            r"navbar", r"modal", r"form validation", r"web page"
        ],
        "backend": [
            r"\bapi\b", r"\brest\b", r"\bgraphql\b", r"endpoint",
            r"database", r"\bsql\b", r"nosql", r"mongodb", r"postgresql",
            r"server", r"microservice", r"backend", r"back-end",
            r"server-side", r"authentication", r"authorization",
            r"middleware", r"orm", r"query", r"schema",
            r"scalability", r"distributed", r"cache", r"redis"
        ],
        "testing": [
            r"\btest\b", r"testing", r"tests", r"\bqa\b",
            r"quality assurance", r"validate", r"verify", r"check",
            r"unit test", r"integration test", r"e2e", r"end-to-end",
            r"coverage", r"pytest", r"jest", r"mocha", r"selenium",
            r"cypress", r"test suite", r"test case", r"assertion",
            r"mock", r"stub", r"fixture", r"tdd", r"bdd"
        ],
        "research": [
            r"\bresearch\b", r"investigate", r"explore", r"study",
            r"analyze", r"analysis", r"document", r"documentation",
            r"find out", r"learn about", r"understand",
            r"compare", r"evaluate", r"assess", r"survey",
            r"\badr\b", r"architecture decision", r"design doc",
            r"technical writing", r"knowledge base", r"\brfc\b"
        ],
        "devops": [
            r"\bdevops\b", r"deployment", r"deploy", r"\bci\b", r"\bcd\b",
            r"ci/cd", r"pipeline", r"infrastructure",
            r"\bdocker\b", r"dockerfile", r"kubernetes", r"\bk8s\b",
            r"container", r"orchestration", r"monitoring",
            r"observability", r"logging", r"metrics", r"prometheus",
            r"grafana", r"jenkins", r"github actions", r"gitlab ci",
            r"release", r"rollback", r"production"
        ],
        "security": [
            r"\bsecurity\b", r"secure", r"vulnerability", r"vuln",
            r"\bauth\b", r"authentication", r"authorization",
            r"encryption", r"decrypt", r"certificate", r"\bssl\b", r"\btls\b",
            r"owasp", r"xss", r"csrf", r"sql injection",
            r"penetration test", r"pen test", r"audit",
            r"secrets management", r"password", r"token", r"\bjwt\b"
        ],
        "performance": [
            r"\bperformance\b", r"optimize", r"optimization",
            r"profiling", r"profile", r"benchmark", r"benchmarking",
            r"latency", r"throughput", r"speed", r"fast", r"slow",
            r"bottleneck", r"memory leak", r"cpu usage",
            r"caching", r"cache", r"efficiency", r"scalability"
        ],
        "documentation": [
            r"\bdocument\b", r"documentation", r"docs",
            r"\breadme\b", r"user guide", r"tutorial", r"how-to",
            r"api docs", r"api documentation", r"changelog",
            r"release notes", r"getting started", r"quickstart",
            r"examples", r"reference", r"manual"
        ],
        # Week 13: Specialized domains for Category Theory and DSL teams
        "category-theory": [
            r"\bfunctor\b", r"\bmonad\b", r"\bmonoid\b", r"\bmorphism\b",
            r"category theory", r"category-theory", r"natural transformation",
            r"composition", r"algebraic", r"\balgebra\b",
            r"mathematical", r"\btheory\b", r"proof", r"\blaw\b",
            r"compose", r"composability", r"∘", r"type preservation"
        ],
        "dsl": [
            r"\.ct\b", r"ct-file", r"ct file", r"\.ct workflow",
            r"dsl", r"domain-specific language", r"dsl-task",
            r"dsl deployment", r"dsl-design", r"dsl composition",
            r"workflow design", r"pipeline design", r"task engineering",
            r"dsl architect", r"dsl engineer", r"composable workflow"
        ]
    }

    # Week 13: Keyword weights for specialized domains (Priority 1 fix)
    # Higher weight = more important for domain classification
    # Solves routing issue where generic keywords override specialized terms
    DOMAIN_KEYWORD_WEIGHTS: Dict[str, Dict[str, int]] = {
        "category-theory": {
            # Specialized mathematical terms (10x weight)
            r"\bfunctor\b": 10,
            r"\bmonad\b": 10,
            r"\bmonoid\b": 10,
            r"\bmorphism\b": 10,
            "natural transformation": 10,
            "category theory": 10,
            "category-theory": 10,
            # Mathematical context (8x weight)
            r"\balgebra\b": 8,
            "algebraic": 8,
            r"proof": 8,
            r"\blaw\b": 8,
            "type preservation": 8,
            # Composition (medium weight, shared with other domains)
            "composition": 5,
            "compose": 5,
            "composability": 5,
            r"∘": 5,
            # Generic terms (lower weight)
            "mathematical": 3,
            r"\btheory\b": 3
        },
        "dsl": {
            # DSL-specific file syntax (10x weight)
            r"\.ct\b": 10,
            "ct-file": 10,
            "ct file": 10,
            r"\.ct workflow": 10,
            # DSL specialization (10x weight)
            "dsl": 10,
            "domain-specific language": 10,
            "dsl-task": 10,
            "dsl deployment": 10,
            "dsl-design": 10,
            "dsl composition": 10,
            "dsl architect": 10,
            "dsl engineer": 10,
            "composable workflow": 8,
            "task engineering": 8,
            # Design concepts (medium weight, semi-generic)
            "workflow design": 5,
            "pipeline design": 5
        },
        # Generic terms with low weights to avoid overriding specialized domains
        "testing": {
            "validate": 3,  # Generic term
            "verify": 3,
            "check": 3,
            # Specialized testing terms keep default weight (1)
        },
        "devops": {
            "deployment": 3,  # Generic term
            "deploy": 3,
            "workflow": 2,  # Very generic
            "pipeline": 3,
            "orchestration": 3,
            # Specialized devops terms keep default weight (1)
        }
    }

    def __init__(self, metrics_collector: Optional['MetricsCollector'] = None):
        """
        Initialize domain classifier with compiled regex patterns.

        Args:
            metrics_collector: Optional metrics collector for tracking (Week 13)
        """
        # Compile patterns for performance
        self._compiled_patterns: Dict[str, List[re.Pattern]] = {
            domain: [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
            for domain, patterns in self.DOMAIN_PATTERNS.items()
        }

        # Metrics collection (optional, injected via DIP)
        self.metrics_collector = metrics_collector

        # Track last classification for metrics
        self.last_classification_score: float = 0.0

        logger.info(f"DomainClassifier initialized with {len(self.DOMAIN_PATTERNS)} domains")

    def classify(self, task: Task) -> str:
        """
        Classify task into primary domain using weighted keyword matching.

        Week 13: Implements weighted scoring to prioritize specialized domains.

        Args:
            task: Task to classify

        Returns:
            Domain string ("frontend", "backend", "testing", "category-theory", "dsl", etc.)
            Returns "general" if no specific domain detected

        Strategy:
            - Calculate weighted score per domain (not simple count)
            - Patterns with explicit weights use those weights
            - Patterns without weights use default weight of 1
            - Return domain with highest weighted score
            - Specialized domains (category-theory, dsl) have high-weight keywords

        Example:
            "Validate functor composition" →
            - testing: validate (weight 3) = 3
            - category-theory: functor (weight 10) = 10
            - Result: category-theory wins
        """
        description = task.description.lower()

        # Calculate weighted scores per domain
        domain_scores: Dict[str, float] = {domain: 0.0 for domain in self.DOMAIN_PATTERNS}

        for domain, patterns in self._compiled_patterns.items():
            domain_weights = self.DOMAIN_KEYWORD_WEIGHTS.get(domain, {})

            for pattern in patterns:
                if pattern.search(description):
                    # Get weight for this pattern (default = 1.0)
                    pattern_str = pattern.pattern
                    weight = domain_weights.get(pattern_str, 1.0)
                    domain_scores[domain] += weight

        # Find domain with highest score
        max_score = max(domain_scores.values())

        # Store for metrics access
        self.last_classification_score = max_score

        if max_score == 0:
            # No domain patterns matched
            logger.debug(f"Task '{task.description[:50]}...' classified as 'general' (no patterns)")
            return "general"

        # Get domain(s) with max score
        top_domains = [domain for domain, score in domain_scores.items() if score == max_score]

        if len(top_domains) == 1:
            domain = top_domains[0]
            logger.info(
                f"Task '{task.description[:50]}...' classified as '{domain}' "
                f"(weighted score: {max_score:.1f})"
            )
            return domain

        # Multiple domains tied - use priority order (specialized domains first)
        priority_order = [
            "category-theory", "dsl",  # Specialized domains (highest priority)
            "backend", "frontend", "testing", "devops",  # Core domains
            "security", "performance", "research", "documentation"  # Support domains
        ]
        for priority_domain in priority_order:
            if priority_domain in top_domains:
                logger.info(
                    f"Task '{task.description[:50]}...' classified as '{priority_domain}' "
                    f"(tie-breaker: weighted score {max_score:.1f} across {len(top_domains)} domains)"
                )
                return priority_domain

        # Fallback (should rarely happen)
        domain = top_domains[0]
        logger.warning(f"Task '{task.description[:50]}...' classified as '{domain}' (fallback)")
        return domain

    def classify_multi(self, task: Task, top_n: int = 2) -> List[str]:
        """
        Classify task into multiple domains (for multi-domain tasks).

        Args:
            task: Task to classify
            top_n: Number of top domains to return

        Returns:
            List of domain strings, sorted by match count (descending)

        Use case: "Build REST API with React frontend and write tests"
            -> ["backend", "frontend", "testing"]
        """
        description = task.description.lower()

        # Count matches per domain
        match_counts: Dict[str, int] = {domain: 0 for domain in self.DOMAIN_PATTERNS}

        for domain, patterns in self._compiled_patterns.items():
            for pattern in patterns:
                if pattern.search(description):
                    match_counts[domain] += 1

        # Sort by match count (descending)
        sorted_domains = sorted(match_counts.items(), key=lambda x: x[1], reverse=True)

        # Filter out zero matches
        result = [domain for domain, count in sorted_domains if count > 0][:top_n]

        if not result:
            result = ["general"]

        logger.info(
            f"Task '{task.description[:50]}...' multi-classified as {result} "
            f"(match counts: {dict(sorted_domains[:top_n])})"
        )

        return result

    def get_statistics(self, tasks: List[Task]) -> Dict[str, int]:
        """
        Get domain distribution statistics for a batch of tasks.

        Args:
            tasks: List of tasks to analyze

        Returns:
            Dict mapping domain to task count

        Use case: Analyze task distribution across domains for load balancing
        """
        domain_counts: Dict[str, int] = {domain: 0 for domain in self.DOMAIN_PATTERNS}
        domain_counts["general"] = 0

        for task in tasks:
            domain = self.classify(task)
            domain_counts[domain] += 1

        logger.info(f"Domain statistics: {domain_counts}")
        return domain_counts
