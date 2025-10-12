# FileStore Architecture Plan - Remote File Access Integration

**Date**: 2025-10-07
**Designed by**: Auggie (GPT-5)
**Status**: Architecture approved, awaiting implementation
**Context**: SSH remote file access (ParamikoSSHAdapter) built but not integrated

---

## Problem Statement

ParamikoSSHAdapter works perfectly (SSH connectivity validated), but Project Builder doesn't use it. Tasks fail because they expect local files and have no mechanism to fetch from remote servers.

**Current State**: `remote_fs` injected into ExecutionCoordinator but sits unused.

---

## Solution: Port-and-Adapter with FileStore

### Core Concept

**IFileStore Port** (use case layer) + **UnifiedFileStore Adapter** (infrastructure)

Tasks reference files via **FileRef** URIs:
- `file:///local/path/file.py` → local filesystem
- `ssh://host/opt/app/file.py` → SSH via Paramiko
- `s3://bucket/key.py` → S3 (future)

**ResourceResolver** ensures file content is loaded into **world_state** before task execution.

---

## Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│ CLI Layer                                                   │
│   - Builds UnifiedFileStore with backends                   │
│   - Injects file_store into ExecutionCoordinator            │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ Use Case Layer                                              │
│   - IFileStore (port/interface)                             │
│   - ResourceResolver (ensures task inputs in world_state)   │
│   - ExecutionCoordinator (orchestrates resource loading)    │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ Infrastructure/Adapter Layer                                │
│   - UnifiedFileStore (routes by FileRef scheme)             │
│   - SSHBackend (wraps ParamikoSSHAdapter)                   │
│   - LocalBackend (wraps os.path/pathlib)                    │
│   - S3Backend (future)                                      │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Abstractions

### 1. FileRef (Entity/Value Object)

```python
@dataclass(frozen=True)
class FileRef:
    """Normalized file identifier with scheme/host/path."""
    scheme: str  # "file", "ssh", "s3", "github"
    host: Optional[str]  # "syd2.jacobhollis.com" for SSH, None for local
    path: str  # "/opt/grokmonster/db_status.py"

    @classmethod
    def parse(cls, uri: str) -> 'FileRef':
        """Parse URI like ssh://host/path or file:///path"""
        ...

    def to_uri(self) -> str:
        """Convert back to URI string"""
        ...
```

**Examples**:
- `FileRef("file", None, "/home/user/app.py")`
- `FileRef("ssh", "syd2.jacobhollis.com", "/opt/grokmonster/db_status.py")`

### 2. IFileStore (Port/Interface - Use Case Layer)

```python
class IFileStore(ABC):
    """Port for all file operations. Use cases depend on this abstraction."""

    @abstractmethod
    async def read(self, ref: FileRef) -> str:
        """Read file content."""
        pass

    @abstractmethod
    async def write(self, ref: FileRef, content: str) -> None:
        """Write content to file."""
        pass

    @abstractmethod
    async def exists(self, ref: FileRef) -> bool:
        """Check if file exists."""
        pass

    @abstractmethod
    async def list_dir(self, ref: FileRef) -> List[FileRef]:
        """List directory contents."""
        pass
```

**Location**: `src/core/ports/file_store.py`

### 3. IFileBackend (Infrastructure Interface)

```python
class IFileBackend(ABC):
    """Backend for a specific file transport (local, SSH, S3, etc.)"""

    @abstractmethod
    def supports(self, ref: FileRef) -> bool:
        """Check if this backend handles this FileRef."""
        pass

    @abstractmethod
    async def read(self, ref: FileRef) -> str:
        pass

    @abstractmethod
    async def write(self, ref: FileRef, content: str) -> None:
        pass

    @abstractmethod
    async def exists(self, ref: FileRef) -> bool:
        pass
```

### 4. UnifiedFileStore (Adapter - Infrastructure Layer)

```python
class UnifiedFileStore(IFileStore):
    """Routes file operations to appropriate backend based on FileRef scheme."""

    def __init__(self, backends: List[IFileBackend]):
        self.backends = backends

    def _get_backend(self, ref: FileRef) -> IFileBackend:
        """Select backend that supports this FileRef."""
        for backend in self.backends:
            if backend.supports(ref):
                return backend
        raise ValueError(f"No backend supports {ref}")

    async def read(self, ref: FileRef) -> str:
        backend = self._get_backend(ref)
        return await backend.read(ref)

    # ... other methods delegate similarly
```

