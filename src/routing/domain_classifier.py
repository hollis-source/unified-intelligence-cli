"""
Domain Classifier - Classifies tasks by domain for hierarchical routing.

Clean Architecture: Strategy pattern for domain detection.
Week 11: Part of hierarchical agent scaling infrastructure.
"""

import re
import logging
from typing import Dict, List
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
        ]
    }

    def __init__(self):
        """Initialize domain classifier with compiled regex patterns."""
        # Compile patterns for performance
        self._compiled_patterns: Dict[str, List[re.Pattern]] = {
            domain: [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
            for domain, patterns in self.DOMAIN_PATTERNS.items()
        }

        logger.info(f"DomainClassifier initialized with {len(self.DOMAIN_PATTERNS)} domains")

    def classify(self, task: Task) -> str:
        """
        Classify task into primary domain.

        Args:
            task: Task to classify

        Returns:
            Domain string ("frontend", "backend", "testing", etc.)
            Returns "general" if no specific domain detected

        Strategy:
            - Count pattern matches per domain
            - Return domain with most matches
            - Fallback to "general" for ambiguous tasks
        """
        description = task.description.lower()

        # Count matches per domain
        match_counts: Dict[str, int] = {domain: 0 for domain in self.DOMAIN_PATTERNS}

        for domain, patterns in self._compiled_patterns.items():
            for pattern in patterns:
                if pattern.search(description):
                    match_counts[domain] += 1

        # Find domain with most matches
        max_matches = max(match_counts.values())

        if max_matches == 0:
            # No domain patterns matched
            logger.debug(f"Task '{task.description[:50]}...' classified as 'general' (no patterns)")
            return "general"

        # Get domain(s) with max matches
        top_domains = [domain for domain, count in match_counts.items() if count == max_matches]

        if len(top_domains) == 1:
            domain = top_domains[0]
            logger.info(f"Task '{task.description[:50]}...' classified as '{domain}' ({max_matches} matches)")
            return domain

        # Multiple domains tied - use priority order
        priority_order = ["backend", "frontend", "testing", "devops", "security", "performance", "research", "documentation"]
        for priority_domain in priority_order:
            if priority_domain in top_domains:
                logger.info(
                    f"Task '{task.description[:50]}...' classified as '{priority_domain}' "
                    f"(tie-breaker: {max_matches} matches across {len(top_domains)} domains)"
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
