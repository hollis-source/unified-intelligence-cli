"""
Template domain consistency check.

Validates that all task templates have consistent domain inference that
normalizes to allowed domains. Catches issues like 'test' vs 'testing'
that would cause A/B test measurement problems.
"""

import pytest
import yaml
from pathlib import Path
from typing import List, Tuple, Set

from scripts.build_rag_patterns import TaskTemplate
from scripts.ab_routing_eval import normalize_domain


# Canonical allowed domains (from DomainClassifier + normalized forms)
ALLOWED_DOMAINS = {
    "testing",         # Canonical (DomainClassifier)
    "qa",              # Canonical (DomainClassifier)
    "frontend",        # Canonical (DomainClassifier)
    "backend",         # Canonical (DomainClassifier)
    "devops",          # Canonical (DomainClassifier)
    "research",        # Canonical (DomainClassifier)
    "documentation",   # Canonical (DomainClassifier)
    "security",        # Canonical (DomainClassifier)
    "performance",     # Canonical (DomainClassifier)
    "category-theory", # Canonical (DomainClassifier)
    "dsl",             # Canonical (DomainClassifier)
    "architecture",    # Canonical (from TaskTemplate inference)
    "general",         # Fallback domain
    "unknown",         # Default fallback
}


def scan_all_task_templates() -> List[Tuple[Path, TaskTemplate]]:
    """Scan all task YAML files and create TaskTemplate objects."""
    tasks_dir = Path("tasks")
    templates = []
    
    for yaml_file in tasks_dir.glob("**/*.yaml"):
        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if data:  # Skip empty files
                template = TaskTemplate(yaml_file, data)
                templates.append((yaml_file, template))
        except Exception as e:
            pytest.fail(f"Failed to parse {yaml_file}: {e}")
    
    return templates


def test_all_templates_parse_successfully():
    """Verify all task YAML files can be parsed without errors."""
    templates = scan_all_task_templates()
    
    assert len(templates) > 0, "No task templates found in tasks/"
    assert len(templates) >= 100, f"Expected at least 100 templates, found {len(templates)}"


def test_all_templates_have_valid_domains():
    """
    Verify all templates infer domains that normalize to allowed domains.
    
    This catches issues like:
    - 'test' directory → 'testing' domain (correct)
    - 'test' tag not normalized → would cause A/B test failures
    """
    templates = scan_all_task_templates()
    
    invalid_templates = []
    
    for file_path, template in templates:
        inferred_domain = template.domain
        normalized_domain = normalize_domain(inferred_domain)
        
        if normalized_domain not in ALLOWED_DOMAINS:
            invalid_templates.append({
                'file': str(file_path),
                'inferred': inferred_domain,
                'normalized': normalized_domain,
            })
    
    # Assert with helpful error message
    if invalid_templates:
        error_msg = (
            f"❌ Found {len(invalid_templates)} templates with invalid domains:\n\n"
        )
        for item in invalid_templates[:10]:  # Show first 10
            error_msg += (
                f"  File: {item['file']}\n"
                f"    Inferred: '{item['inferred']}'\n"
                f"    Normalized: '{item['normalized']}'\n"
                f"    Issue: Not in allowed domains\n\n"
            )
        
        if len(invalid_templates) > 10:
            error_msg += f"  ... and {len(invalid_templates) - 10} more\n\n"
        
        error_msg += (
            f"Allowed domains:\n  {sorted(ALLOWED_DOMAINS)}\n\n"
            f"Action: Either:\n"
            f"  1. Add missing domain to ALLOWED_DOMAINS in this test\n"
            f"  2. Add normalization rule to scripts/ab_routing_eval.py:normalize_domain()\n"
            f"  3. Fix directory/tag names in problematic templates"
        )
        
        pytest.fail(error_msg)


def test_test_directory_normalizes_to_testing():
    """
    Specific test: tasks/test/ files should normalize to 'testing'.
    
    This is the critical A/B test issue that caused 0% accuracy.
    """
    templates = scan_all_task_templates()
    
    test_dir_templates = [
        (fp, tmpl) for fp, tmpl in templates
        if 'tasks/test/' in str(fp)
    ]
    
    if not test_dir_templates:
        pytest.skip("No templates found in tasks/test/ directory")
    
    for file_path, template in test_dir_templates:
        inferred = template.domain
        normalized = normalize_domain(inferred)
        
        assert normalized == "testing", (
            f"File {file_path}:\n"
            f"  Inferred domain: '{inferred}'\n"
            f"  Normalized: '{normalized}'\n"
            f"  Expected: 'testing'\n\n"
            f"This would cause A/B test measurement errors!"
        )