**Location**: `src/adapters/files/unified_file_store.py`

### 5. SSHBackend (Adapts Paramiko)

```python
class SSHBackend(IFileBackend):
    """SSH backend wrapping ParamikoSSHAdapter."""

    def __init__(self, ssh_adapter: ParamikoSSHAdapter):
        self.ssh = ssh_adapter

    def supports(self, ref: FileRef) -> bool:
        return ref.scheme == "ssh"

    async def read(self, ref: FileRef) -> str:
        return await self.ssh.read_file(ref.host, ref.path)

    async def write(self, ref: FileRef, content: str) -> None:
        await self.ssh.write_file(ref.host, ref.path, content)

    async def exists(self, ref: FileRef) -> bool:
        info = await self.ssh.file_exists(ref.host, ref.path)
        return info.exists
```

**Location**: `src/adapters/files/ssh_backend.py`

### 6. LocalBackend

```python
class LocalBackend(IFileBackend):
    """Local filesystem backend."""

    def supports(self, ref: FileRef) -> bool:
        return ref.scheme == "file"

    async def read(self, ref: FileRef) -> str:
        return await asyncio.to_thread(Path(ref.path).read_text)

    async def write(self, ref: FileRef, content: str) -> None:
        await asyncio.to_thread(Path(ref.path).write_text, content)

    async def exists(self, ref: FileRef) -> bool:
        return await asyncio.to_thread(Path(ref.path).exists)
```

**Location**: `src/adapters/files/local_backend.py`

---

## Resource Resolution

### FileSnapshot (World State)

```python
@dataclass
class FileSnapshot:
    """Snapshot of file content in world state."""
    ref: FileRef
    content: str
    checksum: str  # MD5/SHA256 for consistency checks
    fetched_at: datetime
    dirty: bool = False  # True if modified, needs write-back
```

### ResourceResolver (Use Case Layer)

```python
class ResourceResolver:
    """Ensures task resource inputs are loaded into world_state."""

    def __init__(self, file_store: IFileStore):
        self.file_store = file_store

    async def ensure_inputs(
        self,
        refs: List[FileRef],
        world_state: WorldState
    ) -> None:
        """Load file content for all refs not already in world_state."""
        for ref in refs:
            if not world_state.has_file(ref):
                content = await self.file_store.read(ref)
                checksum = hashlib.md5(content.encode()).hexdigest()
                snapshot = FileSnapshot(
                    ref=ref,
                    content=content,
                    checksum=checksum,
                    fetched_at=datetime.now()
                )
                world_state.put_file_snapshot(snapshot)

    async def persist_outputs(
        self,
        refs: List[FileRef],
        world_state: WorldState
    ) -> None:
        """Write back modified files from world_state."""
        for ref in refs:
            snapshot = world_state.get_file_snapshot(ref)
            if snapshot and snapshot.dirty:
                await self.file_store.write(ref, snapshot.content)
                snapshot.dirty = False
```

**Location**: `src/project_builder/execution/resource_resolver.py`

---

## Integration Points

### 1. ExecutionCoordinator

```python
class ExecutionCoordinator(IExecutionCoordinator):
    def __init__(
        self,
        team_router: TeamRouter,
        model_selector: AdaptiveModelSelector,
        teams: List[AgentTeam],
        llm_provider: Optional[ITextGenerator] = None,
        prompt_mode: str = "manual",
        file_store: Optional[IFileStore] = None  # ← NEW
    ):
        self.team_router = team_router
        self.model_selector = model_selector
        self.teams = teams
        self.llm_provider = llm_provider
        self.file_store = file_store

        # Create resource resolver if file_store provided
        if file_store:
            self.resource_resolver = ResourceResolver(file_store)
        else:
            self.resource_resolver = None

    async def execute_task(self, task: Task, state: ProjectState) -> ExecutionResult:
        """Execute single task with resource resolution."""

        # 1. Resolve input resources (load remote files)
        if self.resource_resolver and task.resource_inputs:
            await self.resource_resolver.ensure_inputs(
                task.resource_inputs,
                state.world_state
            )

        # 2. Execute task via agent (content now in world_state)
        result = await self.llm_executor.execute(agent, task, state.world_state)

        # 3. Persist output resources (write back if needed)
        if self.resource_resolver and task.resource_outputs:
            await self.resource_resolver.persist_outputs(
                task.resource_outputs,
                state.world_state
            )

        return result
```

