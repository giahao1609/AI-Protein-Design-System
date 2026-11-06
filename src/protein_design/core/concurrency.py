"""Concurrency-Safe Scheduler and Fallback Orchestrator.

Provides serialized DAG job submission (max_concurrency=1), dependency-based scheduling,
queue backpressure, exponential backoff retries, and resume idempotency without duplicating
completed work on compute clusters.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog

log = structlog.get_logger(__name__)


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PAUSED_INFRA = "PAUSED_INFRA"
    SKIPPED_CACHED = "SKIPPED_CACHED"


@dataclass
class TaskNode:
    """Node in a workflow execution graph with dependency tracking."""

    node_id: str
    task_func: Callable[[], Any]
    dependencies: list[str] = field(default_factory=list)
    max_retries: int = 3
    base_backoff_seconds: float = 0.1
    status: TaskStatus = TaskStatus.PENDING
    retry_count: int = 0
    result: Any = None
    error: str | None = None
    output_artifact_id: str | None = None


class ConcurrencySafeScheduler:
    """Orchestrates workflow execution with strict concurrency throttling and backpressure."""

    def __init__(
        self,
        max_concurrency: int = 1,
        completed_artifacts: dict[str, Any] | None = None,
    ):
        self.max_concurrency = max(1, max_concurrency)
        self.completed_artifacts = completed_artifacts or {}
        self.nodes: dict[str, TaskNode] = {}
        self.execution_log: list[dict[str, Any]] = []

    def add_node(
        self,
        node_id: str,
        task_func: Callable[[], Any],
        dependencies: list[str] | None = None,
        max_retries: int = 3,
        base_backoff_seconds: float = 0.05,
        output_artifact_id: str | None = None,
    ) -> None:
        """Register a node in the workflow graph."""
        if node_id in self.nodes:
            raise ValueError(f"Node '{node_id}' already registered in scheduler")
        self.nodes[node_id] = TaskNode(
            node_id=node_id,
            task_func=task_func,
            dependencies=dependencies or [],
            max_retries=max_retries,
            base_backoff_seconds=base_backoff_seconds,
            output_artifact_id=output_artifact_id,
        )

    def is_node_cached(self, node: TaskNode) -> bool:
        """Check if node output already exists in completed artifacts to guarantee idempotency."""
        art_id = node.output_artifact_id or node.node_id
        return art_id in self.completed_artifacts

    def get_ready_nodes(self) -> list[TaskNode]:
        """Return nodes whose dependencies are all SUCCESS or SKIPPED_CACHED."""
        ready: list[TaskNode] = []
        for node in self.nodes.values():
            if node.status != TaskStatus.PENDING:
                continue

            # Verify all upstream dependencies satisfied
            deps_met = True
            for dep_id in node.dependencies:
                dep_node = self.nodes.get(dep_id)
                if not dep_node or dep_node.status not in (
                    TaskStatus.SUCCESS,
                    TaskStatus.SKIPPED_CACHED,
                ):
                    deps_met = False
                    break

            if deps_met:
                ready.append(node)
        return ready

    def run_all(self) -> dict[str, TaskStatus]:
        """Execute all nodes in dependency order adhering strictly to max_concurrency."""
        log.info(
            "scheduler_started",
            total_nodes=len(self.nodes),
            max_concurrency=self.max_concurrency,
        )

        while True:
            # 1. Check for completed / cached nodes first
            for node in self.nodes.values():
                if node.status == TaskStatus.PENDING and self.is_node_cached(node):
                    node.status = TaskStatus.SKIPPED_CACHED
                    node.result = self.completed_artifacts[node.output_artifact_id or node.node_id]
                    self.execution_log.append(
                        {"node_id": node.node_id, "status": TaskStatus.SKIPPED_CACHED}
                    )
                    log.info("node_resumed_from_cache", node_id=node.node_id)

            # 2. Find eligible nodes
            ready_nodes = self.get_ready_nodes()
            if not ready_nodes:
                # Check if any tasks failed or if all done
                all_done = all(
                    n.status in (TaskStatus.SUCCESS, TaskStatus.SKIPPED_CACHED, TaskStatus.FAILED)
                    for n in self.nodes.values()
                )
                if all_done:
                    break
                # Blocked state: remaining pending nodes have unfulfilled or failed dependencies
                for node in self.nodes.values():
                    if node.status == TaskStatus.PENDING:
                        node.status = TaskStatus.FAILED
                        node.error = "Dependency resolution deadlocked or upstream failure"
                break

            # 3. Dispatch batch constrained by max_concurrency (Serialized submission if concurrency=1)
            batch = ready_nodes[: self.max_concurrency]
            for node in batch:
                self._execute_single_node(node)

        results = {nid: n.status for nid, n in self.nodes.items()}
        log.info("scheduler_finished", summary=results)
        return results

    def _execute_single_node(self, node: TaskNode) -> None:
        """Execute a single task node with exponential backoff retries on failure."""
        node.status = TaskStatus.RUNNING

        while node.retry_count <= node.max_retries:
            try:
                log.info("task_execution_attempt", node_id=node.node_id, attempt=node.retry_count + 1)
                result = node.task_func()
                node.result = result
                node.status = TaskStatus.SUCCESS
                art_id = node.output_artifact_id or node.node_id
                self.completed_artifacts[art_id] = result
                self.execution_log.append({"node_id": node.node_id, "status": TaskStatus.SUCCESS})
                return
            except Exception as exc:
                node.retry_count += 1
                node.error = str(exc)
                log.warning(
                    "task_failed_attempt",
                    node_id=node.node_id,
                    attempt=node.retry_count,
                    error=str(exc),
                )
                if node.retry_count <= node.max_retries:
                    # Exponential backoff
                    delay = node.base_backoff_seconds * (2 ** (node.retry_count - 1))
                    time.sleep(delay)
                else:
                    node.status = TaskStatus.FAILED
                    self.execution_log.append(
                        {"node_id": node.node_id, "status": TaskStatus.FAILED, "error": str(exc)}
                    )
