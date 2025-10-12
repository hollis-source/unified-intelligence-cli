from importlib.machinery import SourceFileLoader


def load_autocommit_module():
    return SourceFileLoader("autocommit_post", ".claude/hooks/autocommit_post.py").load_module()


def test_extract_file_paths_write_tool():
    mod = load_autocommit_module()
    payload = {"tool_input": {"file_path": "foo/bar.py"}}
    assert mod.extract_file_paths(payload) == ["foo/bar.py"]


def test_extract_file_paths_multiedit_tool():
    mod = load_autocommit_module()
    payload = {"tool_input": {"edits": [{"file_path": "a.py"}, {"file_path": "b.py"}]}}
    assert sorted(mod.extract_file_paths(payload)) == ["a.py", "b.py"]


def test_extract_file_paths_top_level_fallbacks():
    mod = load_autocommit_module()
    # Top-level file_path
    payload1 = {"file_path": "x.py"}
    # Top-level edits
    payload2 = {"edits": [{"file_path": "c.py"}]}
    # Alternate key 'path'
    payload3 = {"tool_input": {"path": "d.py"}}
    # Alternate key 'new_file_path'
    payload4 = {"tool_input": {"new_file_path": "e.py"}}

    assert mod.extract_file_paths(payload1) == ["x.py"]
    assert mod.extract_file_paths(payload2) == ["c.py"]
    assert mod.extract_file_paths(payload3) == ["d.py"]
    assert mod.extract_file_paths(payload4) == ["e.py"]