**Changes**: `src/project_builder/execution/coordinator.py`

### 2. HTN Task Metadata

Tasks need to declare resource dependencies:

```python
@dataclass
class Task:
    task_id: str
    description: str
    # ... existing fields
    resource_inputs: List[FileRef] = field(default_factory=list)  # ← NEW
    resource_outputs: List[FileRef] = field(default_factory=list)  # ← NEW
```

**Changes**: `src/entities/task.py`

### 3. HTN-DSL Translator

Translate paths to FileRefs based on CLI context:

```python
class HTNDSLTranslator:
    def __init__(
        self,
        enable_parallel: bool = True,
        default_remote_host: Optional[str] = None  # ← NEW
    ):
        self.enable_parallel = enable_parallel
        self.default_remote_host = default_remote_host

    def _extract_file_refs(self, task_description: str) -> List[FileRef]:
        """Extract file paths from task description and convert to FileRefs."""
        paths = self._parse_paths(task_description)
        refs = []

        for path in paths:
            if path.startswith("ssh://"):
                refs.append(FileRef.parse(path))
            elif self.default_remote_host:
                # Convert plain path to SSH FileRef using CLI's --remote-host
                refs.append(FileRef("ssh", self.default_remote_host, path))
            else:
                # Local file
                refs.append(FileRef("file", None, path))

        return refs

    def translate(self, htn_root: HTNNode) -> ASTNode:
        """Translate HTN to DSL, adding FileRefs to tasks."""
        # ... existing translation logic

        # Add resource_inputs to tasks based on descriptions
        for task in all_tasks:
            task.resource_inputs = self._extract_file_refs(task.description)

        return dsl_workflow
```

**Changes**: `src/project_builder/htn/translator.py`

### 4. CLI Composition

```python
async def _execute_project(..., remote_host: str, ...):
    # ... existing setup

    # Create file store with backends
    backends = []

    # Always include local backend
    backends.append(LocalBackend())

    # Add SSH backend if remote host specified
    if remote_host:
        ssh_adapter = create_paramiko_ssh_adapter(default_host=remote_host)
        await ssh_adapter.connect()
        backends.append(SSHBackend(ssh_adapter))

    file_store = UnifiedFileStore(backends)

    # Create translator with remote context
    htn_dsl_translator = HTNDSLTranslator(
        enable_parallel=parallel,
        default_remote_host=remote_host  # ← NEW
    )

    # Create coordinator with file store
    execution_coordinator = ExecutionCoordinator(
        team_router=team_router,
        model_selector=model_selector,
        teams=teams,
        llm_provider=llm_provider,
        prompt_mode=prompt_mode,
        file_store=file_store  # ← NEW
    )
```

**Changes**: `src/project_builder/cli/command.py`

---

## How This Fixes Current Failure

**Current Flow** (broken):
```
1. Goal: "Read /opt/grokmonster/db_status.py from remote server..."
2. GoalDecomposer creates tasks with preconditions
3. Tasks fail: "server_connection_established" = False
4. Nothing fetches the file
```

**New Flow** (fixed):
```
1. Goal: "Read /opt/grokmonster/db_status.py from remote server..."
2. GoalDecomposer creates tasks
3. HTN-DSL Translator:
   - Extracts path: "/opt/grokmonster/db_status.py"
   - Converts to FileRef("ssh", "syd2.jacobhollis.com", "/opt/grokmonster/db_status.py")
   - Adds to task.resource_inputs
4. ExecutionCoordinator.execute_task():
   - Calls ResourceResolver.ensure_inputs()
   - FileStore.read(FileRef) → UnifiedFileStore → SSHBackend → ParamikoSSHAdapter
   - Content loaded into world_state
   - Precondition satisfied: "file_content_available" = True
5. LLMAgentExecutor:
   - Reads content from world_state
   - Processes with LLM
   - Writes result to world_state
6. ExecutionCoordinator.execute_task():
   - Calls ResourceResolver.persist_outputs()
   - Writes modified file back via FileStore (if needed)
```

---

## Migration Plan

### Phase 1: Core Abstractions (2-3 hours)
- [ ] Create `FileRef` class (`src/core/entities/file_ref.py`)
- [ ] Create `IFileStore` port (`src/core/ports/file_store.py`)
- [ ] Create `IFileBackend` interface (`src/adapters/files/backend.py`)
- [ ] Add unit tests for FileRef parsing/serialization

