# Endpoint Monitor: SOLID & Component Principles Analysis

**Created**: 2025-10-12
**Status**: Architecture Review
**Related**: [ENDPOINT_MONITOR_ARCHITECTURE.md](./ENDPOINT_MONITOR_ARCHITECTURE.md)

## Executive Summary

Detailed analysis of endpoint monitoring architecture against remaining SOLID principles (Liskov Substitution, Interface Segregation) and Clean Architecture component principles. Identifies violations and provides fixes.

## Liskov Substitution Principle (LSP)

### Definition

> "Objects of a supertype should be replaceable with objects of a subtype without breaking the application"

**Formal Requirements**:
1. **Preconditions**: Subtypes cannot strengthen preconditions
2. **Postconditions**: Subtypes cannot weaken postconditions
3. **Invariants**: Subtypes must maintain base type invariants
4. **History Constraint**: Subtypes cannot introduce new behaviors observable to clients

### Current Design

```python
class IHealthChecker(ABC):
    """Abstract health checker interface."""

    @abstractmethod
    async def check(self, endpoint: Endpoint) -> HealthCheckResponse:
        """
        Check endpoint health.

        Args:
            endpoint: Endpoint to check

        Returns:
            HealthCheckResponse with state and metrics

        Raises:
            HealthCheckError: On unrecoverable errors
        """
        pass
```

**Concrete Implementations**:
- `HFInferenceHealthAdapter`
- `ReplicateHealthAdapter`
- `ModalHealthAdapter`

### LSP Violations Identified

#### Violation 1: Precondition Strengthening

**Problem**: Different authentication mechanisms across providers

```python
# HFInferenceHealthAdapter
async def check(self, endpoint: Endpoint) -> HealthCheckResponse:
    # Expects: endpoint.url contains base URL, token in env var HF_TOKEN
    headers = {"Authorization": f"Bearer {os.getenv('HF_TOKEN')}"}
    async with session.post(endpoint.url, headers=headers) as resp:
        ...

# ReplicateHealthAdapter
async def check(self, endpoint: Endpoint) -> HealthCheckResponse:
    # Expects: endpoint.url contains full URL with auth token embedded
    # STRONGER PRECONDITION: URL must include ?token=xxx
    async with session.post(endpoint.url) as resp:  # No headers!
        ...
```

**Impact**: Switching from HF to Replicate breaks if endpoint.url doesn't contain embedded token

**Fix**: Standardize authentication via adapter-specific configuration

```python
@dataclass(frozen=True)
class Endpoint:
    """Represents a monitored inference endpoint."""

    id: str
    provider: str  # "huggingface", "replicate", "modal"
    url: str       # Base URL (no auth)
    auth_config: Dict[str, str]  # Provider-specific auth
    # auth_config examples:
    #   HF: {"type": "bearer", "token_env": "HF_TOKEN"}
    #   Replicate: {"type": "query_param", "token_env": "REPLICATE_TOKEN"}
    #   Modal: {"type": "header", "header_name": "X-Modal-Key", "token_env": "MODAL_KEY"}
```

**Updated Adapters**:

```python
class HFInferenceHealthAdapter(IHealthChecker):
    """Health check for Hugging Face Inference API."""

    async def check(self, endpoint: Endpoint) -> HealthCheckResponse:
        # Validate precondition (fail fast if violated)
        if endpoint.provider != "huggingface":
            raise ValueError(f"HFInferenceHealthAdapter requires provider='huggingface', got '{endpoint.provider}'")

        # Extract auth from standardized config
        token = os.getenv(endpoint.auth_config.get("token_env", "HF_TOKEN"))
        headers = {"Authorization": f"Bearer {token}"}

        # Standard health check logic
        async with session.post(endpoint.url, headers=headers, ...) as resp:
            return self._parse_response(resp)

class ReplicateHealthAdapter(IHealthChecker):
    """Health check for Replicate API."""

    async def check(self, endpoint: Endpoint) -> HealthCheckResponse:
        # Same precondition validation
        if endpoint.provider != "replicate":
            raise ValueError(f"ReplicateHealthAdapter requires provider='replicate', got '{endpoint.provider}'")

        # Extract auth from standardized config
        token = os.getenv(endpoint.auth_config.get("token_env", "REPLICATE_TOKEN"))

        # Replicate uses query parameter
        url_with_auth = f"{endpoint.url}?token={token}"

        async with session.post(url_with_auth, ...) as resp:
            return self._parse_response(resp)
```

