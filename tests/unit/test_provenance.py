"""Unit tests for provenance tracking and hashing."""

from __future__ import annotations

import pytest

from protein_design.schemas.common import hash_string, hash_dict, hash_file
from protein_design.provenance.tracker import create_provenance, get_hardware_info


class TestHashing:
    def test_hash_string_consistent(self):
        assert hash_string("test") == hash_string("test")
        assert hash_string("a") != hash_string("b")

    def test_hash_dict_order_independent(self):
        d1 = {"a": 1, "b": 2, "c": 3}
        d2 = {"c": 3, "a": 1, "b": 2}
        assert hash_dict(d1) == hash_dict(d2)

    def test_hash_file(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello world")
        h1 = hash_file(f)
        h2 = hash_file(f)
        assert h1 == h2
        assert len(h1) == 64

    def test_hash_file_changes_with_content(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("content1")
        h1 = hash_file(f)
        f.write_text("content2")
        h2 = hash_file(f)
        assert h1 != h2


class TestProvenance:
    def test_create_provenance(self):
        prov = create_provenance(
            run_id="run_001",
            target_id="tgt_001",
            generator="dummy",
            generator_version="1.0.0",
            config={"num_candidates": 10},
            random_seed=42,
        )
        assert prov.run_id == "run_001"
        assert prov.generator == "dummy"
        assert prov.config_hash != ""
        assert prov.random_seed == 42
        assert prov.timestamp is not None

    def test_provenance_config_hash_deterministic(self):
        config = {"num_candidates": 10, "seed": 42}
        p1 = create_provenance("r1", "t1", "g", "1.0", config)
        p2 = create_provenance("r2", "t2", "g", "1.0", config)
        assert p1.config_hash == p2.config_hash

    def test_hardware_info(self):
        hw = get_hardware_info()
        assert hw.python_version is not None
        assert hw.hostname is not None
