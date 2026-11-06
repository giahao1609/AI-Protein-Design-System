"""Unit tests for ConcurrencySafeScheduler, backpressure, and resume idempotency."""

from __future__ import annotations

from protein_design.core.concurrency import (
    ConcurrencySafeScheduler,
    TaskStatus,
    calculate_task_fingerprint,
)


def test_scheduler_linear_pipeline_execution() -> None:
    scheduler = ConcurrencySafeScheduler(max_concurrency=1)
    call_order: list[str] = []

    def step1_func() -> str:
        call_order.append("step1")
        return "out1"

    def step2_func() -> str:
        call_order.append("step2")
        return "out2"

    def step3_func() -> str:
        call_order.append("step3")
        return "out3"

    scheduler.add_node("step1", step1_func)
    scheduler.add_node("step2", step2_func, dependencies=["step1"])
    scheduler.add_node("step3", step3_func, dependencies=["step2"])

    results = scheduler.run_all()
    assert results["step1"] == TaskStatus.SUCCESS
    assert results["step2"] == TaskStatus.SUCCESS
    assert results["step3"] == TaskStatus.SUCCESS
    assert call_order == ["step1", "step2", "step3"]


def test_scheduler_max_concurrency_throttling() -> None:
    scheduler = ConcurrencySafeScheduler(max_concurrency=1)
    active_concurrent = 0
    max_observed = 0

    def mock_task() -> str:
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


def test_scheduler_exponential_backoff_retry() -> None:
    scheduler = ConcurrencySafeScheduler(max_concurrency=1)
    attempts = 0

    def flaky_task() -> str:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise RuntimeError("Transient cluster error")
        return "success"

    scheduler.add_node("flaky", flaky_task, max_retries=3, base_backoff_seconds=0.01)
    results = scheduler.run_all()

    assert results["flaky"] == TaskStatus.SUCCESS
    assert attempts == 3


def test_scheduler_failed_node_stops_downstream() -> None:
    scheduler = ConcurrencySafeScheduler(max_concurrency=1)

    def failing_task() -> None:
        raise RuntimeError("Permanent failure")

    scheduler.add_node("upstream", failing_task, max_retries=1, base_backoff_seconds=0.01)
    scheduler.add_node("downstream", lambda: "never_run", dependencies=["upstream"])

    results = scheduler.run_all()
    assert results["upstream"] == TaskStatus.FAILED
    assert results["downstream"] == TaskStatus.FAILED


def test_scheduler_resume_idempotency_skips_cached_artifacts() -> None:
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


def test_scheduler_cache_fingerprint_matching_skips() -> None:
    fp = calculate_task_fingerprint("input_seq", {"mode": "fast"}, "esmfold-v2")
    completed_cache = {"step1": {"result": "cached_pdb", "fingerprint": fp}}
    scheduler = ConcurrencySafeScheduler(max_concurrency=1, completed_artifacts=completed_cache)

    ran = False

    def task_step():
        nonlocal ran
        ran = True
        return {"result": "new_pdb"}

    scheduler.add_node("step1", task_step, expected_fingerprint=fp)
    results = scheduler.run_all()

    assert results["step1"] == TaskStatus.SKIPPED_CACHED
    assert not ran


def test_scheduler_cache_fingerprint_mismatch_invalidates() -> None:
    old_fp = calculate_task_fingerprint("input_seq", {"mode": "fast"}, "esmfold-v1")
    new_fp = calculate_task_fingerprint("input_seq", {"mode": "fast"}, "esmfold-v2")
    completed_cache = {"step1": {"result": "stale_pdb", "fingerprint": old_fp}}
    scheduler = ConcurrencySafeScheduler(max_concurrency=1, completed_artifacts=completed_cache)

    ran = False

    def task_step():
        nonlocal ran
        ran = True
        return {"result": "new_pdb"}

    # Register node expecting new_fp; old cached output should be rejected
    scheduler.add_node("step1", task_step, expected_fingerprint=new_fp)
    results = scheduler.run_all()

    assert results["step1"] == TaskStatus.SUCCESS
    assert ran
    assert scheduler.completed_artifacts["step1"]["fingerprint"] == new_fp