**Result**: ✅ Both adapters have same preconditions (valid Endpoint with auth_config)

#### Violation 2: Postcondition Weakening

**Problem**: Provider-specific error details leak into response

```python
# HFInferenceHealthAdapter returns HF-specific error
return HealthCheckResponse(
    status=EndpointState.FAILED,
    error="HF API Error: Model not loaded (status 503)"  # HF-specific!
)

# Use case depends on parsing error string
if "Model not loaded" in status.error:
    # Assume sleeping, try to wake
    await self._waker.wake(endpoint)
```

**Impact**: Logic breaks when switching to Replicate (different error strings)

**Fix**: Standardize error representation

```python
@dataclass
class HealthCheckResponse:
    """Standardized health check response (provider-agnostic)."""

    status: EndpointState  # HEALTHY, SLEEPING, DEGRADED, FAILED
    response_time_ms: Optional[float]
    error_code: Optional[str]  # Standardized codes (not provider-specific)
    error_details: Optional[Dict[str, Any]]  # Provider-specific details (optional)

# Standardized error codes (across all providers)
class HealthCheckErrorCode(str, Enum):
    MODEL_LOADING = "model_loading"      # Model is loading (sleeping)
    TIMEOUT = "timeout"                   # Request timeout
    RATE_LIMITED = "rate_limited"         # API rate limit exceeded
    AUTH_FAILED = "auth_failed"           # Authentication failure
    INTERNAL_ERROR = "internal_error"     # Provider internal error
    UNKNOWN = "unknown"                   # Unknown error
```

**Updated Adapters**:

```python
class HFInferenceHealthAdapter(IHealthChecker):
    async def check(self, endpoint: Endpoint) -> HealthCheckResponse:
        try:
            async with session.post(...) as resp:
                if resp.status == 503:
                    # Map HF 503 to standardized code
                    return HealthCheckResponse(
                        status=EndpointState.SLEEPING,
                        error_code=HealthCheckErrorCode.MODEL_LOADING,
                        error_details={"provider": "huggingface", "http_status": 503}
                    )
                # ... other cases
        except asyncio.TimeoutError:
            return HealthCheckResponse(
                status=EndpointState.FAILED,
                error_code=HealthCheckErrorCode.TIMEOUT,
                error_details={"provider": "huggingface"}
            )

class ReplicateHealthAdapter(IHealthChecker):
    async def check(self, endpoint: Endpoint) -> HealthCheckResponse:
        try:
            async with session.post(...) as resp:
                if resp.status == 503:
                    # Map Replicate 503 to SAME standardized code
                    return HealthCheckResponse(
                        status=EndpointState.SLEEPING,
                        error_code=HealthCheckErrorCode.MODEL_LOADING,
                        error_details={"provider": "replicate", "http_status": 503}
                    )
                # ... other cases
        except asyncio.TimeoutError:
            return HealthCheckResponse(
                status=EndpointState.FAILED,
                error_code=HealthCheckErrorCode.TIMEOUT,
                error_details={"provider": "replicate"}
            )
```

**Updated Use Case**:

```python
class CheckEndpointHealth:
    async def execute(self, endpoint: Endpoint) -> HealthStatus:
        response = await self._checker.check(endpoint)

        # Use standardized error code (works for all providers)
        if response.error_code == HealthCheckErrorCode.MODEL_LOADING:
            return HealthStatus(
                endpoint_id=endpoint.id,
                state=EndpointState.SLEEPING,
                needs_wake=True
            )
        # ... other cases
```

**Result**: ✅ Postconditions consistent across all adapters

#### Violation 3: Invariant Violation

**Problem**: Different timeout behaviors

