import json
import os
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch, MagicMock

# Ensure import path includes hooks directory
import sys
HOOKS_DIR = str((Path.cwd() / ".claude" / "hooks").resolve())
if HOOKS_DIR not in sys.path:
    sys.path.insert(0, HOOKS_DIR)

import delegation_watcher as dw  # type: ignore


class TestDelegationWatcher(TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.work = Path(self.tmp.name)
        (self.work / ".claude").mkdir(parents=True, exist_ok=True)
        self.todo_path = self.work / ".claude" / "todos.json"

    def write_todos(self, items):
        self.todo_path.write_text(json.dumps(items), encoding="utf-8")

    @patch.object(dw, "perform_delegation")
    @patch.object(dw, "compute_score", return_value=9)
    def test_triggers_delegation_for_complex_todo(self, mock_score, mock_delegate):
        self.write_todos([{"id": "1", "content": "Do complex research"}])
        seen = set()
        count = dw.process_todos_once(self.todo_path, seen)
        self.assertEqual(count, 1)
        mock_delegate.assert_called_once()
        # seen should contain key derived from todo
        self.assertTrue(len(seen) == 1)

    @patch.object(dw, "perform_delegation")
    @patch.object(dw, "compute_score", return_value=3)
    def test_no_delegation_for_simple_todo(self, mock_score, mock_delegate):
        self.write_todos([{"id": "s", "content": "Read file"}])
        seen = set()
        count = dw.process_todos_once(self.todo_path, seen)
        self.assertEqual(count, 0)
        mock_delegate.assert_not_called()
        # seen remains empty since nothing delegated
        self.assertEqual(len(seen), 0)

    @patch.object(dw, "perform_delegation")
    @patch.object(dw, "compute_score", return_value=9)
    def test_deduplication_seen_set(self, mock_score, mock_delegate):
        todo = {"id": "dup", "content": "Complex work"}
        self.write_todos([todo])
        seen = set()
        c1 = dw.process_todos_once(self.todo_path, seen)
        c2 = dw.process_todos_once(self.todo_path, seen)
        self.assertEqual(c1, 1)
        self.assertEqual(c2, 0)
        mock_delegate.assert_called_once()

    @patch.object(dw, "perform_delegation")
    @patch.object(dw, "compute_score", return_value=9)
    def test_robust_to_invalid_json_or_shape(self, mock_score, mock_delegate):
        # Invalid JSON
        self.todo_path.write_text("not json", encoding="utf-8")
        seen = set()
        self.assertEqual(dw.process_todos_once(self.todo_path, seen), 0)
        # Not a list
        self.todo_path.write_text(json.dumps({"id": 1}), encoding="utf-8")
        self.assertEqual(dw.process_todos_once(self.todo_path, seen), 0)
        mock_delegate.assert_not_called()

