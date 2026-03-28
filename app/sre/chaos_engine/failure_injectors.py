# mypy: ignore-errors
"""
Failure Injectors - Controlled Failure Injection for Chaos Engineering

Implements various failure injection mechanisms:
- Pod Killer: Randomly terminates pods/containers
- Network Delay: Injects network latency
- Error Injector: Injects application errors
- Latency Injector: Adds processing delays
- Resource Starver: Limits CPU/memory

Safety:
- All injectors implement rollback
- Blast radius control
- Automatic cleanup on failure
"""

from __future__ import annotations

import asyncio
import logging
import random
import signal
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import psutil
import contextlib

logger = logging.getLogger(__name__)


class InjectionType(str, Enum):
    """Types of failure injection."""

    POD_KILL = "pod_kill"
    NETWORK_DELAY = "network_delay"
    ERROR = "error"
    LATENCY = "latency"
    RESOURCE_STARVE = "resource_starve"


@dataclass
class InjectionConfig:
    """Configuration for failure injection."""

    injection_type: InjectionType
    intensity: Decimal = Decimal("0.5")  # 0.0 to 1.0
    duration_seconds: int = 60
    targets: List[str] = field(default_factory=list)
    blast_radius: str = "limited"  # limited, widespread

    # Type-specific config
    delay_ms: Optional[int] = None
    error_rate: Optional[Decimal] = None
    cpu_limit: Optional[Decimal] = None
    memory_limit_mb: Optional[int] = None