```python
# HFInferenceHealthAdapter: 90s timeout
async with session.post(url, timeout=ClientTimeout(total=90)) as resp:
    ...

# ModalHealthAdapter: 300s timeout (different invariant!)
async with session.post(url, timeout=ClientTimeout(total=300)) as resp:
    ...
```

**Impact**: Use case assumes health checks complete within 90s; switching to Modal breaks assumption

**Fix**: Enforce timeout via Endpoint configuration

```python
@dataclass(frozen=True)
class Endpoint:
    id: str
    provider: str
    url: str
    auth_config: Dict[str, str]
    health_check_timeout: int = 90  # Default 90s (enforced by contract)

class IHealthChecker(ABC):
    """Abstract health checker with enforced contract."""

    @abstractmethod
    async def check(self, endpoint: Endpoint) -> HealthCheckResponse:
        """
        Check endpoint health within timeout.

        Contract:
        - MUST complete within endpoint.health_check_timeout seconds
        - MUST return HealthCheckResponse with status
        - MUST use standardized error codes
        - MUST NOT raise exceptions (return FAILED status instead)
        """
        pass

class BaseHealthChecker(IHealthChecker):
    """Base class enforcing LSP invariants."""

    async def check(self, endpoint: Endpoint) -> HealthCheckResponse:
        """Template method enforcing timeout invariant."""
        try:
            # Enforce timeout at base class level
            return await asyncio.wait_for(
                self._check_impl(endpoint),
                timeout=endpoint.health_check_timeout
            )
        except asyncio.TimeoutError:
            # Timeout handling (enforced by base class)
            return HealthCheckResponse(
                status=EndpointState.FAILED,
                error_code=HealthCheckErrorCode.TIMEOUT
            )
        except Exception as e:
            # Exception handling (enforced by base class)
            return HealthCheckResponse(
                status=EndpointState.FAILED,
                error_code=HealthCheckErrorCode.UNKNOWN,
                error_details={"exception": str(e)}
            )

    @abstractmethod
    async def _check_impl(self, endpoint: Endpoint) -> HealthCheckResponse:
        """Subclass-specific implementation (no timeout handling needed)."""
        pass

class HFInferenceHealthAdapter(BaseHealthChecker):
    """HF health check (inherits timeout enforcement)."""

    async def _check_impl(self, endpoint: Endpoint) -> HealthCheckResponse:
        # No timeout handling here (handled by base class)
        async with session.post(endpoint.url, ...) as resp:
            return self._parse_response(resp)
```

**Result**: ✅ Timeout invariant enforced by base class (all subclasses behave consistently)

### LSP Summary

| Violation | Fix | Status |
|-----------|-----|--------|
| Precondition strengthening (auth) | Standardize via `auth_config` | ✅ Fixed |
| Postcondition weakening (errors) | Standardize error codes | ✅ Fixed |
| Invariant violation (timeouts) | Enforce via base class | ✅ Fixed |
| History constraint | No new observable behaviors | ✅ Good |

**LSP Compliance**: ✅ All adapters now substitutable without breaking use cases

---

## Interface Segregation Principle (ISP)

### Definition

> "No client should be forced to depend on methods it doesn't use"

**Goal**: Small, focused interfaces (role-based segregation)

### Current Design

```python
class IWaker(ABC):
    """Interface for waking sleeping endpoints."""

    @abstractmethod
    async def wake(self, endpoint: Endpoint) -> None:
        """Send wake request to endpoint."""
        pass

    @abstractmethod
    async def wait_for_ready(self, endpoint: Endpoint, timeout: int) -> bool:
        """Poll endpoint until ready or timeout."""
        pass
```

### ISP Violations Identified

#### Violation 1: Fat Interface

**Problem**: Some providers don't support `wait_for_ready`

```python
class ReplicateWaker(IWaker):
    """Replicate doesn't expose status polling API."""

    async def wake(self, endpoint: Endpoint) -> None:
        # Can send wake request
        await self._send_inference_request(endpoint)

    async def wait_for_ready(self, endpoint: Endpoint, timeout: int) -> bool:
        # Can't poll status - Replicate has no API for this!
        # FORCED to implement no-op or raise NotImplementedError
        raise NotImplementedError("Replicate doesn't support status polling")
```

