#!/usr/bin/env python3
"""
SYD2 Autonomous Agent - Phase 1 Implementation
Continuously exercises UI-CLI on syd2.jacobhollis.com, collects metrics, and generates improvements.

Architecture: Clean Architecture with composition over inheritance
Design: Category theory-based task generation, SSH automation, metrics analysis
"""

import asyncio
import json
import logging
import random
import socket
import subprocess
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import paramiko
import yaml

# ==========================
# CUSTOM EXCEPTIONS
# ==========================


class SYD2AgentError(Exception):
    """Base exception for SYD2 Agent"""

    pass


class SSHConnectionError(SYD2AgentError):
    """SSH connection failures"""

    pass


class SSHTimeout(SYD2AgentError):
    """SSH command timeout"""

    pass


class TaskGenerationError(SYD2AgentError):
    """Task generation failures"""

    pass


class MetricsCollectionError(SYD2AgentError):
    """Metrics collection failures"""

    pass


class ConfigurationError(SYD2AgentError):
    """Configuration loading errors"""

    pass


# ==========================
# DATA MODELS
# ==========================


@dataclass
class Task:
    """Represents a generated task"""

    task_id: str
    category: str
    sub_type: str
    description: str
    task_text: str
    difficulty: str
    params: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ExecutionResult:
    """Result of SSH command execution"""

    task_id: str
    success: bool
    stdout: str
    stderr: str
    exit_code: int
    latency: float  # seconds
    timestamp: str
    error_message: Optional[str] = None


@dataclass
class Metric:
    """Collected metric from execution"""

    task_id: str
    category: str
    success: bool
    latency: float
    timestamp: str
    routing_info: Optional[Dict] = None
    error_type: Optional[str] = None


# ==========================
# ABSTRACT BASE CLASS
# ==========================


