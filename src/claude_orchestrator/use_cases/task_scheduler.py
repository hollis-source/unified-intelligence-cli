"""TaskScheduler - Automatic task scheduling.

Schedules generated tasks based on priority and resource availability.
Respects rate limits and resource quotas.

Clean Architecture: Use Case layer
SOLID: SRP - Single responsibility for task scheduling
"""
from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

from src.claude_orchestrator.entities.generated_task import GeneratedTask

logger = logging.getLogger(__name__)


@dataclass
class ScheduleSlot:
    """A scheduled time slot for task execution."""
    task: GeneratedTask
    scheduled_time: datetime
    estimated_end_time: datetime
    priority: str
    resource_allocation: Dict[str, Any]


class TaskScheduler:
    """
    Schedules tasks based on priority and resource availability.
    
    Features:
    - Priority-based scheduling
    - Resource quota enforcement
    - Rate limiting
    - Time-based scheduling
    
    Usage:
        scheduler = TaskScheduler(max_concurrent=5, max_tasks_per_hour=20)
        schedule = scheduler.schedule_tasks(tasks)
    """
    
    def __init__(
        self,
        max_concurrent: int = 5,
        max_tasks_per_hour: int = 20,
        max_tasks_per_day: int = 100,
        cpu_quota: float = 10.0,  # CPU cores
        memory_quota: float = 32.0,  # GB
    ):
        """
        Initialize task scheduler.
        
        Args:
            max_concurrent: Maximum concurrent tasks
            max_tasks_per_hour: Maximum tasks per hour
            max_tasks_per_day: Maximum tasks per day
            cpu_quota: Total CPU quota
            memory_quota: Total memory quota (GB)
        """
        self.max_concurrent = max_concurrent
        self.max_tasks_per_hour = max_tasks_per_hour
        self.max_tasks_per_day = max_tasks_per_day
        self.cpu_quota = cpu_quota
        self.memory_quota = memory_quota
        
        self.scheduled_slots: List[ScheduleSlot] = []
    
    def schedule_tasks(
        self,
        tasks: List[GeneratedTask],
        start_time: Optional[datetime] = None,
    ) -> List[ScheduleSlot]:
        """
        Schedule tasks for execution.
        
        Args:
            tasks: List of GeneratedTask objects (should be prioritized)
            start_time: Start time for scheduling (default: now)
            
        Returns:
            List of ScheduleSlot objects
        """
        if start_time is None:
            start_time = datetime.now()
        
        schedule: List[ScheduleSlot] = []
        current_time = start_time
        
        # Track resource usage
        hourly_counts: Dict[int, int] = {}  # hour -> count
        daily_count = 0
        
        for task in tasks:
            # Check daily limit
            if daily_count >= self.max_tasks_per_day:
                logger.warning(f"Daily task limit reached ({self.max_tasks_per_day}), skipping remaining tasks")
                break
            
            # Find next available slot
            slot_time = self._find_next_slot(
                current_time,
                task,
                schedule,
                hourly_counts,
            )
            
            if slot_time is None:
                logger.warning(f"Could not schedule task {task.id} (resource constraints)")
                continue
            
            # Create schedule slot
            estimated_end = slot_time + timedelta(minutes=task.estimated_minutes)
            
            slot = ScheduleSlot(
                task=task,
                scheduled_time=slot_time,
                estimated_end_time=estimated_end,
                priority=task.priority,
                resource_allocation=self._allocate_resources(task),
            )
            
            schedule.append(slot)
            
            # Update counters
            hour_key = slot_time.hour
            hourly_counts[hour_key] = hourly_counts.get(hour_key, 0) + 1
            daily_count += 1
            
            # Advance current time
            current_time = estimated_end
        
        self.scheduled_slots = schedule
        
        logger.info(f"Scheduled {len(schedule)}/{len(tasks)} tasks")
        
        return schedule
    
    def _find_next_slot(
        self,
        current_time: datetime,
        task: GeneratedTask,
        schedule: List[ScheduleSlot],
        hourly_counts: Dict[int, int],
    ) -> Optional[datetime]:
        """Find next available time slot for task."""
        candidate_time = current_time
        max_attempts = 24  # Try up to 24 hours ahead
        
        for _ in range(max_attempts):
            # Check hourly rate limit
            hour_key = candidate_time.hour
            if hourly_counts.get(hour_key, 0) >= self.max_tasks_per_hour:
                # Move to next hour
                candidate_time = candidate_time.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
                continue
            
            # Check concurrent limit
            concurrent = self._count_concurrent(candidate_time, schedule)
            if concurrent >= self.max_concurrent:
                # Move forward by 10 minutes
                candidate_time += timedelta(minutes=10)
                continue
            
            # Check resource availability
            if not self._check_resources(candidate_time, task, schedule):
                candidate_time += timedelta(minutes=10)
                continue
            
            # Found a slot
            return candidate_time
        
        # Could not find slot
        return None
    
    def _count_concurrent(
        self,
        time: datetime,
        schedule: List[ScheduleSlot],
    ) -> int:
        """Count concurrent tasks at given time."""
        count = 0
        for slot in schedule:
            if slot.scheduled_time <= time < slot.estimated_end_time:
                count += 1
        return count
    
    def _check_resources(
        self,
        time: datetime,
        task: GeneratedTask,
        schedule: List[ScheduleSlot],
    ) -> bool:
        """Check if resources are available for task at given time."""
        # Calculate resource usage at this time
        cpu_used = 0.0
        memory_used = 0.0
        
        for slot in schedule:
            if slot.scheduled_time <= time < slot.estimated_end_time:
                cpu_used += slot.resource_allocation.get("cpu", 1.0)
                memory_used += slot.resource_allocation.get("memory", 2.0)
        
        # Estimate task resource needs
        task_cpu = self._estimate_cpu(task)
        task_memory = self._estimate_memory(task)
        
        # Check if within quota
        if cpu_used + task_cpu > self.cpu_quota:
            return False
        
        if memory_used + task_memory > self.memory_quota:
            return False
        
        return True
    
    def _allocate_resources(self, task: GeneratedTask) -> Dict[str, Any]:
        """Allocate resources for task."""
        return {
            "cpu": self._estimate_cpu(task),
            "memory": self._estimate_memory(task),
        }
    
    def _estimate_cpu(self, task: GeneratedTask) -> float:
        """Estimate CPU cores needed for task."""
        # Heuristic based on complexity
        complexity_map = {
            "low": 0.5,
            "medium": 1.0,
            "high": 2.0,
        }
        return complexity_map.get(task.complexity, 1.0)
    
    def _estimate_memory(self, task: GeneratedTask) -> float:
        """Estimate memory (GB) needed for task."""
        # Heuristic based on complexity
        complexity_map = {
            "low": 1.0,
            "medium": 2.0,
            "high": 4.0,
        }
        return complexity_map.get(task.complexity, 2.0)
    
    def get_schedule_summary(self) -> Dict[str, Any]:
        """Get summary of current schedule."""
        if not self.scheduled_slots:
            return {
                "total_tasks": 0,
                "total_duration_minutes": 0,
                "start_time": None,
                "end_time": None,
            }
        
        total_duration = sum(s.task.estimated_minutes for s in self.scheduled_slots)
        
        return {
            "total_tasks": len(self.scheduled_slots),
            "total_duration_minutes": total_duration,
            "start_time": self.scheduled_slots[0].scheduled_time.isoformat(),
            "end_time": self.scheduled_slots[-1].estimated_end_time.isoformat(),
            "priority_breakdown": self._get_priority_breakdown(),
        }
    
    def _get_priority_breakdown(self) -> Dict[str, int]:
        """Get breakdown of tasks by priority."""
        breakdown: Dict[str, int] = {}
        for slot in self.scheduled_slots:
            priority = str(slot.priority)
            breakdown[priority] = breakdown.get(priority, 0) + 1
        return breakdown

