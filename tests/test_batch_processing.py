import asyncio
import time
from types import SimpleNamespace

import pytest

from src.project_builder.execution.batch_processor import ProjectBatchProcessor, ProjectSpec


@pytest.mark.asyncio
async def test_process_batch_concurrency(monkeypatch):
    # Simulate work taking ~0.2s per project
    async def fake_process(self, spec: ProjectSpec):
        await asyncio.sleep(0.2)
        return SimpleNamespace(success=True, artifacts={}, execution_time=0.2, task_results=[])

    # Patch the internal single-project processor to our fake
    monkeypatch.setattr(ProjectBatchProcessor, "_process_single_project", fake_process)

    processor = ProjectBatchProcessor(max_workers=4)
    specs = [ProjectSpec(goal=f"g{i}", project_id=f"p{i}") for i in range(8)]

    start = time.time()
    results = await processor.process_batch(specs)
    duration = time.time() - start

    assert len(results) == 8
    # With max_workers=4 and per-task ~0.2s, expected wall time ~0.4–0.6s (2 waves)
    assert duration < 0.8, "Batch should complete within concurrency envelope"
