#!/usr/bin/env python3
"""
Phase 1 Tool-Use Validation Script

Quick validation that tool-use system is working correctly.
Tests tool registration, ReAct integration, and basic execution.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.adapters.agent.tools.registry import ToolRegistry
from src.adapters.agent.tools.file_reader import FileReaderTool
from src.adapters.agent.tools.bash_executor import BashExecutorTool
from src.adapters.agent.tools.file_writer import FileWriterTool
from src.composition import compose_dependencies
from src.factories.provider_factory import ProviderFactory
from src.factories.agent_factory import AgentFactory


def test_tool_registration():
    """Test 1: Tool registration works"""
    print("=" * 60)
    print("TEST 1: Tool Registration")
    print("=" * 60)

    registry = ToolRegistry()
    registry.register(FileReaderTool())
    registry.register(BashExecutorTool())
    registry.register(FileWriterTool())

    tools = ["read_file", "bash", "write_file"]
    for tool_name in tools:
        tool = registry.get_tool(tool_name)
        assert tool is not None, f"Tool {tool_name} not found"
        print(f"✅ {tool_name}: {tool.description[:50]}...")

    print("\n✅ Tool registration: PASS\n")


def test_tool_descriptions():
    """Test 2: Tool descriptions are formatted for LLM"""
    print("=" * 60)
    print("TEST 2: Tool Descriptions")
    print("=" * 60)

    registry = ToolRegistry()
    registry.register(FileReaderTool())
    registry.register(BashExecutorTool())

    descriptions = registry.get_tool_descriptions()
    assert len(descriptions) > 0, "No tool descriptions generated"
    assert "Tool:" in descriptions, "Missing Tool: prefix"
    assert "Description:" in descriptions, "Missing Description: field"
    assert "Parameters:" in descriptions, "Missing Parameters: field"

    print(descriptions[:300] + "...\n")
    print("✅ Tool descriptions: PASS\n")


def test_composition_integration():
    """Test 3: Composition properly wires tool registry"""
    print("=" * 60)
    print("TEST 3: Composition Integration")
    print("=" * 60)

    provider_factory = ProviderFactory()
    agent_factory = AgentFactory()

    llm_provider = provider_factory.create_provider("mock")
    agents = agent_factory.create_default_agents()

    coordinator, metrics_collector = compose_dependencies(
        llm_provider=llm_provider,
        agents=agents,
        collect_metrics=False
    )

    assert coordinator is not None, "Coordinator not created"
    print("✅ Coordinator created successfully")
    print(f"✅ Agents: {len(agents)}")
    print(f"✅ Metrics collector: {metrics_collector}")
    print("\n✅ Composition integration: PASS\n")


def test_file_reader_tool_execution():
    """Test 4: FileReaderTool can read files"""
    print("=" * 60)
    print("TEST 4: FileReaderTool Execution")
    print("=" * 60)

    tool = FileReaderTool(base_dir=Path(__file__).parent)

    # Read this validation script itself
    result = tool.execute(file_path="validate_phase1_tooluse.py", max_lines=10)

    assert len(result) > 0, "FileReaderTool returned empty result"
    assert "#!/usr/bin/env python3" in result, "File content not read correctly"

    print(f"✅ Read {len(result)} chars from validate_phase1_tooluse.py")
    print(f"✅ First line: {result.split(chr(10))[0][:60]}...")
    print("\n✅ FileReaderTool execution: PASS\n")


def test_bash_executor_tool_execution():
    """Test 5: BashExecutorTool can execute commands"""
    print("=" * 60)
    print("TEST 5: BashExecutorTool Execution")
    print("=" * 60)

    tool = BashExecutorTool()

    # Simple echo command
    result = tool.execute(command="echo 'Phase 1 Tool-Use System Operational'", timeout=5)

    assert len(result) > 0, "BashExecutorTool returned empty result"
    assert "Phase 1" in result or "stdout" in result, "Bash output not captured"

    print(f"✅ Executed bash command successfully")
    print(f"✅ Output: {result[:100]}...")
    print("\n✅ BashExecutorTool execution: PASS\n")


def test_file_writer_tool_execution():
    """Test 6: FileWriterTool can write files"""
    print("=" * 60)
    print("TEST 6: FileWriterTool Execution")
    print("=" * 60)

    import tempfile
    import os

    tool = FileWriterTool()

    # Write to temp file
    temp_file = tempfile.mktemp(suffix=".txt")
    content = "Phase 1 validation test content"

    try:
        result = tool.execute(file_path=temp_file, content=content)

        assert os.path.exists(temp_file), "File was not created"
        assert "Successfully wrote" in result, "Success message not returned"

        # Verify content
        with open(temp_file, 'r') as f:
            written = f.read()
            assert written == content, "Written content doesn't match"

        print(f"✅ Wrote {len(content)} chars to {temp_file}")
        print(f"✅ Content verified: {content}")
        print("\n✅ FileWriterTool execution: PASS\n")

    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)


def main():
    """Run all validation tests"""
    print("\n" + "=" * 60)
    print("PHASE 1 TOOL-USE SYSTEM VALIDATION")
    print("=" * 60 + "\n")

    tests = [
        test_tool_registration,
        test_tool_descriptions,
        test_composition_integration,
        test_file_reader_tool_execution,
        test_bash_executor_tool_execution,
        test_file_writer_tool_execution
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"❌ {test.__name__}: FAILED")
            print(f"   Error: {e}\n")

    print("=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    print(f"✅ Passed: {passed}/{len(tests)}")
    print(f"❌ Failed: {failed}/{len(tests)}")

    if failed == 0:
        print("\n🎉 Phase 1 Tool-Use System: FULLY OPERATIONAL")
        print("=" * 60 + "\n")
        return 0
    else:
        print("\n⚠️  Phase 1 Tool-Use System: ISSUES DETECTED")
        print("=" * 60 + "\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
