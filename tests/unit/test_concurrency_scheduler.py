"""Unit tests for ConcurrencySafeScheduler, backpressure, and resume idempotency."""

from __future__ import annotations

from protein_design.core.concurrency import ConcurrencySafeScheduler, TaskStatus


def test_scheduler_linear_pipeline_execution():
    scheduler = ConcurrencySafeScheduler(max_concurrency=1)
    call_order: list[str] = []

    scheduler.add_node("step1", lambda: call_order.append("step1") or "out1")
    scheduler.add_node(
        "step2",
        lambda: call_order.append("step2") or "out2",
        dependencies=["step1"],
    )
    scheduler.add_node(
        "step3",
        lambda: call_order.append("step3") or "out3",
        dependencies=["step2"],
    )

    results = scheduler.run_all()
    assert results["step1"] == TaskStatus.SUCCESS
    assert results["step2"] == TaskStatus.SUCCESS
    assert results["step3"] == TaskStatus.SUCCESS
    assert call_order == ["step1", "step2", "step3"]


def test_scheduler_max_concurrency_throttling():
    scheduler = ConcurrencySafeScheduler(max_concurrency=1)
    active_concurrent = 0
    max_observed = 0

    def mock_task():
        nonlocal active_concurrent, max_observed
        active_concurrent += 1
        max_observed = max(max_observed, active_concurrent)
        active_concurrent -= 1
        return "done"

    for i in range(5):
        scheduler.add_node(f"task_{i}", mock_task)

    results = scheduler.run_all()
    assert len(results) == 5
    assert all(st == TaskStatus.SUCCESS for st in results.values())
    assert max_observed <= 1


def test_scheduler_exponential_backoff_retry():
    scheduler = ConcurrencySafeScheduler(max_concurrency=1)
    attempts = 0

    def flaky_task():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise RuntimeError("Transient cluster error")
        return "success"

    scheduler.add_node("flaky", flaky_task, max_retries=3, base_backoff_seconds=0.01)
    results = scheduler.run_all()

    assert results["flaky"] == TaskStatus.SUCCESS
    assert attempts == 3


def test_scheduler_failed_node_stops_downstream():
    scheduler = ConcurrencySafeScheduler(max_concurrency=1)

    def failing_task():
        raise RuntimeError("Permanent failure")

    scheduler.add_node("upstream", failing_task, max_retries=1, base_backoff_seconds=0.01)
    scheduler.add_node("downstream", lambda: "never_run", dependencies=["upstream"])

    results = scheduler.run_all()
    assert results["upstream"] == TaskStatus.FAILED
    assert results["downstream"] == TaskStatus.FAILED


def test_scheduler_resume_idempotency_skips_cached_artifacts():
    completed_cache = {"step1": "cached_output_1"}
    scheduler = ConcurrencySafeScheduler(max_concurrency=1, completed_artifacts=completed_cache)

    step1_ran = False
    step2_ran = False

    def task1():
        nonlocal step1_ran
        step1_ran = True
        return "new_output"

    def task2():
        nonlocal step2_ran
        step2_ran = True
        return "output_2"

    scheduler.add_node("step1", task1)
    scheduler.add_node("step2", task2, dependencies=["step1"])

    results = scheduler.run_all()
    assert results["step1"] == TaskStatus.SKIPPED_CACHED
    assert results["step2"] == TaskStatus.SUCCESS
    assert not step1_ran  # Did not duplicate work
    assert step2_ran