### Phase 2: Adapters (2-3 hours)
- [ ] Implement `LocalBackend` (`src/adapters/files/local_backend.py`)
- [ ] Implement `SSHBackend` wrapping `ParamikoSSHAdapter` (`src/adapters/files/ssh_backend.py`)
- [ ] Implement `UnifiedFileStore` (`src/adapters/files/unified_file_store.py`)
- [ ] Add unit tests for each backend

### Phase 3: Resource Resolution (3-4 hours)
- [ ] Add `FileSnapshot` to world_state (`src/project_builder/state/world_state.py`)
- [ ] Implement `ResourceResolver` (`src/project_builder/execution/resource_resolver.py`)
- [ ] Add `resource_inputs`/`resource_outputs` to Task entity (`src/entities/task.py`)
- [ ] Add unit tests for ResourceResolver

### Phase 4: Integration (3-4 hours)
- [ ] Update `ExecutionCoordinator` to use file_store + ResourceResolver
- [ ] Update `HTN-DSL Translator` to extract FileRefs from task descriptions
- [ ] Update CLI to build UnifiedFileStore with backends
- [ ] Update CLI to pass remote_host context to translator

### Phase 5: Testing (2-3 hours)
- [ ] Integration test: Local file read/write
- [ ] Integration test: SSH file read from syd2
- [ ] Integration test: End-to-end Project Builder with --remote-host
- [ ] Performance test: Resource caching (avoid redundant fetches)

**Total Estimated Time**: 12-17 hours

---

## Benefits

### Clean Architecture Maintained
- **SRP**: LLMExecutor stays pure (no I/O)
- **DIP**: Use cases depend on IFileStore (port), not concrete adapters
- **OCP**: Add new backends without touching use cases
- **Layer separation**: HTN tasks specify FileRefs; infrastructure handles transport

### Extensibility
- **S3Backend**: `s3://bucket/key.py` → boto3
- **GitHubBackend**: `github://org/repo/path` → GitHub API
- **HTTPBackend**: `https://example.com/file.py` → HTTP GET/PUT
- No changes to tasks, coordinator, or executor

### Performance
- **Caching**: FileSnapshots in world_state avoid redundant fetches
- **Checksums**: Detect stale content, avoid unnecessary writes
- **Connection pooling**: ParamikoSSHAdapter already pools SSH connections

### Testability
- **Mock IFileStore**: Test use cases without real I/O
- **Test backends independently**: LocalBackend, SSHBackend unit tests
- **Integration tests**: End-to-end with real SSH

---

## Alternative Approaches Considered

### Option 1: Inject into LLMAgentExecutor
**Rejected**: Violates SRP - executor becomes file-aware

### Option 2: Task Metadata Routing
**Rejected**: Too complex, coordinator routing logic gets messy

### Option 3: Explicit Fetch Tasks in HTN
**Rejected**: GoalDecomposer needs remote awareness, breaks abstraction

### Option 4: World State as Unified Storage ✅ **SELECTED**
**Chosen**: Tasks stay I/O-agnostic, infrastructure handles everything

---

## Open Questions

1. **World state persistence**: Should FileSnapshots be persisted to SurrealDB?
   - **Answer**: Yes, for resumption. Store FileRef + checksum, re-fetch if stale.

2. **Write-back strategy**: Immediate or batched at project end?
   - **Answer**: Immediate for safety, batch option for optimization.

3. **Conflict detection**: What if remote file changed during execution?
   - **Answer**: Use checksums/ETags, fail-fast or merge strategies.

4. **Large files**: Stream instead of loading fully into memory?
   - **Answer**: V1 loads fully, V2 adds streaming for >10MB files.

---

## Success Metrics

- [ ] SSH remote file access works end-to-end
- [ ] No changes needed to LLMAgentExecutor
- [ ] Tasks remain I/O-agnostic
- [ ] Can add S3Backend in <2 hours
- [ ] Integration test passes: fix bare excepts on remote file

---

**Next Steps**: Begin Phase 1 (Core Abstractions) in next session

**Commit**: de2f698 (SSH adapter), 8a3f5d2 (env fixes)
**Branch**: priority/prod-010
**Status**: Architecture designed, ready for implementation