**Impact**: Clients using `ReplicateWaker` can't use `wait_for_ready`

**Fix**: Split into smaller interfaces

```python
# Separate interfaces for separate capabilities
class IWaker(ABC):
    """Interface for waking sleeping endpoints."""

    @abstractmethod
    async def wake(self, endpoint: Endpoint) -> WakeResult:
        """
        Send wake request to endpoint.

        Returns:
            WakeResult with success status
        """
        pass

class IReadinessPoller(ABC):
    """Interface for polling endpoint readiness (optional capability)."""

    @abstractmethod
    async def poll_until_ready(self, endpoint: Endpoint, timeout: int) -> bool:
        """
        Poll endpoint until ready or timeout.

        Returns:
            True if ready, False if timeout
        """
        pass

class IHealthChecker(ABC):
    """Interface for checking endpoint health (already defined)."""

    @abstractmethod
    async def check(self, endpoint: Endpoint) -> HealthCheckResponse:
        pass
```

**Updated Adapters**:

```python
# HF supports both waking and polling
class HFInferenceWaker(IWaker, IReadinessPoller):
    """HF supports wake + readiness polling."""

    async def wake(self, endpoint: Endpoint) -> WakeResult:
        # Send minimal inference request
        await self._send_wake_request(endpoint)
        return WakeResult(success=True)

    async def poll_until_ready(self, endpoint: Endpoint, timeout: int) -> bool:
        # HF exposes status API
        start_time = time.time()
        while time.time() - start_time < timeout:
            status = await self._check_status(endpoint)
            if status == "loaded":
                return True
            await asyncio.sleep(5)
        return False

# Replicate only supports waking
class ReplicateWaker(IWaker):
    """Replicate only supports wake (no polling API)."""

    async def wake(self, endpoint: Endpoint) -> WakeResult:
        await self._send_wake_request(endpoint)
        return WakeResult(success=True)

    # No poll_until_ready implementation (not forced to implement unused method)
```

**Updated Use Case**:

```python
class WakeEndpoint:
    """Wake endpoint use case (uses composition)."""

    def __init__(
        self,
        waker: IWaker,
        readiness_poller: Optional[IReadinessPoller] = None,
        health_checker: Optional[IHealthChecker] = None
    ):
        self._waker = waker
        self._poller = readiness_poller
        self._health_checker = health_checker

    async def execute(self, endpoint: Endpoint, max_retries: int = 3) -> WakeResult:
        """Wake endpoint and wait for readiness."""

        # Always send wake request
        wake_result = await self._waker.wake(endpoint)
        if not wake_result.success:
            return wake_result

        # If poller available, use it
        if self._poller:
            ready = await self._poller.poll_until_ready(
                endpoint,
                timeout=endpoint.wake_timeout
            )
            return WakeResult(success=ready)

        # If health checker available (fallback), use that
        elif self._health_checker:
            return await self._poll_via_health_check(endpoint)

        # If neither available, assume success after wake
        else:
            return WakeResult(success=True, warning="No readiness check available")
```

**Result**: ✅ Clients only depend on interfaces they actually use

#### Violation 2: Forced Coupling

**Problem**: Clients that only need wake are coupled to wait_for_ready

```python
# Simple wake-only use case
class QuickWakeEndpoint:
    def __init__(self, waker: IWaker):  # Currently forces wait_for_ready too
        self._waker = waker

    async def execute(self, endpoint: Endpoint) -> None:
        await self._waker.wake(endpoint)
        # Don't need wait_for_ready, but it's in interface!
```

**Fix**: Already fixed by splitting interfaces (clients now choose what to depend on)

```python
class QuickWakeEndpoint:
    def __init__(self, waker: IWaker):  # Only depends on IWaker
        self._waker = waker

    async def execute(self, endpoint: Endpoint) -> None:
        await self._waker.wake(endpoint)
        # No forced coupling to IReadinessPoller
```

### ISP Summary

