from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from hashlib import sha256
from uuid import uuid4


class TaskStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    VERIFYING = "verifying"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass
class AuditEvent:
    event: str
    detail: str


@dataclass
class Task:
    id: str
    intent: str
    status: TaskStatus = TaskStatus.QUEUED
    artifact: str | None = None
    audit: list[AuditEvent] = field(default_factory=list)


class ControlPlane:
    """Deterministic reference implementation of the task lifecycle."""

    def __init__(self) -> None:
        self.tasks: dict[str, Task] = {}

    def create_task(self, intent: str) -> Task:
        if not intent.strip():
            raise ValueError("intent must not be empty")
        task = Task(id=str(uuid4()), intent=intent)
        task.audit.append(AuditEvent("task.created", intent))
        self.tasks[task.id] = task
        return task

    def run(self, task_id: str) -> Task:
        task = self.tasks[task_id]
        if task.status is not TaskStatus.QUEUED:
            raise ValueError(f"task {task_id} is not queued")
        task.status = TaskStatus.RUNNING
        task.audit.append(AuditEvent("run.started", "local-worker"))
        task.artifact = f"result.md\n\nIntent: {task.intent}\nStatus: completed by local worker.\n"
        task.status = TaskStatus.VERIFYING
        task.audit.append(AuditEvent("artifact.created", self.artifact_digest(task)))
        if self.verify(task):
            task.status = TaskStatus.SUCCEEDED
            task.audit.append(AuditEvent("verification.passed", "artifact is present and traceable"))
        else:
            task.status = TaskStatus.FAILED
            task.audit.append(AuditEvent("verification.failed", "artifact missing"))
        return task

    @staticmethod
    def verify(task: Task) -> bool:
        return bool(task.artifact and task.intent in task.artifact)

    @staticmethod
    def artifact_digest(task: Task) -> str:
        return sha256((task.artifact or "").encode()).hexdigest()
