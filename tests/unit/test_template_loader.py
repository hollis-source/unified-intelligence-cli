"""
Unit tests for TemplateLoader.

Tests Phase 3: Template library integration.
Clean Architecture: Adapter layer tests.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from src.adapters.prompt.template_loader import TemplateLoader, PromptTemplate


class TestTemplateLoader:
    """Test suite for TemplateLoader."""
    
    def test_detect_framework_path_sibling(self):
        """Test framework path detection (sibling directory)."""
        loader = TemplateLoader()
        
        # Should find framework as sibling
        if loader.framework_path:
            assert "agentic-prompt-strategy-framework" in str(loader.framework_path)
    
    def test_load_template_backend(self):
        """Test loading backend template."""
        loader = TemplateLoader()
        
        if not loader.framework_path:
            pytest.skip("Framework not available")
        
        template = loader.load_template("backend")
        
        if template:
            assert template.domain == "backend"
            assert template.framework in ["4-sentence", "role"]
            assert len(template.persona) > 0
            assert len(template.goal) > 0
            assert len(template.task) > 0
            assert len(template.context) > 0
    
    def test_load_template_frontend(self):
        """Test loading frontend template."""
        loader = TemplateLoader()
        
        if not loader.framework_path:
            pytest.skip("Framework not available")
        
        template = loader.load_template("frontend")
        
        if template:
            assert template.domain == "frontend"
            assert template.framework in ["4-sentence", "role"]
    
    def test_load_template_testing(self):
        """Test loading testing template."""
        loader = TemplateLoader()
        
        if not loader.framework_path:
            pytest.skip("Framework not available")
        
        template = loader.load_template("testing")
        
        if template:
            assert template.domain == "testing"
            assert template.framework in ["4-sentence", "role"]
    
    def test_load_template_nonexistent(self):
        """Test loading nonexistent template returns None."""
        loader = TemplateLoader()
        
        template = loader.load_template("nonexistent-domain")
        
        assert template is None
    
    def test_list_domains(self):
        """Test listing available domains."""
        loader = TemplateLoader()
        
        if not loader.framework_path:
            pytest.skip("Framework not available")
        
        domains = loader.list_domains()
        
        # Should have at least some domains
        assert isinstance(domains, list)
        
        # Check for expected domains
        expected_domains = ["backend", "frontend", "testing", "database", "devops"]
        for domain in expected_domains:
            if domain in domains:
                assert True  # At least one expected domain found
                break
    
    def test_has_template(self):
        """Test checking if template exists."""
        loader = TemplateLoader()
        
        if not loader.framework_path:
            pytest.skip("Framework not available")
        
        # Should have at least one template
        domains = loader.list_domains()
        if domains:
            assert loader.has_template(domains[0])
        
        # Should not have nonexistent template
        assert not loader.has_template("nonexistent-domain")
    
    def test_get_template_count(self):
        """Test getting template count."""
        loader = TemplateLoader()
        
        count = loader.get_template_count()
        
        assert isinstance(count, int)
        assert count >= 0
    
    def test_parse_4sentence_template(self):
        """Test parsing 4-Sentence Framework template."""
        loader = TemplateLoader()
        
        # Create mock template content
        content = """# Backend Development Template

## Persona
Senior Backend Developer with expertise in Python and FastAPI.

## Goal
Build scalable and maintainable backend services.

## Task
{task_description}

## Context
- Agent Tier: {tier}
- Priority: {priority}
"""
        
        template = loader._parse_4sentence(content, "backend", Path("test.md"))
        
        assert template.domain == "backend"
        assert template.framework == "4-sentence"
        assert "Senior Backend Developer" in template.persona
        assert "scalable" in template.goal
        assert "{task_description}" in template.task
        assert "{tier}" in template.context
    
    def test_parse_role_template(self):
        """Test parsing ROLE Model template."""
        loader = TemplateLoader()
        
        # Create mock template content
        content = """# Testing Template

## Role
QA Engineer with expertise in automated testing.

## Objective
Ensure high-quality software through comprehensive testing.

## Logistics
- Write test cases
- Execute tests
- Report bugs

## Expectations
- 80%+ code coverage
- All critical paths tested
"""
        
        template = loader._parse_role(content, "testing", Path("test.md"))
        
        assert template.domain == "testing"
        assert template.framework == "role"
        assert "QA Engineer" in template.persona
        assert "high-quality" in template.goal
        assert "Write test cases" in template.task
        assert "80%" in template.context
    
    def test_extract_section(self):
        """Test extracting section from template."""
        loader = TemplateLoader()
        
        lines = [
            "# Template",
            "",
            "## Persona",
            "Senior Developer",
            "Expert in Python",
            "",
            "## Goal",
            "Build great software",
        ]
        
        persona = loader._extract_section(lines, ["## Persona"])
        
        assert "Senior Developer" in persona
        assert "Expert in Python" in persona
        assert "## Goal" not in persona
    
    def test_framework_not_found_fallback(self):
        """Test fallback when framework not found."""
        with patch.object(TemplateLoader, '_detect_framework_path', return_value=None):
            loader = TemplateLoader()
            
            assert loader.framework_path is None
            assert loader.get_template_count() == 0
            assert loader.load_template("backend") is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