| Violation | Fix | Status |
|-----------|-----|--------|
| Fat interface (IWaker) | Split into IWaker + IReadinessPoller | ✅ Fixed |
| Forced implementation | Optional interfaces via composition | ✅ Fixed |
| Unnecessary coupling | Clients depend only on needed interfaces | ✅ Fixed |

**ISP Compliance**: ✅ Small, focused interfaces (role-based segregation)

---

## Component Principles

### Component Cohesion Principles

#### REP (Reuse/Release Equivalence Principle)

**Definition**: "The granule of reuse is the granule of release"

**Current Structure**:
```
src/monitoring/
├── entities/          # Domain entities (Endpoint, HealthStatus)
├── use_cases/         # Business logic (CheckHealth, WakeEndpoint)
├── adapters/          # External integrations
│   ├── health/        # Health check adapters (HF, Replicate, Modal)
│   ├── metrics/       # Metrics adapters (Prometheus)
│   └── config/        # Config adapters (YAML)
└── daemon.py          # Main daemon service
```

**Analysis**:
- ✅ All components released together as `endpoint-monitor:1.0`
- ✅ Versioning at daemon level (not individual adapters)
- ✅ Single Docker image, single deployment unit

**Compliance**: ✅ Good (monolithic release strategy appropriate for this size)

#### CCP (Common Closure Principle)

**Definition**: "Classes that change together belong together"

**Change Scenarios**:

1. **Adding new provider** (e.g., Modal)
   - Changes: Add `ModalHealthAdapter`, `ModalWaker`
   - Location: `src/monitoring/adapters/health/`, `src/monitoring/adapters/wake/`
   - ✅ All provider-specific code isolated to adapters

2. **Changing health check logic** (e.g., new endpoint state)
   - Changes: `EndpointState` enum, all use cases
   - Location: `src/monitoring/entities/`, `src/monitoring/use_cases/`
   - ✅ Domain changes isolated to domain layer

3. **Changing metrics format** (e.g., switch from Prometheus to OpenTelemetry)
   - Changes: `IMetricsExporter`, `PrometheusMetricsAdapter`
   - Location: `src/monitoring/adapters/metrics/`
   - ✅ Metrics changes isolated to adapters

**Package Structure** (enforcing CCP):

```python
# src/monitoring/adapters/health/__init__.py
"""Health check adapters (change together when adding providers)."""

from .base import IHealthChecker, BaseHealthChecker
from .hf_inference import HFInferenceHealthAdapter
from .replicate import ReplicateHealthAdapter
from .modal import ModalHealthAdapter

__all__ = [
    "IHealthChecker",
    "BaseHealthChecker",
    "HFInferenceHealthAdapter",
    "ReplicateHealthAdapter",
    "ModalHealthAdapter",
]
```

**Compliance**: ✅ Good (clear package boundaries based on change reasons)

#### CRP (Common Reuse Principle)

**Definition**: "Don't force users to depend on things they don't use"

**Current Issue**: All adapters bundled in single deployment

```python
# requirements.txt (currently monolithic)
aiohttp>=3.9.0        # Used by all adapters
prometheus-client     # Only used if Prometheus metrics enabled
pyyaml               # Only used if YAML config enabled
```

**Problem**: User only using HF + Prometheus forced to install YAML dependencies

**Fix**: Optional dependencies via extras

```python
# setup.py
setup(
    name="endpoint-monitor",
    install_requires=[
        "aiohttp>=3.9.0",  # Core dependency
    ],
    extras_require={
        "hf": ["huggingface-hub"],          # Only for HF adapter
        "replicate": ["replicate"],          # Only for Replicate adapter
        "modal": ["modal-client"],           # Only for Modal adapter
        "prometheus": ["prometheus-client"], # Only for Prometheus metrics
        "yaml": ["pyyaml"],                  # Only for YAML config
        "all": [
            "huggingface-hub",
            "replicate",
            "modal-client",
            "prometheus-client",
            "pyyaml",
        ],
    },
)

# Usage:
# pip install endpoint-monitor[hf,prometheus]  # Only HF + Prometheus
# pip install endpoint-monitor[all]            # All adapters
```

**Plugin Architecture** (advanced):

