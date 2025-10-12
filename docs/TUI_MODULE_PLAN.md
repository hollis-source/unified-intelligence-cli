# Textual TUI Module Plan

**Status**: Planning Phase
**Technology**: [Textual](https://textual.textualize.io/) (Python TUI framework by Will McGugan)
**Goal**: Add interactive terminal dashboard to unified-intelligence-cli
**Timeline**: 2-3 weeks implementation
**DSL Integration**: Category theory workflows for component development

---

## Executive Summary

Add a rich, interactive terminal UI to the unified-intelligence-cli using Textual, enabling:

- **Visual agent orchestration**: See all 12 agents at a glance with status indicators
- **Real-time monitoring**: Live task execution with streaming logs
- **Interactive control**: Start/stop agents, modify priorities, cancel tasks
- **Training visualization**: Progress bars, loss graphs, model metrics
- **Result exploration**: Browse task outputs with syntax highlighting
- **Keyboard-driven**: Vim-style navigation for efficiency

**Why Textual?**
- Built on Rich (same author) - excellent rendering
- Reactive/async design - perfect for real-time updates
- CSS-like styling - easy theming
- Snapshot testing - testable UIs
- Cross-platform - works on Linux, macOS, Windows

---

## Architecture Overview

### Current CLI (Text-Based)

```bash
$ ui-cli task "Write a function to parse JSON"
🤖 Routing to: python-specialist
⏳ Generating...
✅ Result:
def parse_json(text: str) -> dict:
    import json
    return json.loads(text)
```

**Limitations**:
- No visibility into queue depth
- Can't monitor multiple agents simultaneously
- No history/result browsing
- No training progress visualization

### Proposed TUI (Interactive Dashboard)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Unified Intelligence CLI                          [Press ? for help]        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│ Agent Status                      Task Queue (12 pending)                  │
│ ┌──────────────────────────────┐  ┌──────────────────────────────────────┐ │
│ │ ● Python      [BUSY] 3 tasks │  │ P1: Fix auth bug (assigned: backend)││
│ │ ○ Frontend    [IDLE]         │  │ P1: Deploy hotfix (assigned: devops)││
│ │ ● Backend     [BUSY] 1 task  │  │ P2: Refactor API (queued)           ││
│ │ ○ DevOps      [IDLE]         │  │ P2: Update docs (queued)            ││
│ │ ● Tester      [BUSY] 2 tasks │  │ P3: Add tests (queued)              ││
│ │ ○ Researcher  [IDLE]         │  │                                      ││
│ │ [6 more...]                  │  │ [7 more...]                         ││
│ └──────────────────────────────┘  └──────────────────────────────────────┘ │
│                                                                             │
│ Live Execution Log                                                          │
│ ┌───────────────────────────────────────────────────────────────────────┐   │
│ │ [15:42:12] python-specialist: Analyzing task...                       │   │
│ │ [15:42:15] python-specialist: Generating code...                      │   │
│ │ [15:42:23] python-specialist: ✓ Code generated (256 tokens)          │   │
│ │ [15:42:25] tester: Running unit tests...                              │   │
│ │ [15:42:30] tester: ✓ 12/12 tests passed                              │   │
│ │                                                                        │   │
│ └───────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│ [Tab] Switch View  [q] Quit  [/] Search  [:] Command                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Benefits**:
- ✅ Real-time visibility across all agents
- ✅ Queue management (priorities, filtering)
- ✅ Searchable logs with syntax highlighting
- ✅ Keyboard shortcuts for power users
- ✅ Multiple concurrent views (tabs/splits)

---

## Component Architecture

### 1. Main Application Structure

```python
# src/tui/app.py
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, TabbedContent

class UnifiedIntelligenceTUI(App):
    """Main TUI application."""

    CSS_PATH = "app.css"
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("d", "toggle_dark", "Toggle dark mode"),
        ("/", "search", "Search"),
        (":", "command", "Command palette"),
        ("?", "help", "Help"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield TabbedContent(
            DashboardTab(),
            TaskQueueTab(),
            AgentMonitorTab(),
            TrainingTab(),
            ResultsTab(),
            SettingsTab(),
        )
        yield Footer()
```

### 2. Dashboard Tab (Main View)

```python
# src/tui/tabs/dashboard.py
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Static, DataTable

class DashboardTab(Container):
    """Main dashboard with agent status + task queue."""

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield AgentStatusGrid()
            yield TaskQueueList()
        yield LiveExecutionLog()
```

**AgentStatusGrid**:
```
┌─────────────────────────┐
│ ● Python      [BUSY] 3  │  ← Green dot (active), count of tasks
│ ○ Frontend    [IDLE]    │  ← Gray dot (idle)
│ ● Backend     [BUSY] 1  │
│ ⚠ Tester      [ERROR]   │  ← Red dot (error state)
│ ○ Researcher  [IDLE]    │
│ ... (12 total)          │
└─────────────────────────┘
```

**Implementation**:
```python
class AgentStatusGrid(DataTable):
    def on_mount(self):
        self.add_columns("Agent", "Status", "Tasks")
        self.add_rows([
            ("Python", "BUSY", "3"),
            ("Frontend", "IDLE", "0"),
            # ... etc
        ])

        # Update every 500ms
        self.set_interval(0.5, self.refresh_status)

    async def refresh_status(self):
        # Query agent status from orchestrator
        status = await get_agent_status()
        self.update_rows(status)
```

### 3. Task Queue Tab

```python
# src/tui/tabs/task_queue.py
class TaskQueueTab(Container):
    """Priority queue with filtering and actions."""

    BINDINGS = [
        ("p", "set_priority", "Set Priority"),
        ("c", "cancel_task", "Cancel Task"),
        ("r", "retry_task", "Retry Task"),
    ]

    def compose(self) -> ComposeResult:
        yield Input(placeholder="Filter tasks...")
        yield TaskQueueTable()
        yield TaskDetailPane()
```

**Task Queue Table**:
```
┌──────────────────────────────────────────────────────────────────┐
│ Priority │ Task ID       │ Agent     │ Status   │ Created        │
├──────────┼───────────────┼───────────┼──────────┼────────────────┤
│ P1       │ task-abc123   │ backend   │ RUNNING  │ 2 min ago      │
│ P1       │ task-def456   │ devops    │ QUEUED   │ 5 min ago      │
│ P2       │ task-ghi789   │ (pending) │ QUEUED   │ 10 min ago     │
│ P2       │ task-jkl012   │ (pending) │ QUEUED   │ 15 min ago     │
│ P3       │ task-mno345   │ (pending) │ QUEUED   │ 1 hour ago     │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
   ↑ Selected row (navigation: j/k or arrows)
```

**Features**:
- **Sorting**: Click column headers or use `:sort priority`
- **Filtering**: Type in search box or use `/pattern`
- **Actions**: Select row → press `p` to change priority
- **Live updates**: New tasks appear automatically

### 4. Agent Monitor Tab (Live Logs)

```python
# src/tui/tabs/agent_monitor.py
class AgentMonitorTab(Container):
    """Real-time log streaming with syntax highlighting."""

    def compose(self) -> ComposeResult:
        yield AgentSelector()  # Dropdown to choose agent
        yield LogViewer()      # Rich syntax-highlighted log
```

**Log Viewer**:
```
┌─────────────────────────────────────────────────────────────────┐
│ Agent: python-specialist                    [Auto-scroll: ON]   │
├─────────────────────────────────────────────────────────────────┤
│ [15:42:12] INFO  Received task: task-abc123                     │
│ [15:42:12] DEBUG Loading model: Qwen3-8B Q4_K_M                 │
│ [15:42:15] INFO  Generating response...                         │
│ [15:42:23] INFO  Generated 256 tokens (avg: 31 tok/s)          │
│ [15:42:23] DEBUG Response:                                      │
│                                                                  │
│   def parse_json(text: str) -> dict:                           │
│       """Parse JSON string safely."""                          │
│       import json                                              │
│       try:                                                     │
│           return json.loads(text)                             │
│       except json.JSONDecodeError as e:                       │
│           raise ValueError(f"Invalid JSON: {e}")              │
│                                                                  │
│ [15:42:24] INFO  ✓ Task completed successfully                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Features**:
- **Syntax highlighting**: Code blocks auto-detected and highlighted
- **Log levels**: Color-coded (INFO=blue, WARNING=yellow, ERROR=red)
- **Auto-scroll**: Follow tail (toggle with Space)
- **Search**: `/error` to find all errors
- **Export**: Save filtered logs to file

### 5. Training Tab

```python
# src/tui/tabs/training.py
class TrainingTab(Container):
    """Monitor model training with progress bars and graphs."""

    def compose(self) -> ComposeResult:
        yield TrainingProgress()
        yield LossGraph()
        yield MetricsTable()
```

**Training Progress**:
```
┌─────────────────────────────────────────────────────────────────┐
│ Training: Qwen3-8B LoRA Fine-Tuning                             │
├─────────────────────────────────────────────────────────────────┤
│ Epoch 2/3                                                        │
│ ████████████████████░░░░░░░░░░ 75% (18/24 steps)               │
│                                                                  │
│ Current Loss: 1.42                                              │
│ Best Loss:    1.38 (epoch 1, step 7)                           │
│ ETA:          45 minutes                                         │
│                                                                  │
│ Loss History (last 10 steps):                                   │
│ 2.1 ┤                                                           │
│ 1.8 ┤╮                                                          │
│ 1.5 ┤╰╮                                                         │
│ 1.2 ┤ ╰─╮╭─╮                                                   │
│ 0.9 ┤    ╰╯ ╰───────                                           │
│     └──────────────────────────────────────────────────        │
│     0        5        10       15       20                      │
│                                                                  │
│ [p] Pause  [s] Stop  [e] Export checkpoint                      │
└─────────────────────────────────────────────────────────────────┘
```

**Features**:
- **Live progress bar**: Updates every step
- **Loss graph**: Sparkline or full chart (toggleable)
- **Metrics**: Learning rate, gradient norm, throughput
- **Control**: Pause, resume, stop training
- **Export**: Save checkpoint on demand

### 6. Results Browser Tab

```python
# src/tui/tabs/results.py
class ResultsTab(Container):
    """Browse and search task results."""

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield ResultsTree()      # Tree view of tasks (by date/agent)
            yield ResultDetailPane() # Selected result with syntax highlighting
```

**Results Tree + Detail**:
```
┌────────────────────────┬──────────────────────────────────────────┐
│ Results                │ Task: task-abc123                        │
│                        │ Agent: python-specialist                 │
│ ▼ Today                │ Created: 2025-10-02 15:42                │
│   ▼ python-specialist  │ Duration: 11.2s                          │
│     ● task-abc123      │                                          │
│     ● task-def456      │ Result:                                  │
│   ▼ backend            │ ┌────────────────────────────────────┐  │
│     ● task-ghi789      │ │def parse_json(text: str) -> dict: │  │
│ ▼ Yesterday            │ │    """Parse JSON safely."""        │  │
│   ▼ frontend           │ │    import json                     │  │
│     ● task-jkl012      │ │    try:                            │  │
│     [24 more...]       │ │        return json.loads(text)     │  │
│                        │ │    except json.JSONDecodeError:    │  │
│ [Filter: ]             │ │        raise ValueError(...)       │  │
│                        │ └────────────────────────────────────┘  │
│                        │                                          │
│                        │ [c] Copy  [e] Export  [Enter] Full view │
└────────────────────────┴──────────────────────────────────────────┘
```

**Features**:
- **Tree navigation**: Group by date, agent, status
- **Search**: Find results by content, agent, date
- **Syntax highlighting**: Auto-detect language (Python, JS, etc.)
- **Export**: Save individual result or bulk export
- **Compare**: Diff two results side-by-side

### 7. Settings Tab

```python
# src/tui/tabs/settings.py
class SettingsTab(Container):
    """Configure models, agents, and UI preferences."""

    def compose(self) -> ComposeResult:
        yield ModelConfigSection()
        yield AgentConfigSection()
        yield UIPreferencesSection()
```

**Settings Interface**:
```
┌─────────────────────────────────────────────────────────────────┐
│ Settings                                                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│ Model Configuration                                              │
│ ┌──────────────────────────────────────────────────────────┐    │
│ │ Default Model:  [Qwen3-8B Q4_K_M ▼]                       │    │
│ │ Max Tokens:     [2048          ] ← →                      │    │
│ │ Temperature:    [0.7           ] ← →                      │    │
│ │ Top P:          [0.9           ] ← →                      │    │
│ └──────────────────────────────────────────────────────────┘    │
│                                                                  │
│ Agent Configuration                                              │
│ ┌──────────────────────────────────────────────────────────┐    │
│ │ Auto-routing:      [✓] Enabled                            │    │
│ │ Max parallel:      [5 ] agents                            │    │
│ │ Queue strategy:    [Priority-based ▼]                     │    │
│ │ Timeout:           [300] seconds                          │    │
│ └──────────────────────────────────────────────────────────┘    │
│                                                                  │
│ UI Preferences                                                   │
│ ┌──────────────────────────────────────────────────────────┐    │
│ │ Theme:             [Dark ▼] (Dark/Light/Auto)             │    │
│ │ Syntax theme:      [Monokai ▼]                            │    │
│ │ Keybindings:       [Vim ▼] (Vim/Emacs/Default)           │    │
│ │ Auto-refresh:      [500] ms                               │    │
│ └──────────────────────────────────────────────────────────┘    │
│                                                                  │
│ [Save] [Reset to Defaults] [Cancel]                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Keybindings

### Global (Available Everywhere)

| Key | Action | Description |
|-----|--------|-------------|
| `q` | Quit | Exit application |
| `Ctrl+c` | Interrupt | Cancel current operation |
| `?` | Help | Show keybinding reference |
| `Tab` | Next tab | Cycle through tabs |
| `Shift+Tab` | Prev tab | Reverse cycle tabs |
| `/` | Search | Open search dialog |
| `:` | Command | Command palette |
| `d` | Dark mode | Toggle dark/light theme |

### Vim-Style Navigation (Optional, Configurable)

| Key | Action | Description |
|-----|--------|-------------|
| `h` | Left | Move left |
| `j` | Down | Move down |
| `k` | Up | Move up |
| `l` | Right | Move right |
| `g` | Top | Go to top |
| `G` | Bottom | Go to bottom |
| `Ctrl+d` | Page down | Scroll half-page down |
| `Ctrl+u` | Page up | Scroll half-page up |

### Context-Specific

**Task Queue**:
- `p`: Set priority
- `c`: Cancel task
- `r`: Retry task
- `Enter`: View details

**Agent Monitor**:
- `Space`: Toggle auto-scroll
- `e`: Export logs
- `f`: Follow specific agent

**Training**:
- `p`: Pause training
- `s`: Stop training
- `e`: Export checkpoint

**Results**:
- `c`: Copy result
- `e`: Export result
- `Enter`: Full-screen view

---

## Styling (CSS-Like)

Textual supports CSS-like styling for beautiful UIs:

```css
/* src/tui/app.css */

/* Global theme */
Screen {
    background: $background;
    color: $text;
}

/* Agent status indicators */
.agent-idle {
    color: $secondary;
}

.agent-busy {
    color: $success;
}

.agent-error {
    color: $error;
}

/* Priority badges */
.priority-p1 {
    background: $error;
    color: $text-on-error;
}

.priority-p2 {
    background: $warning;
    color: $text-on-warning;
}

.priority-p3 {
    background: $secondary;
    color: $text-on-secondary;
}

/* Syntax highlighting */
.code-keyword { color: #ff79c6; }
.code-string  { color: #f1fa8c; }
.code-comment { color: #6272a4; font-style: italic; }
.code-function { color: #50fa7b; }

/* Layout */
DashboardTab {
    layout: vertical;
}

DashboardTab Horizontal {
    height: 40%;
}

LiveExecutionLog {
    height: 1fr;
    border: solid $primary;
}
```

---

## Implementation Roadmap

### Week 1: Foundation

**Days 1-2**: Setup + Wireframes
- [ ] Install Textual + dependencies
- [ ] Create ASCII mockups of all 6 tabs
- [ ] Define data models (AgentStatus, Task, Result)
- [ ] Set up project structure

**Days 3-5**: Core Components (Parallel)
- [ ] Dashboard tab (agent grid + task queue)
- [ ] Task queue tab (table + filtering)
- [ ] Agent monitor tab (log viewer)
- [ ] Stub out training/results/settings tabs

**Days 6-7**: Integration
- [ ] Wire up navigation between tabs
- [ ] Implement state management (reactive data)
- [ ] Add keybindings (global + context)
- [ ] Basic error handling

### Week 2: Features

**Days 1-3**: Advanced Components
- [ ] Training tab (progress bars + graphs)
- [ ] Results browser (tree + detail pane)
- [ ] Settings tab (dropdowns + sliders)
- [ ] Command palette (`:` command)

**Days 4-5**: Data Integration
- [ ] Connect to real agent orchestrator
- [ ] Real-time updates via websockets/polling
- [ ] Task submission from TUI
- [ ] Result persistence

**Days 6-7**: Polish
- [ ] Themes (dark + light mode)
- [ ] Syntax highlighting for code blocks
- [ ] Animations (smooth transitions)
- [ ] Performance optimization (<16ms frames)

### Week 3: Testing & Docs

**Days 1-3**: Testing
- [ ] Unit tests for widgets
- [ ] Snapshot tests for UI
- [ ] Interaction tests (keyboard/mouse)
- [ ] Load testing (100+ tasks)

**Days 4-5**: Documentation
- [ ] User guide (screenshots + examples)
- [ ] Developer guide (adding new tabs)
- [ ] Keybinding reference card
- [ ] Troubleshooting guide

**Days 6-7**: Release
- [ ] Integration with main CLI (`ui-cli tui`)
- [ ] Package dependencies
- [ ] Announce + demo video

---

## DSL Integration

### Workflow 1: Full TUI Development

**File**: `tui_development_pipeline.ct`
```
write_docs ∘ performance_test ∘ implement_themes ∘ add_keybindings ∘
  integrate_components ∘
  (build_dashboard × build_task_queue × build_agent_monitor ×
   build_model_config × build_training_view × build_results_browser) ∘
  setup_textual ∘ design_wireframes
```

**Execution**:
```bash
PYTHONPATH=. python -m src.dsl.cli_integration \
  examples/workflows/tui_development_pipeline.ct
```

**Benefit**: Parallel component development (6 widgets built simultaneously)

### Workflow 2: Feature Addition

**File**: `tui_feature_workflow.ct`
```
update_docs ∘ add_tests ∘ integrate_dashboard ∘ add_rendering ∘
  implement_data_layer ∘ create_widget ∘ prototype_layout
```

**Use case**: Developer adds network graph widget showing agent collaboration

### Workflow 3: Testing Pipeline

**File**: `tui_testing_pipeline.ct`
```
generate_report ∘ performance_profiling ∘ manual_qa ∘
  (run_unit_tests × run_snapshot_tests ×
   run_interaction_tests × run_accessibility_tests) ∘
  create_snapshots
```

**Benefit**: Parallel test execution (4 test suites run concurrently)

---

## Example Usage

### Launch TUI

```bash
# Primary command
ui-cli tui

# Or with specific tab
ui-cli tui --tab=training

# Or with config override
ui-cli tui --theme=light --keybindings=vim
```

### Typical User Flow

**Scenario**: Developer monitors multi-agent code review workflow

1. **Launch TUI**:
   ```bash
   ui-cli tui
   ```

2. **Dashboard view**: See all agents
   ```
   ● Python      [BUSY] - Generating code
   ● Tester      [BUSY] - Writing tests
   ● Reviewer    [QUEUED] - Waiting for code
   ○ DevOps      [IDLE]
   ```

3. **Switch to Agent Monitor** (press `Tab`):
   ```
   Agent: python-specialist
   [15:42:12] Generating function implementation...
   [15:42:23] ✓ Generated 256 tokens
   ```

4. **View task queue** (press `Tab` again):
   ```
   P1: Review code (assigned: reviewer)
   P2: Deploy (queued)
   ```

5. **Adjust priority** (select task, press `p`):
   ```
   Set priority: [P1▼] → [P2]
   ```

6. **Monitor training** (press `Tab` to training tab):
   ```
   Epoch 2/3: ████████████████░░░░ 75%
   Loss: 1.42 (↓ from 2.1)
   ETA: 45 minutes
   ```

7. **Browse results** (press `Tab` to results):
   ```
   ▼ Today
     ▼ python-specialist
       ● task-abc123 ← Select, press Enter

   [Full code displayed with syntax highlighting]
   ```

**Exit**: Press `q` at any time

---

## Technical Details

### Reactive Data Flow

```python
# src/tui/state.py
from textual.reactive import Reactive

class AgentState:
    """Reactive state for agent status."""

    status: Reactive[str] = Reactive("IDLE")
    task_count: Reactive[int] = Reactive(0)
    current_task: Reactive[str | None] = Reactive(None)

    def watch_status(self, old: str, new: str):
        """Called when status changes."""
        if new == "ERROR":
            self.notify("Agent error!", severity="error")
```

Widgets automatically re-render when reactive properties change.

### Real-Time Updates

```python
# src/tui/tabs/dashboard.py
class DashboardTab(Container):
    def on_mount(self):
        # Poll agent status every 500ms
        self.set_interval(0.5, self.update_agents)

        # Or use websocket for push updates
        asyncio.create_task(self.listen_for_events())

    async def update_agents(self):
        status = await get_agent_status()
        self.agent_grid.update(status)

    async def listen_for_events(self):
        async for event in websocket_connection():
            if event.type == "task_completed":
                self.notify(f"✓ Task {event.task_id} completed")
```

### Performance Optimization

**Target**: 60fps = 16.67ms per frame

**Techniques**:
1. **Lazy rendering**: Only render visible widgets
2. **Debouncing**: Don't update on every keystroke
3. **Background tasks**: Offload heavy computation
4. **Caching**: Cache rendered content

```python
class LargeLogViewer(Widget):
    def __init__(self, max_lines: int = 10000):
        super().__init__()
        self.max_lines = max_lines
        self._cache = []

    def render(self) -> RenderableType:
        # Only render visible portion
        viewport = self.scrollable_content_region
        visible_lines = self._cache[viewport.y:viewport.y + viewport.height]
        return "\n".join(visible_lines)
```

---

## Testing Strategy

### 1. Snapshot Testing

Textual's built-in snapshot testing:

```python
# tests/test_dashboard.py
from textual.testing import App

async def test_dashboard_layout(snap_compare):
    """Test dashboard renders correctly."""
    app = UnifiedIntelligenceTUI()
    async with app.run_test() as pilot:
        await pilot.pause()
        assert await snap_compare("dashboard.svg")
```

### 2. Interaction Testing

```python
async def test_task_queue_navigation():
    """Test keyboard navigation in task queue."""
    app = UnifiedIntelligenceTUI()
    async with app.run_test() as pilot:
        # Navigate to task queue tab
        await pilot.press("tab", "tab")

        # Select first task
        await pilot.press("j")  # Down

        # Change priority
        await pilot.press("p")

        # Verify priority changed
        task_queue = app.query_one(TaskQueueTable)
        assert task_queue.selected_task.priority == "P2"
```

### 3. Performance Testing

```python
async def test_large_log_performance():
    """Ensure log viewer handles 10k+ lines."""
    app = UnifiedIntelligenceTUI()
    async with app.run_test() as pilot:
        log_viewer = app.query_one(LogViewer)

        # Add 10,000 log lines
        for i in range(10_000):
            log_viewer.append(f"[{i}] Log line {i}")

        # Measure frame time
        start = time.time()
        await log_viewer.refresh()
        duration = time.time() - start

        assert duration < 0.016  # < 16ms (60fps)
```

---

## Alternatives Considered

### Why Not Blessed/Urwid?

**Blessed**:
- ❌ Lower-level (more boilerplate)
- ❌ No reactive model
- ❌ Limited layout system

**Urwid**:
- ❌ Older codebase
- ❌ Not async-first
- ❌ Less modern styling

**Textual**:
- ✅ Modern, actively developed
- ✅ Async/await native
- ✅ CSS-like styling
- ✅ Built on Rich (excellent rendering)
- ✅ Snapshot testing built-in

### Why Not Web UI (Gradio/Streamlit)?

- ❌ Requires browser (not terminal-native)
- ❌ Heavier dependencies
- ❌ Not SSH-friendly (port forwarding needed)
- ✅ Textual works over SSH seamlessly

---

## Future Enhancements

### Phase 2 (Post-Launch)

1. **Collaboration Graph**: Visual network showing agent communication
2. **Time Machine**: Replay task execution with step-by-step navigation
3. **Diff View**: Side-by-side comparison of agent outputs
4. **Metrics Dashboard**: Grafana-style graphs for throughput, latency
5. **Voice Control**: Whisper integration for hands-free operation

### Phase 3 (Advanced)

1. **Multi-User**: Collaborative TUI (multiple users see same state)
2. **Plugin System**: Custom widgets/tabs via plugins
3. **Remote Mode**: TUI client connects to remote server
4. **Mobile Companion**: Mirror TUI state to mobile app

---

## Success Metrics

### Phase 1 (MVP)

- ✅ All 6 core tabs functional
- ✅ Real-time updates with <500ms latency
- ✅ 60fps rendering (16ms per frame)
- ✅ 100% test coverage for widgets
- ✅ Documentation complete

### Phase 2 (Adoption)

- ✅ 80% of CLI users try TUI
- ✅ 50% of CLI users prefer TUI
- ✅ <5% bug reports in first month
- ✅ Community contributions (themes, plugins)

---

## Conclusion

Adding a Textual-based TUI to unified-intelligence-cli provides:

1. **Visibility**: Real-time view of all 12 agents simultaneously
2. **Control**: Interactive task management, priority adjustment
3. **Monitoring**: Live logs, training progress, metrics
4. **Productivity**: Keyboard-driven workflow (Vim shortcuts)
5. **Accessibility**: Works over SSH, no GUI required

**DSL Integration**: Category theory workflows orchestrate parallel component development, reducing build time from ~24 hours (sequential) to ~8 hours (6 components in parallel).

**Next Steps**: Implement Week 1 roadmap (foundation + core components).

---

**Document Version**: 1.0
**Created**: 2025-10-02
**Status**: Planning → Ready for Implementation