class AbstractManager(ABC):
    """Base interface for all managers - Dependency Inversion Principle"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize manager resources"""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Cleanup resources"""
        pass


# ==========================
# SSH MANAGER
# ==========================


class SSHManager(AbstractManager):
    """
    Secure SSH automation using Paramiko
    Features: key-based auth, connection pooling, timeout handling, retry logic
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.client: Optional[paramiko.SSHClient] = None
        self.host = config["server"]["host"]
        self.user = config["server"]["user"]
        self.key_path = Path(config["server"]["ssh_key"]).expanduser()
        self.timeout = config["server"]["timeout"]
        self.connected = False

    async def initialize(self) -> None:
        """Initialize SSH connection"""
        await self.connect()

    async def connect(self) -> None:
        """Establish SSH connection with key-based auth"""
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # Load private key
            if not self.key_path.exists():
                raise SSHConnectionError(f"SSH key not found: {self.key_path}")

            private_key = paramiko.Ed25519Key.from_private_key_file(str(self.key_path))

            # Connect
            self.logger.info(f"Connecting to {self.user}@{self.host}...")
            self.client.connect(
                hostname=self.host,
                username=self.user,
                pkey=private_key,
                timeout=self.timeout,
                banner_timeout=30,
            )

            self.connected = True
            self.logger.info(f"Successfully connected to {self.host}")

        except (
            paramiko.SSHException,
            paramiko.AuthenticationException,
            socket.error,
        ) as e:
            raise SSHConnectionError(f"SSH connection failed: {e}")

    async def execute_command(
        self, cmd: str, timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute command on remote server
        Returns: dict with stdout, stderr, exit_code, timestamp
        """
        if not self.connected or not self.client:
            await self.connect()

        timeout = timeout or self.timeout

        try:
            start_time = datetime.now()

            stdin, stdout, stderr = self.client.exec_command(cmd, timeout=timeout)

            # Wait for command completion
            exit_code = stdout.channel.recv_exit_status()

            # Read output
            stdout_str = stdout.read().decode("utf-8", errors="replace")
            stderr_str = stderr.read().decode("utf-8", errors="replace")

            latency = (datetime.now() - start_time).total_seconds()

            return {
                "stdout": stdout_str,
                "stderr": stderr_str,
                "exit_code": exit_code,
                "timestamp": datetime.now().isoformat(),
                "latency": latency,
            }

        except socket.timeout:
            self.logger.warning(f"Command timed out after {timeout}s: {cmd[:100]}")
            raise SSHTimeout(f"Command timed out after {timeout}s")

        except Exception as e:
            self.logger.error(f"Command execution failed: {e}")
            raise SSHConnectionError(f"Command execution failed: {e}")

    async def sync_metrics(
        self, remote_path: str, local_path: str
    ) -> Tuple[bool, str]:
        """
        Rsync metrics from remote to local
        Returns: (success, message)
        """
        try:
            local_dir = Path(local_path)
            local_dir.mkdir(parents=True, exist_ok=True)

            cmd = [
                "rsync",
                "-avz",
                "--timeout=30",
                f"{self.user}@{self.host}:{remote_path}/",
                f"{local_path}/",
            ]

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=60, check=False
            )

            if result.returncode == 0:
                self.logger.info(f"Successfully synced metrics from {remote_path}")
                return True, result.stdout
            else:
                self.logger.warning(
                    f"Rsync failed (code {result.returncode}): {result.stderr}"
                )
                return False, result.stderr

        except subprocess.TimeoutExpired:
            self.logger.error("Rsync timed out")
            return False, "Timeout"
        except Exception as e:
            self.logger.error(f"Rsync failed: {e}")
            return False, str(e)

    async def shutdown(self) -> None:
        """Close SSH connection"""
        if self.client:
            self.client.close()
            self.connected = False
            self.logger.info("SSH connection closed")


# ==========================
# TASK GENERATOR
# ==========================


class TaskGenerator(AbstractManager):
    """
    Category theory-based task generation from YAML templates
    Supports: composition (∘), parallel execution (×), difficulty scaling
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.templates: Dict[str, Any] = {}
        self.template_path = Path("config/agent_task_templates.yml")
        self.task_counter = 0

    async def initialize(self) -> None:
        """Load task templates from YAML"""
        try:
            if not self.template_path.exists():
                raise TaskGenerationError(
                    f"Template file not found: {self.template_path}"
                )

            with open(self.template_path, "r") as f:
                self.templates = yaml.safe_load(f)

            self.logger.info(f"Loaded {len(self.templates)} task templates")

        except yaml.YAMLError as e:
            raise TaskGenerationError(f"Failed to parse template YAML: {e}")

    def generate_task(self, category: Optional[str] = None) -> Task:
        """
        Generate random task from templates
        Args:
            category: Optional category filter (research, testing, etc.)
        Returns:
            Task object with parameterized task text
        """
        # Filter templates by category if specified
        if category:
            templates = {
                k: v
                for k, v in self.templates.items()
                if v.get("category") == category
            }
            if not templates:
                raise TaskGenerationError(f"No templates found for category: {category}")
        else:
            templates = self.templates

        # Select random template
        template_name = random.choice(list(templates.keys()))
        template = templates[template_name]

        # Parameterize task
        task_text = template["task_template"]
        params = template.get("params", {})

        # Substitute random parameter values
        for param_name, param_values in params.items():
            if param_values:  # Skip empty param lists
                value = random.choice(param_values)
                task_text = task_text.replace(f"{{{{{param_name}}}}}", str(value))

        # Generate unique task ID
        self.task_counter += 1
        task_id = f"syd2_task_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self.task_counter:04d}"

        return Task(
            task_id=task_id,
            category=template["category"],
            sub_type=template["sub_type"],
            description=template["description"],
            task_text=task_text,
            difficulty=template.get("difficulty", "medium"),
            params=params,
        )

    def compose_tasks(self, t1: Task, t2: Task, operator: str) -> Task:
        """
        Compose two tasks using category theory operators
        Args:
            t1, t2: Tasks to compose
            operator: '∘' for sequential, '×' for parallel
        Returns:
            Composed task
        """
        if operator == "∘":
            # Sequential composition: execute t2 then t1
            composed_text = f"{t2.task_text}\n\nThen:\n{t1.task_text}"
        elif operator == "×":
            # Parallel composition: execute both concurrently
            composed_text = (
                f"Execute in parallel:\nTask A: {t1.task_text}\nTask B: {t2.task_text}"
            )
        else:
            raise TaskGenerationError(f"Unknown operator: {operator}")

        self.task_counter += 1
        task_id = f"syd2_composed_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self.task_counter:04d}"

        return Task(
            task_id=task_id,
            category="composed",
            sub_type=f"{t1.sub_type}_{operator}_{t2.sub_type}",
            description=f"Composed task ({operator})",
            task_text=composed_text,
            difficulty="hard",
        )

    async def shutdown(self) -> None:
        """No cleanup needed for task generator"""
        pass


# ==========================
# METRICS COLLECTOR
# ==========================


class MetricsCollector(AbstractManager):
    """
    Collects and stores execution metrics to JSON
    Supports: rsync from remote, local storage, statistical analysis
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.local_dir = Path(config["metrics"]["local_dir"])
        self.remote_dir = config["metrics"]["remote_dir"]
        self.metrics: List[Metric] = []

    async def initialize(self) -> None:
        """Create metrics directory"""
        self.local_dir.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"Metrics directory: {self.local_dir}")

    async def collect(
        self, task: Task, result: ExecutionResult
    ) -> Metric:
        """
        Create metric from execution result
        """
        metric = Metric(
            task_id=task.task_id,
            category=task.category,
            success=result.success,
            latency=result.latency,
            timestamp=result.timestamp,
            error_type=result.error_message if not result.success else None,
        )

        self.metrics.append(metric)
        return metric

    async def store(self, metric: Metric, session_id: str) -> None:
        """
        Store metric to JSON file
        Format: data/syd2_metrics/session_YYYYMMDD_HHMMSS.json
        """
        session_file = self.local_dir / f"session_{session_id}.json"

        # Load existing session data or create new
        if session_file.exists():
            with open(session_file, "r") as f:
                session_data = json.load(f)
        else:
            session_data = {
                "session_id": session_id,
                "start_time": datetime.now().isoformat(),
                "metrics": [],
            }

        # Append metric
        session_data["metrics"].append({
            "task_id": metric.task_id,
            "category": metric.category,
            "success": metric.success,
            "latency": metric.latency,
            "timestamp": metric.timestamp,
            "error_type": metric.error_type,
        })

        session_data["last_updated"] = datetime.now().isoformat()

        # Write back
        with open(session_file, "w") as f:
            json.dump(session_data, f, indent=2)

        self.logger.debug(f"Stored metric to {session_file}")

    def get_recent(self, count: int = 100) -> List[Metric]:
        """Get most recent N metrics"""
        return self.metrics[-count:]

    async def shutdown(self) -> None:
        """No cleanup needed"""
        pass


# ==========================
# MAIN ORCHESTRATOR
# ==========================


class SYD2Agent:
    """
    Main autonomous agent orchestrator
    Composes: SSHManager, TaskGenerator, MetricsCollector
    """

    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)
        self.logger = self._setup_logging()

        # Initialize managers (Dependency Injection)
        self.ssh_manager = SSHManager(self.config)
        self.task_generator = TaskGenerator(self.config)
        self.metrics_collector = MetricsCollector(self.config)

        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.running = False

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load YAML configuration"""
        try:
            with open(config_path, "r") as f:
                return yaml.safe_load(f)
        except (FileNotFoundError, yaml.YAMLError) as e:
            raise ConfigurationError(f"Failed to load config: {e}")

    def _setup_logging(self) -> logging.Logger:
        """Setup structured JSON logging"""
        log_config = self.config["logging"]
        log_file = Path(log_config["file"])
        log_file.parent.mkdir(parents=True, exist_ok=True)

        logger = logging.getLogger("SYD2Agent")
        logger.setLevel(getattr(logging, log_config["level"]))

        # Rotating file handler
        handler = RotatingFileHandler(
            log_file,
            maxBytes=log_config.get("max_bytes", 10485760),
            backupCount=log_config.get("backup_count", 5),
        )

        # JSON-like formatter
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
            '"logger": "%(name)s", "message": "%(message)s"}'
        )
        handler.setFormatter(formatter)

        logger.addHandler(handler)

        # Also log to console
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(console_handler)

        return logger

    async def initialize(self) -> None:
        """Initialize all managers"""
        self.logger.info("=" * 60)
        self.logger.info("SYD2 Autonomous Agent - Phase 1")
        self.logger.info(f"Session ID: {self.session_id}")
        self.logger.info("=" * 60)

        self.logger.info("Initializing managers...")
        await self.ssh_manager.initialize()
        await self.task_generator.initialize()
        await self.metrics_collector.initialize()
        self.logger.info("All managers initialized successfully")

    async def run(self, duration_hours: float = 24) -> None:
        """
        Main execution loop
        Args:
            duration_hours: How long to run (default 24 hours)
        """
        try:
            await self.initialize()

            self.running = True
            start_time = datetime.now()
            end_time = start_time + timedelta(hours=duration_hours)

            tasks_per_hour = self.config["execution"]["tasks_per_hour"]
            pause_between = self.config["execution"]["pause_between_tasks"]

            self.logger.info(
                f"Starting execution loop: {tasks_per_hour} tasks/hour for {duration_hours}h"
            )

            task_count = 0

            while self.running and datetime.now() < end_time:
                try:
                    # 1. Generate task
                    task = self.task_generator.generate_task()
                    task_count += 1

                    self.logger.info(
                        f"[Task {task_count}] Generated: {task.category}/{task.sub_type} "
                        f"(difficulty: {task.difficulty})"
                    )
                    self.logger.debug(f"Task text: {task.task_text[:200]}...")

                    # 2. Build UI-CLI command
                    ui_cli_config = self.config["ui_cli"]
                    cmd = (
                        f"cd /opt/unified-intelligence-cli && "
                        f"{ui_cli_config['executable']} "
                        f"--task '{task.task_text}' "
                        f"--provider {ui_cli_config['default_provider']} "
                        f"--routing {ui_cli_config['routing']} "
                        f"--agents {ui_cli_config['agents']} "
                        f"--orchestrator {ui_cli_config['orchestrator']} "
                        f"--timeout {ui_cli_config['timeout']} "
                        f"{'--collect-metrics' if ui_cli_config['collect_metrics'] else ''}"
                    )

                    # 3. Execute via SSH
                    self.logger.info(f"[Task {task_count}] Executing via SSH...")
                    start_exec = datetime.now()

                    try:
                        ssh_result = await self.ssh_manager.execute_command(
                            cmd, timeout=ui_cli_config["timeout"]
                        )

                        success = ssh_result["exit_code"] == 0
                        error_msg = None if success else ssh_result["stderr"]

                        result = ExecutionResult(
                            task_id=task.task_id,
                            success=success,
                            stdout=ssh_result["stdout"],
                            stderr=ssh_result["stderr"],
                            exit_code=ssh_result["exit_code"],
                            latency=ssh_result["latency"],
                            timestamp=ssh_result["timestamp"],
                            error_message=error_msg,
                        )

                        self.logger.info(
                            f"[Task {task_count}] Completed: "
                            f"{'SUCCESS' if success else 'FAILED'} "
                            f"(latency: {result.latency:.2f}s)"
                        )

                        if not success:
                            self.logger.warning(
                                f"[Task {task_count}] Error: {error_msg[:200]}"
                            )

                    except (SSHTimeout, SSHConnectionError) as e:
                        self.logger.error(f"[Task {task_count}] SSH error: {e}")
                        result = ExecutionResult(
                            task_id=task.task_id,
                            success=False,
                            stdout="",
                            stderr=str(e),
                            exit_code=-1,
                            latency=(datetime.now() - start_exec).total_seconds(),
                            timestamp=datetime.now().isoformat(),
                            error_message=str(e),
                        )

                    # 4. Collect metrics
                    metric = await self.metrics_collector.collect(task, result)
                    await self.metrics_collector.store(metric, self.session_id)

                    # 5. Pause between tasks
                    self.logger.info(
                        f"[Task {task_count}] Waiting {pause_between}s before next task..."
                    )
                    await asyncio.sleep(pause_between)

                except TaskGenerationError as e:
                    self.logger.error(f"Task generation failed: {e}")
                    await asyncio.sleep(60)  # Wait before retry

                except Exception as e:
                    self.logger.error(f"Unexpected error in execution loop: {e}")
                    await asyncio.sleep(60)

            self.logger.info(
                f"Execution loop completed. Total tasks executed: {task_count}"
            )

        except KeyboardInterrupt:
            self.logger.info("Interrupted by user")
            self.running = False

        finally:
            await self.shutdown()

    async def shutdown(self) -> None:
        """Cleanup all resources"""
        self.logger.info("Shutting down...")
        await self.ssh_manager.shutdown()
        await self.task_generator.shutdown()
        await self.metrics_collector.shutdown()
        self.logger.info("Shutdown complete")


# ==========================
# MAIN ENTRY POINT
# ==========================


async def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="SYD2 Autonomous Agent - Continuous UI-CLI exerciser"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config/syd2_agent.yml",
        help="Path to configuration file (default: config/syd2_agent.yml)",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=24.0,
        help="Duration in hours (default: 24.0)",
    )

    args = parser.parse_args()

    try:
        agent = SYD2Agent(args.config)
        await agent.run(duration_hours=args.duration)

    except ConfigurationError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)

    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
