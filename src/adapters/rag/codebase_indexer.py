from __future__ import annotations

import ast
import hashlib
import os
from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple

import numpy as np

from .embedding_pipeline import EmbeddingPipeline
from .surrealdb_store import SurrealDBStore


@dataclass
class CodeChunk:
    file_path: str
    language: str
    entity_type: str
    name: str
    qualified_name: str
    start_line: int
    end_line: int
    content: str
    docstring: Optional[str]

    @property
    def content_hash(self) -> str:
        h = hashlib.sha256()
        h.update(self.content.encode("utf-8"))
        if self.docstring:
            h.update(self.docstring.encode("utf-8"))
        return h.hexdigest()


class CodebaseIndexer:
    """Indexes a Python codebase into SurrealDB with embeddings.

    - Walks repo
    - Extracts functions/classes via AST
    - Computes content hashes for incremental updates
    - Stores vectors in SurrealDB
    """

    def __init__(self, db: SurrealDBStore, embedder: EmbeddingPipeline, repo_root: str):
        self.db = db
        self.embedder = embedder
        self.repo_root = os.path.abspath(repo_root)

    def _iter_python_files(self, include: Optional[List[str]] = None, exclude_dirs: Optional[List[str]] = None) -> Iterable[str]:
        exclude_dirs = set(exclude_dirs or [".git", "venv", "node_modules", "__pycache__", ".mypy_cache"])  # noqa
        for root, dirs, files in os.walk(self.repo_root):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            for f in files:
                if f.endswith(".py"):
                    yield os.path.join(root, f)

    def _extract_chunks_py(self, file_path: str) -> List[CodeChunk]:
        rel_path = os.path.relpath(file_path, self.repo_root)
        with open(file_path, "r", encoding="utf-8") as f:
            src = f.read()
        try:
            tree = ast.parse(src)
        except SyntaxError:
            return []

        chunks: List[CodeChunk] = []

        class Visitor(ast.NodeVisitor):
            def __init__(self, outer: 'CodebaseIndexer'):
                self.outer = outer
                self.stack: List[str] = []

            def generic_visit(self, node):
                super().generic_visit(node)

            def visit_FunctionDef(self, node: ast.FunctionDef):
                qname = ".".join(self.stack + [node.name])
                doc = ast.get_docstring(node)
                content = ast.get_source_segment(src, node) or ""
                chunks.append(CodeChunk(
                    file_path=rel_path,
                    language="python",
                    entity_type="function",
                    name=node.name,
                    qualified_name=qname,
                    start_line=node.lineno,
                    end_line=getattr(node, 'end_lineno', node.lineno),
                    content=content,
                    docstring=doc,
                ))
                self.generic_visit(node)

            def visit_ClassDef(self, node: ast.ClassDef):
                qname = ".".join(self.stack + [node.name])
                doc = ast.get_docstring(node)
                content = ast.get_source_segment(src, node) or ""
                chunks.append(CodeChunk(
                    file_path=rel_path,
                    language="python",
                    entity_type="class",
                    name=node.name,
                    qualified_name=qname,
                    start_line=node.lineno,
                    end_line=getattr(node, 'end_lineno', node.lineno),
                    content=content,
                    docstring=doc,
                ))
                self.stack.append(node.name)
                self.generic_visit(node)
                self.stack.pop()

        Visitor(self).visit(tree)
        return chunks

    async def index(self, include: Optional[List[str]] = None, exclude_dirs: Optional[List[str]] = None, batch_size: int = 64) -> int:
        """Index repository into SurrealDB. Returns number of upserts."""
        total = 0
        files = list(self._iter_python_files(include, exclude_dirs))
        for file_path in files:
            chunks = self._extract_chunks_py(file_path)
            if not chunks:
                continue
            # Prepare embeddings text: content + docstring
            texts = [f"{c.content}\n\n{c.docstring or ''}" for c in chunks]
            embs = await self.embedder.embed_texts(texts, batch_size=batch_size)
            for c, e in zip(chunks, embs):
                # Incremental check
                existing = await self.db.get_code_entity_hash(c.file_path, c.name)
                if existing == c.content_hash:
                    continue
                await self.db.upsert_code_entity(
                    file_path=c.file_path,
                    name=c.name,
                    qualified_name=c.qualified_name,
                    language=c.language,
                    entity_type=c.entity_type,
                    start_line=c.start_line,
                    end_line=c.end_line,
                    content=c.content,
                    content_hash=c.content_hash,
                    docstring=c.docstring,
                    tags=None,
                    embedding=e,
                    embedding_model=self.embedder.model_id,
                )
                total += 1
        return total