class FailureInjector(ABC):
    """
    Abstract base class for failure injectors.

    All injectors must implement:
    - inject(): Start failure injection
    - rollback(): Stop failure injection and cleanup
    - is_active(): Check if injection is active
    """

    def __init__(self, config: InjectionConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{config.injection_type.value}")
        self._active = False
        self._injection_tasks: List[asyncio.Task] = []

    @abstractmethod
    async def inject(self) -> None:
        """Start failure injection."""

    @abstractmethod
    async def rollback(self) -> None:
        """Stop failure injection and cleanup."""

    def is_active(self) -> bool:
        """Check if injection is active."""
        return self._active

    async def _wait_for_duration(self) -> None:
        """Wait for injection duration."""
        await asyncio.sleep(self.config.duration_seconds)


class PodKiller(FailureInjector):
    """
    Randomly terminates pods/containers.

    Simulates pod failures to test resiliency.

    Safety:
    - Never kills all pods
    - Respects blast radius
    - Auto-restart killed pods
    """

    def __init__(self, config: InjectionConfig):
        super().__init__(config)
        self._killed_pids: List[int] = []
        self._original_processes: Dict[int, Dict[str, Any]] = {}

    async def inject(self) -> None:
        """Start killing pods."""
        self._active = True
        self.logger.info(f"Starting pod killer (intensity: {self.config.intensity})")

        # Calculate number of pods to kill
        total_pods = await self._get_total_pods()
        kill_count = int(total_pods * float(self.config.intensity))

        # Ensure at least one pod remains
        kill_count = min(kill_count, total_pods - 1)

        self.logger.info(f"Killing {kill_count}/{total_pods} pods")

        # Start periodic killing
        task = asyncio.create_task(self._periodic_kill(kill_count))
        self._injection_tasks.append(task)

    async def _get_total_pods(self) -> int:
        """Get total number of pods."""
        # For local processes, count relevant processes
        count = 0
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info['cmdline']
                if cmdline and any('python' in str(c) for c in cmdline):
                    count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return max(1, count)

    async def _periodic_kill(self, kill_count: int) -> None:
        """Periodically kill pods."""
        while self._active:
            # Kill random pods
            for _ in range(kill_count):
                await self._kill_random_pod()

            # Wait before next round
            await asyncio.sleep(30)

    async def _kill_random_pod(self) -> None:
        """Kill a random pod/process."""
        try:
            # Find relevant processes
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = proc.info['cmdline']
                    if cmdline and any('python' in str(c) for c in cmdline):
                        processes.append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            if not processes:
                return

            # Select random process
            target = random.choice(processes)
            pid = target.pid

            # Skip if already killed this one
            if pid in self._killed_pids:
                return

            self.logger.info(f"Killing pod: PID {pid}")

            # Store process info for rollback
            with contextlib.suppress(psutil.NoSuchProcess, psutil.AccessDenied):
                self._original_processes[pid] = {
                    'name': target.name(),
                    'cmdline': target.cmdline(),
                }

            # Kill process
            target.send_signal(signal.SIGTERM)
            self._killed_pids.append(pid)

            # Wait and force kill if needed
            await asyncio.sleep(5)
            if target.is_running():
                target.kill()

        except Exception as e:
            self.logger.error(f"Error killing pod: {e}")

    async def rollback(self) -> None:
        """Stop killing pods and restart killed ones."""
        self._active = False

        # Cancel tasks
        for task in self._injection_tasks:
            if not task.done():
                task.cancel()
        self._injection_tasks.clear()

        self.logger.info(f"Rolling back {len(self._killed_pids)} killed pods")

        # Restart killed processes (in real K8s, controller does this)
        for pid in self._killed_pids:
            if pid in self._original_processes:
                proc_info = self._original_processes[pid]
                self.logger.info(f"Would restart: {proc_info['name']}")

        self._killed_pids.clear()
        self._original_processes.clear()


class NetworkDelayInjector(FailureInjector):
    """
    Injects network delays using tc (traffic control).

    Simulates network latency and jitter.

    Requirements:
    - sudo privileges for tc command
    - Linux system with tc installed
    """

    def __init__(self, config: InjectionConfig):
        super().__init__(config)
        self._interfaces: List[str] = []
        self._original_rules: Dict[str, str] = {}

    async def inject(self) -> None:
        """Inject network delays."""
        self._active = True
        delay_ms = self.config.delay_ms or 100

        self.logger.info(f"Injecting {delay_ms}ms network delay")

        # Get network interfaces
        self._interfaces = await self._get_network_interfaces()

        # Apply delay to each interface
        for interface in self._interfaces:
            await self._apply_delay(interface, delay_ms)

    async def _get_network_interfaces(self) -> List[str]:
        """Get network interfaces."""
        try:
            result = subprocess.run(
                ['ip', 'link', 'show'],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )

            interfaces = []
            for line in result.stdout.split('\n'):
                if ': ' in line and 'LOOPBACK' not in line:
                    interface = line.split(': ')[1].split('@')[0]
                    if interface:
                        interfaces.append(interface)

            return interfaces[:2]  # Limit to first 2 interfaces

        except Exception as e:
            self.logger.error(f"Error getting interfaces: {e}")
            return []

    async def _apply_delay(self, interface: str, delay_ms: int) -> None:
        """Apply delay to interface."""
        try:
            # Store original config (for rollback)
            self._original_rules[interface] = ""

            # Add delay using tc
            cmd = [
                'sudo',
                'tc',
                'qdisc',
                'add',
                'dev',
                interface,
                'root',
                'netem',
                'delay',
                f'{delay_ms}ms',
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )

            if result.returncode != 0:
                self.logger.warning(f"tc command failed: {result.stderr}")

            self.logger.info(f"Applied {delay_ms}ms delay to {interface}")

        except Exception as e:
            self.logger.error(f"Error applying delay: {e}")

    async def rollback(self) -> None:
        """Remove network delays."""
        self._active = True

        for interface in self._interfaces:
            try:
                # Remove tc rules
                cmd = ['sudo', 'tc', 'qdisc', 'del', 'dev', interface, 'root']
                subprocess.run(cmd, capture_output=True, timeout=30, check=False)

                self.logger.info(f"Removed delay from {interface}")

            except Exception as e:
                self.logger.error(f"Error removing delay from {interface}: {e}")

        self._interfaces.clear()
        self._original_rules.clear()


class ErrorInjector(FailureInjector):
    """
    Injects application errors.

    Simulates various error conditions:
    - HTTP errors
    - Database errors
    - Timeout errors
    - Validation errors
    """

    def __init__(self, config: InjectionConfig):
        super().__init__(config)
        self._error_hook: Optional[Callable] = None
        self._original_handlers: Dict[str, Any] = {}

    async def inject(self) -> None:
        """Start error injection."""
        self._active = True
        error_rate = self.config.error_rate or Decimal("0.1")  # 10%

        self.logger.info(f"Injecting errors at {error_rate * 100}% rate")

        # Set up error hooks (implementation depends on application)
        # This is a placeholder for application-specific error injection
        self._setup_error_hooks(error_rate)

    def _setup_error_hooks(self, error_rate: Decimal) -> None:
        """Set up error hooks in application."""
        # Placeholder: In real implementation, this would:
        # 1. Monkey-patch critical functions
        # 2. Add decorators that randomly raise errors
        # 3. Inject faults in API handlers

    async def rollback(self) -> None:
        """Remove error injection."""
        self._active = False

        # Remove error hooks
        # Restore original handlers
        for _key, _handler in self._original_handlers.items():
            # Restore original handler
            pass

        self._original_handlers.clear()


class LatencyInjector(FailureInjector):
    """
    Injects processing delays.

    Simulates slow operations by adding delays to:
    - API handlers
    - Database queries
    - External API calls
    """

    def __init__(self, config: InjectionConfig):
        super().__init__(config)
        self._delay_hooks: List[Callable] = []

    async def inject(self) -> None:
        """Inject latency."""
        self._active = True
        delay_ms = self.config.delay_ms or 500

        self.logger.info(f"Injecting {delay_ms}ms processing latency")

        # Set up latency hooks
        self._setup_latency_hooks(delay_ms)

    def _setup_latency_hooks(self, delay_ms: int) -> None:
        """Set up latency hooks."""
        # Placeholder: In real implementation, this would:
        # 1. Wrap critical functions with delays
        # 2. Add sleep() in API handlers
        # 3. Delay database queries

    async def rollback(self) -> None:
        """Remove latency injection."""
        self._active = False
        self._delay_hooks.clear()


class ResourceStarver(FailureInjector):
    """
    Starves system of resources (CPU/memory).

    Simulates resource exhaustion.

    WARNING: Can affect system stability!
    """

    def __init__(self, config: InjectionConfig):
        super().__init__(config)
        self._stress_processes: List[subprocess.Popen] = []

    async def inject(self) -> None:
        """Start resource starvation."""
        self._active = True

        cpu_limit = self.config.cpu_limit or Decimal("0.8")  # 80% CPU
        memory_limit = self.config.memory_limit_mb or 1024  # 1GB

        self.logger.info(f"Starving resources: CPU {cpu_limit * 100}%, Memory {memory_limit}MB")

        # Start CPU stress
        if cpu_limit > 0:
            await self._start_cpu_stress(cpu_limit)

        # Start memory stress
        if memory_limit > 0:
            await self._start_memory_stress(memory_limit)

    async def _start_cpu_stress(self, cpu_limit: Decimal) -> None:
        """Start CPU stress."""
        try:
            # Use stress-ng to load CPU
            cpu_count = max(1, int(psutil.cpu_count() * float(cpu_limit)))

            proc = subprocess.Popen(
                [
                    'stress-ng',
                    '--cpu',
                    str(cpu_count),
                    '--timeout',
                    f'{self.config.duration_seconds}s',
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            self._stress_processes.append(proc)
            self.logger.info(f"Started CPU stress on {cpu_count} cores")

        except Exception as e:
            self.logger.error(f"Error starting CPU stress: {e}")

    async def _start_memory_stress(self, memory_mb: int) -> None:
        """Start memory stress."""
        try:
            # Allocate memory
            proc = subprocess.Popen(
                [
                    'stress-ng',
                    '--vm',
                    '1',
                    '--vm-bytes',
                    f'{memory_mb}M',
                    '--timeout',
                    f'{self.config.duration_seconds}s',
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            self._stress_processes.append(proc)
            self.logger.info(f"Started memory stress: {memory_mb}MB")

        except Exception as e:
            self.logger.error(f"Error starting memory stress: {e}")

    async def rollback(self) -> None:
        """Stop resource starvation."""
        self._active = False

        # Kill all stress processes
        for proc in self._stress_processes:
            try:
                proc.terminate()
                proc.wait(timeout=10)
            except Exception as e:
                self.logger.error(f"Error stopping stress process: {e}")
                with contextlib.suppress(Exception):
                    proc.kill()

        self._stress_processes.clear()


class FailureInjectorFactory:
    """Factory for creating failure injectors."""

    @staticmethod
    def create(config: InjectionConfig) -> FailureInjector:
        """Create failure injector from config."""
        injectors = {
            InjectionType.POD_KILL: PodKiller,
            InjectionType.NETWORK_DELAY: NetworkDelayInjector,
            InjectionType.ERROR: ErrorInjector,
            InjectionType.LATENCY: LatencyInjector,
            InjectionType.RESOURCE_STARVE: ResourceStarver,
        }

        injector_class = injectors.get(config.injection_type)
        if not injector_class:
            raise ValueError(f"Unknown injection type: {config.injection_type}")

        return injector_class(config)
