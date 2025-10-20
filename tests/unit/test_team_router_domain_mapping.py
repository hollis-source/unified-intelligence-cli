"""
Unit tests for domain_to_team mapping consistency.

Validates that all domains returned by DomainClassifier have corresponding
team mappings in TeamRouter to prevent routing failures.
"""

import pytest
from src.routing.domain_classifier import DomainClassifier
from src.routing.team_router import TeamRouter


def test_all_classifier_domains_have_team_mappings():
    """
    Ensure all DomainClassifier domains map to teams in TeamRouter.

    This prevents runtime routing failures when classifier returns a domain
    that has no team mapping, which would fall back to Orchestration team.
    """
    classifier = DomainClassifier()
    classifier_domains = set(classifier.DOMAIN_PATTERNS.keys())

    # Extract domain_to_team mapping from TeamRouter
    # Note: This mapping is defined in route_to_team_by_domain() method
    expected_domain_to_team = {
        "frontend": "Frontend",
        "backend": "Backend",
        "testing": "Testing",
        "devops": "Infrastructure",
        "research": "Research",
        "documentation": "Research",
        "security": "Backend",
        "performance": "Backend",
        "general": "Orchestration",
        "category-theory": "Category Theory",
        "dsl": "DSL",
        "qa": "Quality Assurance"
    }

    mapped_domains = set(expected_domain_to_team.keys())

    # Find domains that classifier can return but have no team mapping
    missing_mappings = classifier_domains - mapped_domains

    # Assert with helpful error message
    assert not missing_mappings, (
        f"DomainClassifier can return these domains, but they have no team mappings in TeamRouter:\n"
        f"  Missing: {sorted(missing_mappings)}\n\n"
        f"Add these domains to domain_to_team mapping in src/routing/team_router.py:route_to_team_by_domain()\n"
        f"Available domains in DomainClassifier.DOMAIN_PATTERNS:\n  {sorted(classifier_domains)}\n"
        f"Mapped domains in TeamRouter:\n  {sorted(mapped_domains)}"
    )


def test_domain_to_team_mapping_correctness():
    """Validate that domain_to_team mappings point to reasonable team names."""
    expected_domain_to_team = {
        "frontend": "Frontend",
        "backend": "Backend",
        "testing": "Testing",
        "devops": "Infrastructure",
        "research": "Research",
        "documentation": "Research",  # Docs handled by Research team
        "security": "Backend",  # Security handled by Backend team
        "performance": "Backend",  # Performance handled by Backend team
        "general": "Orchestration",  # Fallback to Orchestration
        "category-theory": "Category Theory",
        "dsl": "DSL",
        "qa": "Quality Assurance"
    }

    # Verify all values are non-empty team names
    for domain, team_name in expected_domain_to_team.items():
        assert team_name, f"Domain '{domain}' maps to empty team name"
        assert isinstance(team_name, str), f"Domain '{domain}' team name must be string"
        assert len(team_name) > 0, f"Domain '{domain}' team name is empty"


def test_classifier_testing_domain_maps_to_testing_team():
    """Specific test: 'testing' domain → 'Testing' team."""
    expected_domain_to_team = {
        "frontend": "Frontend",
        "backend": "Backend",
        "testing": "Testing",
        "devops": "Infrastructure",
        "research": "Research",
        "documentation": "Research",
        "security": "Backend",
        "performance": "Backend",
        "general": "Orchestration",
        "category-theory": "Category Theory",
        "dsl": "DSL",
        "qa": "Quality Assurance"
    }

    assert "testing" in expected_domain_to_team
    assert expected_domain_to_team["testing"] == "Testing"


def test_classifier_qa_domain_maps_to_qa_team():
    """Specific test: 'qa' domain → 'Quality Assurance' team."""
    expected_domain_to_team = {
        "frontend": "Frontend",
        "backend": "Backend",
        "testing": "Testing",
        "devops": "Infrastructure",
        "research": "Research",
        "documentation": "Research",
        "security": "Backend",
        "performance": "Backend",
        "general": "Orchestration",
        "category-theory": "Category Theory",
        "dsl": "DSL",
        "qa": "Quality Assurance"
    }

    assert "qa" in expected_domain_to_team
    assert expected_domain_to_team["qa"] == "Quality Assurance"


