"""
Template Loader - Load prompt templates from agentic-prompt-strategy-framework.

Phase 3: Template Library Integration
Clean Architecture: Adapter layer
SOLID: SRP - Single responsibility for template loading
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PromptTemplate:
    """Prompt template loaded from framework."""
    domain: str
    framework: str  # "4-sentence" or "role"
    persona: str
    goal: str
    task: str
    context: str
    file_path: str
    raw_content: str


class TemplateLoader:
    """
    Load prompt templates from agentic-prompt-strategy-framework.
    
    Features:
    - Auto-discover framework path
    - Load domain-specific templates
    - Parse 4-Sentence and ROLE frameworks
    - Cache templates for performance
    
    Usage:
        loader = TemplateLoader()
        template = loader.load_template("backend")
        if template:
            print(f"Loaded: {template.domain}")
    """
    
    def __init__(self, framework_path: Optional[Path] = None):
        """
        Initialize template loader.
        
        Args:
            framework_path: Optional path to framework (auto-detected if None)
        """
        self.framework_path = framework_path or self._detect_framework_path()
        self.templates_cache: Dict[str, PromptTemplate] = {}
        self._load_all_templates()
    
    def _detect_framework_path(self) -> Optional[Path]:
        """
        Auto-detect framework path.
        
        Tries:
        1. Sibling directory: ../agentic-prompt-strategy-framework
        2. Environment variable: ATADO_PROMPT_FRAMEWORK_PATH
        3. Current directory: ./agentic-prompt-strategy-framework
        """
        # Try sibling directory
        sibling = Path(__file__).parent.parent.parent.parent.parent / "agentic-prompt-strategy-framework"
        if sibling.exists() and (sibling / "prompts" / "templates").exists():
            logger.info(f"Framework found at: {sibling}")
            return sibling
        
        # Try environment variable
        import os
        env_path = os.getenv("ATADO_PROMPT_FRAMEWORK_PATH")
        if env_path:
            env_path_obj = Path(env_path)
            if env_path_obj.exists():
                logger.info(f"Framework found via env: {env_path_obj}")
                return env_path_obj
        
        # Try current directory
        current = Path.cwd() / "agentic-prompt-strategy-framework"
        if current.exists():
            logger.info(f"Framework found at: {current}")
            return current
        
        logger.warning("Framework not found, template loading disabled")
        return None
    
    def _load_all_templates(self) -> None:
        """Load all templates from framework."""
        if not self.framework_path:
            return
        
        templates_dir = self.framework_path / "prompts" / "templates"
        if not templates_dir.exists():
            logger.warning(f"Templates directory not found: {templates_dir}")
            return
        
        # Load domain-specific templates
        for template_file in templates_dir.glob("domain-*.md"):
            try:
                domain = template_file.stem.replace("domain-", "")
                template = self._parse_template(template_file, domain)
                if template:
                    self.templates_cache[domain] = template
                    logger.debug(f"Loaded template: {domain}")
            except Exception as e:
                logger.error(f"Failed to load template {template_file}: {e}")
        
        logger.info(f"Loaded {len(self.templates_cache)} templates")
    
    def _parse_template(self, file_path: Path, domain: str) -> Optional[PromptTemplate]:
        """
        Parse template file.
        
        Supports:
        - 4-Sentence Framework (Persona, Goal, Task, Context)
        - ROLE Model (Role, Objective, Logistics, Expectations)
        """
        try:
            content = file_path.read_text(encoding="utf-8")
            
            # Detect framework
            if "## Persona" in content or "**Persona:**" in content:
                framework = "4-sentence"
                return self._parse_4sentence(content, domain, file_path)
            elif "## Role" in content or "**Role:**" in content:
                framework = "role"
                return self._parse_role(content, domain, file_path)
            else:
                logger.warning(f"Unknown framework in {file_path}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to parse template {file_path}: {e}")
            return None
    
    def _parse_4sentence(self, content: str, domain: str, file_path: Path) -> PromptTemplate:
        """Parse 4-Sentence Framework template."""
        lines = content.split("\n")
        
        persona = self._extract_section(lines, ["## Persona", "**Persona:**"])
        goal = self._extract_section(lines, ["## Goal", "**Goal:**"])
        task = self._extract_section(lines, ["## Task", "**Task:**"])
        context = self._extract_section(lines, ["## Context", "**Context:**"])
        
        return PromptTemplate(
            domain=domain,
            framework="4-sentence",
            persona=persona,
            goal=goal,
            task=task,
            context=context,
            file_path=str(file_path),
            raw_content=content
        )
    
    def _parse_role(self, content: str, domain: str, file_path: Path) -> PromptTemplate:
        """Parse ROLE Model template."""
        lines = content.split("\n")
        
        role = self._extract_section(lines, ["## Role", "**Role:**"])
        objective = self._extract_section(lines, ["## Objective", "**Objective:**"])
        logistics = self._extract_section(lines, ["## Logistics", "**Logistics:**"])
        expectations = self._extract_section(lines, ["## Expectations", "**Expectations:**"])
        
        # Map ROLE to 4-Sentence for consistency
        return PromptTemplate(
            domain=domain,
            framework="role",
            persona=role,
            goal=objective,
            task=logistics,  # Logistics → Task
            context=expectations,  # Expectations → Context
            file_path=str(file_path),
            raw_content=content
        )
    
    def _extract_section(self, lines: List[str], headers: List[str]) -> str:
        """Extract section content between headers."""
        content_lines = []
        in_section = False
        
        for line in lines:
            # Check if this is the start of our section
            if any(header in line for header in headers):
                in_section = True
                continue
            
            # Check if this is the start of another section
            if in_section and (line.startswith("## ") or line.startswith("**") and line.endswith(":**")):
                break
            
            # Collect content
            if in_section:
                content_lines.append(line)
        
        # Clean up
        content = "\n".join(content_lines).strip()
        return content if content else "[Template section]"
    
    def load_template(self, domain: str) -> Optional[PromptTemplate]:
        """
        Load template for domain.
        
        Args:
            domain: Domain name (backend, frontend, testing, etc.)
            
        Returns:
            PromptTemplate if found, None otherwise
        """
        return self.templates_cache.get(domain)
    
    def list_domains(self) -> List[str]:
        """List available template domains."""
        return list(self.templates_cache.keys())
    
    def has_template(self, domain: str) -> bool:
        """Check if template exists for domain."""
        return domain in self.templates_cache
    
    def get_template_count(self) -> int:
        """Get number of loaded templates."""
        return len(self.templates_cache)

