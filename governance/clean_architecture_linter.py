from __future__ import annotations
import ast
from dataclasses import dataclass
from typing import List, Iterable
import argparse
import sys


@dataclass
class Violation:
    file: str
    line: int
    rule: str
    message: str


def _end_lineno(node: ast.AST) -> int:
    end = getattr(node, "end_lineno", None)
    if end is not None:
        return int(end)
    body = getattr(node, "body", []) or []
    last = body[-1] if body else node
    while hasattr(last, "body") and getattr(last, "body", []):
        last = getattr(last, "body")[-1]
    return int(getattr(last, "end_lineno", getattr(last, "lineno", 0)))


def _check_function_lengths(tree: ast.AST, filename: str, max_len: int) -> List[Violation]:
    v: List[Violation] = []
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            length = _end_lineno(n) - int(n.lineno) + 1
            if length > max_len:
                v.append(
                    Violation(
                        file=filename,
                        line=int(n.lineno),
                        rule="FUNC_LEN",
                        message=f"Function '{n.name}' has {length} lines (>{max_len}).",
                    )
                )
    return v


def check_source(source: str, filename: str = "<memory>", max_len: int = 20) -> List[Violation]:
    tree = ast.parse(source)
    return _check_function_lengths(tree, filename, max_len)


def _iter_py_files(paths: Iterable[str]) -> Iterable[str]:
    for p in paths:
        if p.endswith(".py"):
            yield p


def check_files(files: Iterable[str], max_len: int = 20) -> List[Violation]:
    out: List[Violation] = []
    for f in _iter_py_files(files):
        try:
            with open(f, "r", encoding="utf-8") as fh:
                src = fh.read()
        except FileNotFoundError:
            continue
        out.extend(check_source(src, f, max_len))
    return out


def _parse_args(argv: List[str]) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Clean Architecture linter")
    ap.add_argument("--files", nargs="*", default=[], help="Python files to check")
    ap.add_argument("--max-len", type=int, default=20, help="Max function length")
    return ap.parse_args(argv)


def main(argv: List[str] | None = None) -> int:
    ns = _parse_args(argv or sys.argv[1:])
    violations = check_files(ns.files, max_len=ns.max_len)
    for v in violations:
        print(f"{v.file}:{v.line}: {v.rule}: {v.message}")
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())