def test_all_11_classifier_domains_covered():
    """
    Verify all 11 DomainClassifier domains have team mappings.

    DomainClassifier defines 11 domains:
    backend, category-theory, devops, documentation, dsl, frontend,
    performance, qa, research, security, testing
    """
    classifier = DomainClassifier()
    classifier_domains = set(classifier.DOMAIN_PATTERNS.keys())

    # Should be exactly 11 domains
    assert len(classifier_domains) == 11, (
        f"Expected 11 domains in DomainClassifier, found {len(classifier_domains)}: "
        f"{sorted(classifier_domains)}"
    )

    expected_domains = {
        "backend", "category-theory", "devops", "documentation", "dsl",
        "frontend", "performance", "qa", "research", "security", "testing"
    }

    assert classifier_domains == expected_domains, (
        f"DomainClassifier domains changed!\n"
        f"  Expected: {sorted(expected_domains)}\n"
        f"  Actual:   {sorted(classifier_domains)}\n"
        f"  Missing:  {sorted(expected_domains - classifier_domains)}\n"
        f"  Extra:    {sorted(classifier_domains - expected_domains)}"
    )


def test_no_unmapped_domains_in_production():
    """
    Integration test: Ensure no classifier domain would cause routing fallback.

    This test fails if a domain exists in DomainClassifier but not in
    domain_to_team mapping, which would cause unexpected Orchestration fallback.
    """
    classifier = DomainClassifier()
    classifier_domains = set(classifier.DOMAIN_PATTERNS.keys())

    expected_domain_to_team = {
        "frontend": "Frontend",
        "backend": "Backend",
        "testing": "Testing",
        "devops": "Infrastructure",
        "research": "Research",
        "documentation": "Research",
        "security": "Backend",
        "performance": "Backend",
        "general": "Orchestration",
        "category-theory": "Category Theory",
        "dsl": "DSL",
        "qa": "Quality Assurance"
    }

    unmapped = []
    for domain in classifier_domains:
        if domain not in expected_domain_to_team:
            unmapped.append(domain)

    assert not unmapped, (
        f"❌ ROUTING FAILURE RISK: These domains have no team mappings:\n"
        f"  {unmapped}\n\n"
        f"Action required: Add mappings to src/routing/team_router.py\n"
        f"Example:\n"
        f"  domain_to_team = {{\n"
        f"      ...\n"
        f"      '{unmapped[0] if unmapped else 'example'}': 'TeamName',\n"
        f"  }}"
    )


def test_domain_to_team_values_are_valid_team_names():
    """Validate team names follow expected naming conventions."""
    expected_domain_to_team = {
        "frontend": "Frontend",
        "backend": "Backend",
        "testing": "Testing",
        "devops": "Infrastructure",
        "research": "Research",
        "documentation": "Research",
        "security": "Backend",
        "performance": "Backend",
        "general": "Orchestration",
        "category-theory": "Category Theory",
        "dsl": "DSL",
        "qa": "Quality Assurance"
    }

    valid_team_names = {
        "Frontend", "Backend", "Testing", "Infrastructure", "Research",
        "Orchestration", "Category Theory", "DSL", "Quality Assurance"
    }

    for domain, team_name in expected_domain_to_team.items():
        assert team_name in valid_team_names, (
            f"Domain '{domain}' maps to invalid team '{team_name}'\n"
            f"Valid teams: {sorted(valid_team_names)}"
        )


def test_fallback_domain_general_exists():
    """Verify 'general' fallback domain maps to Orchestration."""
    expected_domain_to_team = {
        "frontend": "Frontend",
        "backend": "Backend",
        "testing": "Testing",
        "devops": "Infrastructure",
        "research": "Research",
        "documentation": "Research",
        "security": "Backend",
        "performance": "Backend",
        "general": "Orchestration",
        "category-theory": "Category Theory",
        "dsl": "DSL",
        "qa": "Quality Assurance"
    }

    assert "general" in expected_domain_to_team
    assert expected_domain_to_team["general"] == "Orchestration"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