```python
# src/monitoring/adapters/health/registry.py
class HealthAdapterRegistry:
    """Registry for dynamically loaded health check adapters."""

    _adapters: Dict[str, Type[IHealthChecker]] = {}

    @classmethod
    def register(cls, provider: str, adapter: Type[IHealthChecker]):
        """Register health check adapter for provider."""
        cls._adapters[provider] = adapter

    @classmethod
    def get(cls, provider: str) -> Type[IHealthChecker]:
        """Get health check adapter for provider."""
        if provider not in cls._adapters:
            raise ValueError(f"No health check adapter for provider '{provider}'")
        return cls._adapters[provider]

# src/monitoring/adapters/health/hf_inference.py
try:
    from huggingface_hub import InferenceClient

    class HFInferenceHealthAdapter(IHealthChecker):
        # Implementation
        pass

    # Auto-register if HF dependencies available
    HealthAdapterRegistry.register("huggingface", HFInferenceHealthAdapter)

except ImportError:
    # HF adapter not available (dependencies not installed)
    pass

# Usage:
adapter_class = HealthAdapterRegistry.get(endpoint.provider)
adapter = adapter_class()
```

**Compliance**: ⚠️ Needs improvement (add optional dependencies + plugin registry)

### Component Coupling Principles

#### ADP (Acyclic Dependencies Principle)

**Definition**: "The dependency graph must have no cycles"

**Current Dependency Graph**:

```
daemon.py
  ↓
use_cases/
  ↓
entities/ ← interfaces/
  ↓
adapters/
```

**Check for Cycles**:
- daemon.py → use_cases → entities → interfaces (one direction) ✅
- adapters → interfaces (implements) ✅
- No back-references ✅

**Compliance**: ✅ No cycles (good layered architecture)

#### SDP (Stable Dependencies Principle)

**Definition**: "Depend in the direction of stability"

**Stability Metric**: I = Fan-out / (Fan-in + Fan-out)
- I = 0: Maximally stable (many dependents, no dependencies)
- I = 1: Maximally unstable (no dependents, many dependencies)

**Analysis**:

| Component | Fan-in | Fan-out | I | Stability |
|-----------|--------|---------|---|-----------|
| entities/ | 3 (use_cases, adapters, daemon) | 0 | 0.00 | Most stable |
| interfaces/ | 2 (use_cases, adapters) | 1 (entities) | 0.33 | Stable |
| use_cases/ | 1 (daemon) | 2 (interfaces, entities) | 0.67 | Unstable |
| adapters/ | 0 | 2 (interfaces, entities) | 1.00 | Most unstable |
| daemon.py | 0 | 3 (use_cases, adapters, entities) | 1.00 | Most unstable |

**Dependency Direction**:
- daemon (I=1.00) → use_cases (I=0.67) ✅ (unstable → less unstable)
- use_cases (I=0.67) → interfaces (I=0.33) ✅ (unstable → stable)
- adapters (I=1.00) → interfaces (I=0.33) ✅ (unstable → stable)

**Compliance**: ✅ Dependencies flow toward stability

#### SAP (Stable Abstractions Principle)

**Definition**: "Stable components should be abstract"

**Abstractness Metric**: A = Abstract classes / Total classes

**Analysis**:

| Component | Abstract | Concrete | A | Abstractness |
|-----------|----------|----------|---|--------------|
| entities/ | 0 | 3 (Endpoint, HealthStatus, FallbackChain) | 0.00 | Not abstract |
| interfaces/ | 4 (IHealthChecker, IWaker, IReadinessPoller, IMetricsExporter) | 1 (BaseHealthChecker) | 0.80 | Highly abstract |
| use_cases/ | 0 | 3 (CheckHealth, WakeEndpoint, ExecuteFallback) | 0.00 | Not abstract |
| adapters/ | 0 | 6 (HF, Replicate, Modal adapters) | 0.00 | Not abstract |

**Expected Relationship**: Stable components (low I) should be abstract (high A)