def test_no_unnormalized_test_domains():
    """
    Ensure no templates have 'test' or 'tests' as their normalized domain.
    
    These should always normalize to 'testing'.
    """
    templates = scan_all_task_templates()
    
    problematic = []
    
    for file_path, template in templates:
        inferred = template.domain
        normalized = normalize_domain(inferred)
        
        if normalized in ['test', 'tests']:
            problematic.append((str(file_path), inferred, normalized))
    
    assert not problematic, (
        f"❌ Found templates with unnormalized 'test'/'tests' domains:\n" +
        "\n".join([
            f"  {fp}: inferred='{inf}', normalized='{norm}'"
            for fp, inf, norm in problematic
        ]) +
        "\n\nThese should normalize to 'testing'!"
    )


def test_domain_distribution_is_reasonable():
    """
    Sanity check: Verify domain distribution isn't heavily skewed.
    
    This catches bulk misconfiguration (e.g., all files inferring 'unknown').
    """
    templates = scan_all_task_templates()
    
    domain_counts = {}
    for _, template in templates:
        normalized = normalize_domain(template.domain)
        domain_counts[normalized] = domain_counts.get(normalized, 0) + 1
    
    total = len(templates)
    unknown_count = domain_counts.get('unknown', 0)
    unknown_percentage = (unknown_count / total) * 100 if total > 0 else 0
    
    # Fail if more than 20% are 'unknown' (suggests inference issues)
    assert unknown_percentage < 20, (
        f"⚠️ {unknown_percentage:.1f}% of templates have 'unknown' domain!\n"
        f"  Unknown: {unknown_count}/{total}\n"
        f"  Distribution: {dict(sorted(domain_counts.items(), key=lambda x: x[1], reverse=True))}\n\n"
        f"This suggests domain inference issues. Check:\n"
        f"  1. TaskTemplate._infer_domain() path/tag matching\n"
        f"  2. Directory naming conventions\n"
        f"  3. Metadata tags in YAML files"
    )


def test_each_domain_has_at_least_one_template():
    """
    Verify major domains have at least one template.
    
    Ensures test/validation coverage for all routing paths.
    """
    templates = scan_all_task_templates()
    
    domain_counts = {}
    for _, template in templates:
        normalized = normalize_domain(template.domain)
        domain_counts[normalized] = domain_counts.get(normalized, 0) + 1
    
    # Major domains that should have templates
    major_domains = {
        'testing', 'qa', 'frontend', 'backend', 'devops', 'research'
    }
    
    missing = []
    for domain in major_domains:
        if domain not in domain_counts or domain_counts[domain] == 0:
            missing.append(domain)
    
    assert not missing, (
        f"⚠️ Major domains have no templates: {missing}\n"
        f"  Current distribution: {dict(sorted(domain_counts.items(), key=lambda x: x[1], reverse=True))}\n\n"
        f"Add templates for missing domains to ensure routing coverage."
    )


def test_directory_names_match_expected_domains():
    """
    Verify directory names align with expected domain inference.
    
    Expected mappings:
    - tasks/test/, tasks/testing/ → testing
    - tasks/qa/ → qa
    - tasks/frontend/ → frontend
    - tasks/backend/, tasks/database/, tasks/python/ → backend
    - tasks/devops/ → devops
    - tasks/research/ → research
    - tasks/architect/ → architecture
    """
    expected_dir_to_domain = {
        'test': 'testing',
        'testing': 'testing',
        'qa': 'qa',
        'frontend': 'frontend',
        'backend': 'backend',
        'database': 'backend',
        'python': 'backend',
        'devops': 'devops',
        'research': 'research',
        'architect': 'architecture',
    }
    
    templates = scan_all_task_templates()
    
    mismatches = []
    
    for file_path, template in templates:
        # Extract directory name from path
        parts = file_path.parts
        if len(parts) >= 2 and parts[0] == 'tasks':
            dir_name = parts[1]
            
            if dir_name in expected_dir_to_domain:
                expected_domain = expected_dir_to_domain[dir_name]
                normalized = normalize_domain(template.domain)
                
                if normalized != expected_domain:
                    mismatches.append({
                        'file': str(file_path),
                        'directory': dir_name,
                        'expected': expected_domain,
                        'actual': normalized,
                    })
    
    if mismatches:
        error_msg = (
            f"❌ Found {len(mismatches)} directory/domain mismatches:\n\n"
        )
        for item in mismatches[:5]:  # Show first 5
            error_msg += (
                f"  {item['file']}\n"
                f"    Directory: {item['directory']}/\n"
                f"    Expected domain: {item['expected']}\n"
                f"    Actual domain: {item['actual']}\n\n"
            )
        
        if len(mismatches) > 5:
            error_msg += f"  ... and {len(mismatches) - 5} more\n"
        
        pytest.fail(error_msg)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
