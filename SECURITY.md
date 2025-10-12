# Security Documentation

This document outlines security considerations, current protections, and best practices for using the Unified Intelligence CLI.

## Table of Contents

- [Overview](#overview)
- [Command Execution Security](#command-execution-security)
- [File Operation Safety](#file-operation-safety)
- [LLM API Security](#llm-api-security)
- [Best Practices](#best-practices)
- [Threat Model](#threat-model)
- [Future Enhancements](#future-enhancements)

---

## Overview

The Unified Intelligence CLI enables LLM agents to execute commands and file operations on the local system. This provides powerful automation capabilities but requires careful security considerations.

**Security Philosophy**: Trust but verify. The CLI is designed for trusted local development workflows, not untrusted remote execution.

---

## Command Execution Security

### Current Protections

The `run_command()` tool in `src/tools.py` implements several safety mechanisms:

#### 1. Timeout Protection
```python
# Commands automatically timeout after 30 seconds
timeout=30  # Prevents infinite loops or hanging processes
```

**Protection Against**: Denial of service, resource exhaustion, infinite loops

**Example**:
```bash
# Safe: Times out after 30s
run_command("sleep 60")  # Raises CommandTimeoutError
```

#### 2. Exception Handling
```python
# All command failures raise typed exceptions
try:
    run_command("dangerous_command")
except CommandTimeoutError:
    # Handle timeout gracefully
except CommandExecutionError:
    # Handle execution failure
```

**Protection Against**: Unhandled errors, crashes, silent failures

#### 3. Working Directory Control
```python
# Commands execute in specified directory
run_command("ls", cwd="/safe/workspace")
```

**Protection Against**: Accidental system-wide changes

### Security Trade-offs

#### Current Approach: **Full Shell Access**

**Advantages**:
- ✅ Maximum flexibility for LLM agents
- ✅ No artificial limitations on legitimate tasks
- ✅ Simpler implementation and maintenance
- ✅ Better for trusted development environments

**Risks**:
- ⚠️ Agents can execute any shell command
- ⚠️ Potential for destructive operations (rm, format, etc.)
- ⚠️ Dependent on LLM making safe decisions

**Mitigation**: Use in trusted environments only (local development, CI/CD with isolated containers)

#### Alternative Approach: **Command Whitelist**

**Advantages**:
- ✅ Explicit control over allowed commands
- ✅ Prevents dangerous operations by design
- ✅ Easier to audit and reason about

**Disadvantages**:
- ❌ Limits agent autonomy and effectiveness
- ❌ Requires constant maintenance as needs evolve
- ❌ Can be bypassed via shell features (pipes, &&, etc.)
- ❌ May block legitimate use cases

**Example Whitelist Implementation**:
```python
ALLOWED_COMMANDS = {
    # Safe read-only operations
    'ls', 'cat', 'head', 'tail', 'grep', 'find', 'pwd',

    # Version control
    'git status', 'git log', 'git diff', 'git add', 'git commit',

    # Testing
    'pytest', 'python', 'node', 'npm test',

    # Build
    'make', 'cmake', 'npm run build'
}

def is_command_allowed(command: str) -> bool:
    """Check if command is in whitelist."""
    base_cmd = command.split()[0]
    return base_cmd in ALLOWED_COMMANDS
```

**Bypass Example**:
```bash
# Whitelist allows 'git', but can be misused
git status && rm -rf /  # Dangerous!
```

### Recommended Security Model

**For Local Development** (Current):
- ✅ Use full shell access for maximum productivity
- ✅ Run in user-owned directories only
- ✅ Review LLM outputs before executing critical operations
- ✅ Use version control to track all changes

**For Production/CI** (Future Enhancement):
- 🔄 Run in isolated Docker containers
- 🔄 Use read-only mounts for sensitive directories
- 🔄 Implement command audit logging
- 🔄 Add pre-execution approval hooks

---

## File Operation Safety

### Current Protections

#### 1. Size Limits
```python
# Files limited to 100KB to prevent memory exhaustion
FILE_SIZE_LIMIT = 100000  # 100KB

if file_size > FILE_SIZE_LIMIT:
    raise FileSizeLimitError(path, file_size, FILE_SIZE_LIMIT)
```

**Protection Against**: Memory exhaustion, accidental processing of large files

#### 2. Path Validation
```python
# Paths are resolved to absolute paths
path = Path(file_path).resolve()

# Parent directories created safely
path.parent.mkdir(parents=True, exist_ok=True)
```

**Protection Against**: Path traversal issues, relative path confusion

#### 3. Explicit Error Types
```python
# File operations raise typed exceptions
raise FileNotFoundError(file_path)
raise FileWriteError(file_path, reason)
raise DirectoryNotFoundError(directory)
```

**Protection Against**: Silent failures, unclear error states

### Dangerous Operations

The following operations are **NOT** protected against:

⚠️ **Overwriting important files**:
```python
# No confirmation before overwrite
write_file_content("/etc/passwd", "malicious")
```

⚠️ **Reading sensitive files**:
```python
# No restrictions on file paths
read_file_content("/home/user/.ssh/id_rsa")
```

**Mitigation**:
- Run CLI in isolated workspace directories
- Use non-privileged user accounts
- Store sensitive files outside workspace
- Review agent actions before execution

### Safe Usage Pattern

```python
# Create isolated workspace
workspace = Path("/home/user/projects/myproject")
workspace.mkdir(exist_ok=True)

# All operations within workspace
run_command("ls", cwd=str(workspace))
write_file_content(str(workspace / "output.txt"), content)
```

---

## LLM API Security

### API Key Protection

**Current Approach**:
```bash
# Store API keys in .env file (gitignored)
echo "XAI_API_KEY=your_key" > .env
```

**Best Practices**:
- ✅ Never commit `.env` files to version control
- ✅ Use environment variables in production
- ✅ Rotate keys regularly
- ✅ Use separate keys for dev/staging/prod

**Verification**:
```bash
# Check .gitignore includes .env
grep "^\.env$" .gitignore

# Verify no keys in git history
git log --all --full-history --source --patch -S "XAI_API_KEY"
```

### Data Privacy

**What Gets Sent to LLM**:
- ✅ Task descriptions
- ✅ Agent role and capabilities
- ✅ Previous task results (in context)
- ✅ Tool execution results

**What Should NOT Be Sent**:
- ❌ API keys, credentials, tokens
- ❌ Personal information (PII)
- ❌ Proprietary code (unless authorized)
- ❌ Sensitive file contents

**Mitigation**:
```bash
# Review task descriptions before submission
--task "Analyze config.json"  # Safe
--task "Process /etc/passwd"  # Review carefully!
```

---

## Best Practices

### For Developers

1. **Workspace Isolation**
   ```bash
   # Create dedicated project directory
   mkdir ~/safe-workspace
   cd ~/safe-workspace

   # Run CLI only in isolated workspace
   python3 src/main.py --task "..." --provider mock
   ```

2. **Version Control Everything**
   ```bash
   # Initialize git before starting
   git init
   git add .
   git commit -m "Initial state"

   # Review changes after agent actions
   git diff
   ```

3. **Start with Mock Provider**
   ```bash
   # Test with mock provider first (no API calls)
   --provider mock

   # Use real provider only after verification
   --provider grok
   ```

4. **Review Before Production**
   ```bash
   # Always review agent outputs
   --verbose  # See detailed execution

   # Manually verify critical operations
   ```

### For CI/CD

1. **Use Docker Isolation**
   ```dockerfile
   # Run in isolated container
   FROM python:3.12-slim
   RUN useradd -m appuser
   USER appuser
   WORKDIR /workspace
   ```

2. **Read-Only Mounts**
   ```bash
   docker run -v $(pwd):/workspace:ro unified-cli
   ```

3. **Audit Logging**
   ```python
   # Log all command executions
   logger.info(f"Executing: {command}")
   ```

### For API Key Management

1. **Use Secret Managers**
   ```bash
   # Production: Use secret manager
   export XAI_API_KEY=$(aws secretsmanager get-secret-value ...)
   ```

2. **Least Privilege**
   ```bash
   # Use API keys with minimal scopes
   # Rotate regularly
   ```

---

## Threat Model

### In Scope (Defended)

✅ **Timeout Attacks**: Commands timing out are handled gracefully
✅ **Memory Exhaustion**: File size limits prevent large file processing
✅ **Path Confusion**: Absolute paths prevent relative path issues
✅ **Silent Failures**: Explicit exception types ensure errors are visible

### Out of Scope (User Responsibility)

⚠️ **Malicious LLM Outputs**: Assuming LLM is benign (trusted provider)
⚠️ **Credential Theft**: User must not provide secrets in task descriptions
⚠️ **Data Exfiltration**: No network egress control (runs on user's system)
⚠️ **Privilege Escalation**: No sudo/root prevention (user's responsibility)

### Attack Scenarios

#### Scenario 1: Destructive Command
```
Attacker: Tricks LLM into executing `rm -rf /`
Protection: None (user responsibility to run as non-root, review actions)
Mitigation: Use Docker, review verbose output, version control
```

#### Scenario 2: Credential Harvest
```
Attacker: LLM searches for and reads ~/.ssh/id_rsa
Protection: None (file reading is legitimate feature)
Mitigation: Run in isolated workspace, store secrets elsewhere
```

#### Scenario 3: Code Injection
```
Attacker: Injects malicious code via task description
Protection: None (arbitrary code execution is the feature)
Mitigation: Review task descriptions, use mock provider for testing
```

---

## Future Enhancements

### Planned Security Features

1. **Command Audit Log** (Rec #5 Extension)
   ```python
   # Log all commands to audit file
   with open("audit.log", "a") as f:
       f.write(f"{timestamp} | {command} | {result}\n")
   ```

2. **Pre-execution Hooks** (Future)
   ```python
   # Allow user approval before dangerous commands
   if is_dangerous(command):
       if not user_approval(command):
           raise SecurityException("User denied execution")
   ```

3. **Workspace Constraints** (Future)
   ```python
   # Restrict all operations to workspace directory
   if not path.is_relative_to(WORKSPACE):
       raise SecurityException("Access outside workspace denied")
   ```

4. **Command Whitelist Mode** (Optional)
   ```bash
   # Optional strict mode with whitelist
   --security-mode=strict
   ```

### Community Contributions

Security enhancements welcome! Please submit issues or PRs at:
- GitHub: [project-url]
- Security issues: security@project.com (private disclosure)

---

## Disclosure Policy

If you discover a security vulnerability:

1. **Do NOT** open a public issue
2. Email: security@project.com with details
3. Allow 90 days for fix before public disclosure
4. Responsible disclosure will be acknowledged

---

## Summary

**Current Security Model**: Trusted local development environment

**Key Principle**: The CLI is a **power tool** for developers, not a sandboxed system. Use with the same care you would use when running any script with shell access.

**Recommended Use Cases**:
- ✅ Local development workflows
- ✅ Automated testing in CI/CD containers
- ✅ Code generation and refactoring
- ✅ Documentation and analysis tasks

**NOT Recommended**:
- ❌ Running untrusted task descriptions
- ❌ Production systems without containerization
- ❌ Shared multi-user environments
- ❌ Systems with sensitive data in workspace

For questions or security concerns, see: [CLAUDE.md](CLAUDE.md) or open an issue.