| Component | I (Instability) | A (Abstractness) | Expected | Actual |
|-----------|----------------|------------------|----------|--------|
| entities/ | 0.00 (stable) | 0.00 | Should be abstract | ❌ Concrete |
| interfaces/ | 0.33 (stable) | 0.80 | Should be abstract | ✅ Abstract |
| use_cases/ | 0.67 (unstable) | 0.00 | Can be concrete | ✅ Concrete |
| adapters/ | 1.00 (unstable) | 0.00 | Can be concrete | ✅ Concrete |

**Issue**: `entities/` is stable but concrete (violates SAP)

**Fix**: Make entities more abstract (use interfaces or abstract base classes)

```python
# Before: Concrete dataclass (stable + concrete = bad)
@dataclass(frozen=True)
class Endpoint:
    id: str
    provider: str
    url: str
    # ... concrete fields

# After: Abstract base + concrete implementations
class IEndpoint(ABC):
    """Abstract endpoint interface (stable)."""

    @property
    @abstractmethod
    def id(self) -> str:
        pass

    @property
    @abstractmethod
    def provider(self) -> str:
        pass

@dataclass(frozen=True)
class HTTPEndpoint(IEndpoint):
    """Concrete HTTP endpoint implementation."""

    _id: str
    _provider: str
    _url: str

    @property
    def id(self) -> str:
        return self._id

    @property
    def provider(self) -> str:
        return self._provider
```

**Trade-off**: More abstraction = more complexity
- For this project: Concrete dataclasses acceptable (pragmatic choice)
- For larger systems: Abstract entities preferred (better stability)

**Compliance**: ⚠️ Minor violation (acceptable trade-off for simplicity)

### Component Principles Summary

| Principle | Compliance | Action |
|-----------|-----------|---------|
| REP | ✅ Good | None (monolithic release OK) |
| CCP | ✅ Good | None (clear package boundaries) |
| CRP | ⚠️ Needs improvement | Add optional dependencies + plugin registry |
| ADP | ✅ Good | None (no cycles) |
| SDP | ✅ Good | None (dependencies flow toward stability) |
| SAP | ⚠️ Minor violation | Accept trade-off (concrete entities simpler) |

---

## Revised Architecture Summary

### Updated Interface Hierarchy

```python
# Domain Layer (Stable + Abstract)
class IHealthChecker(ABC):
    """Check endpoint health."""
    async def check(self, endpoint: Endpoint) -> HealthCheckResponse:
        pass

class IWaker(ABC):
    """Wake sleeping endpoint (basic capability)."""
    async def wake(self, endpoint: Endpoint) -> WakeResult:
        pass

class IReadinessPoller(ABC):
    """Poll endpoint readiness (optional capability)."""
    async def poll_until_ready(self, endpoint: Endpoint, timeout: int) -> bool:
        pass

class IMetricsExporter(ABC):
    """Export health metrics."""
    async def record_health_check(self, endpoint: Endpoint, status: HealthStatus):
        pass

# Adapter Layer (Unstable + Concrete)
class HFInferenceHealthAdapter(BaseHealthChecker):
    """HF-specific health check (LSP-compliant)."""
    async def _check_impl(self, endpoint: Endpoint) -> HealthCheckResponse:
        # Enforced: timeout via base class
        # Enforced: standardized error codes
        # Enforced: provider-agnostic response
        pass

class HFInferenceWaker(IWaker, IReadinessPoller):
    """HF-specific wake + polling (ISP-compliant)."""
    async def wake(self, endpoint: Endpoint) -> WakeResult:
        pass

    async def poll_until_ready(self, endpoint: Endpoint, timeout: int) -> bool:
        pass

class ReplicateWaker(IWaker):
    """Replicate-specific wake only (ISP-compliant, no forced polling)."""
    async def wake(self, endpoint: Endpoint) -> WakeResult:
        pass
```

### Benefits of Revised Design

1. ✅ **LSP Compliance**: All adapters substitutable
   - Standardized auth via `auth_config`
   - Standardized errors via `HealthCheckErrorCode`
   - Enforced invariants via `BaseHealthChecker`

2. ✅ **ISP Compliance**: Small, focused interfaces
   - `IWaker` (basic wake)
   - `IReadinessPoller` (optional polling)
   - Clients depend only on what they use

3. ✅ **Component Cohesion**: Clear boundaries
   - REP: Monolithic release (appropriate)
   - CCP: Changes isolated to layers
   - CRP: Optional dependencies (improvement needed)

4. ✅ **Component Coupling**: Healthy dependencies
   - ADP: No cycles
   - SDP: Flow toward stability
   - SAP: Acceptable trade-off (concrete entities)

---

## Testing Strategy (SOLID Validation)

### LSP Validation Tests

```python
# tests/solid/test_liskov_substitution.py
@pytest.mark.parametrize("adapter_class", [
    HFInferenceHealthAdapter,
    ReplicateHealthAdapter,
    ModalHealthAdapter,
])
async def test_health_check_adapters_substitutable(adapter_class):
    """Verify all health check adapters are LSP-compliant."""

    # Setup: Create endpoint with standardized config
    endpoint = Endpoint(
        id="test-endpoint",
        provider=adapter_class.PROVIDER_NAME,
        url="https://example.com/api",
        auth_config={"type": "bearer", "token_env": "TEST_TOKEN"},
        health_check_timeout=90
    )

    # Execute: Call check() on adapter
    adapter = adapter_class()
    response = await adapter.check(endpoint)

    # Assert: All adapters return same contract
    assert isinstance(response, HealthCheckResponse)
    assert response.status in EndpointState

    # Assert: Standardized error codes (if failed)
    if response.error_code:
        assert response.error_code in HealthCheckErrorCode

    # Assert: Timeout enforced (max 90s)
    # (Implicitly tested by BaseHealthChecker)
```

### ISP Validation Tests

```python
# tests/solid/test_interface_segregation.py
def test_waker_interface_minimal():
    """Verify IWaker interface is minimal (only wake method)."""

    # IWaker should only have wake() method
    waker_methods = [m for m in dir(IWaker) if not m.startswith('_')]
    assert waker_methods == ['wake']

def test_readiness_poller_interface_minimal():
    """Verify IReadinessPoller interface is minimal (only poll method)."""

    poller_methods = [m for m in dir(IReadinessPoller) if not m.startswith('_')]
    assert poller_methods == ['poll_until_ready']

async def test_replicate_waker_not_forced_to_implement_polling():
    """Verify Replicate adapter not forced to implement polling."""

    # ReplicateWaker should only implement IWaker, not IReadinessPoller
    assert isinstance(ReplicateWaker(), IWaker)
    assert not isinstance(ReplicateWaker(), IReadinessPoller)
```

---

## Conclusion

### SOLID Compliance Summary

| Principle | Before | After | Status |
|-----------|--------|-------|--------|
| **S**RP | ✅ Good | ✅ Good | No changes needed |
| **O**CP | ✅ Good | ✅ Good | No changes needed |
| **L**SP | ❌ Violations | ✅ Fixed | Standardized contracts |
| **I**SP | ❌ Fat interface | ✅ Fixed | Split interfaces |
| **D**IP | ✅ Good | ✅ Good | No changes needed |

### Component Principles Summary

| Principle | Status | Notes |
|-----------|--------|-------|
| REP | ✅ Good | Monolithic release appropriate |
| CCP | ✅ Good | Clear layer boundaries |
| CRP | ⚠️ Improvement needed | Add optional dependencies |
| ADP | ✅ Good | No dependency cycles |
| SDP | ✅ Good | Dependencies flow toward stability |
| SAP | ⚠️ Minor violation | Acceptable trade-off |

### Key Improvements Made

1. **LSP Compliance**:
   - Standardized `auth_config` for consistent authentication
   - Standardized `HealthCheckErrorCode` for provider-agnostic errors
   - `BaseHealthChecker` enforces timeout invariants

2. **ISP Compliance**:
   - Split `IWaker` into `IWaker` + `IReadinessPoller`
   - Clients depend only on needed capabilities
   - Adapters not forced to implement unused methods

3. **Better Component Design**:
   - Optional dependencies via `extras_require`
   - Plugin registry for dynamic adapter loading
   - Clear stability/abstractness relationship

**Architecture Quality**: Production-ready with strong SOLID and Clean Architecture compliance ✅
