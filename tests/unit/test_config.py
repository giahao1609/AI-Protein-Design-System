"""Unit tests for configuration loading and validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from protein_design.config.loader import (
    PipelineConfig,
    load_config,
    merge_configs,
    save_config,
    load_yaml,
)


class TestPipelineConfig:
    def test_default_config(self):
        config = PipelineConfig()
        assert config.generation.generator == "dummy"
        assert config.generation.num_candidates == 10
        assert config.generation.random_seed == 42
        assert config.validation.plddt.threshold is None  # Not calibrated
        assert config.validation.iptm.threshold is None  # Not calibrated

    def test_config_hash_deterministic(self):
        c1 = PipelineConfig()
        c2 = PipelineConfig()
        assert c1.config_hash == c2.config_hash

    def test_config_hash_changes(self):
        c1 = PipelineConfig()
        c2 = PipelineConfig()
        c2.generation.num_candidates = 100
        assert c1.config_hash != c2.config_hash

    def test_no_hardcoded_thresholds(self):
        """Verify that all validation thresholds default to None."""
        config = PipelineConfig()
        assert config.validation.plddt.threshold is None
        assert config.validation.ptm.threshold is None
        assert config.validation.iptm.threshold is None
        assert config.validation.pae.threshold is None
        assert config.validation.clash_score.threshold is None
        assert config.validation.interface_contacts.threshold is None
        assert config.validation.sasa.threshold is None


class TestConfigLoading:
    def test_load_yaml_file(self, tmp_path):
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(
            "generation:\n  num_candidates: 50\n  random_seed: 123\n"
        )
        data = load_yaml(yaml_file)
        assert data["generation"]["num_candidates"] == 50

    def test_load_config_from_file(self, tmp_path):
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text(
            "generation:\n  num_candidates: 25\n  generator: dummy\n"
        )
        config = load_config(base_path=yaml_file)
        assert config.generation.num_candidates == 25
        assert config.generation.generator == "dummy"

    def test_merge_configs(self):
        base = {"generation": {"num_candidates": 10, "seed": 42}}
        override = {"generation": {"num_candidates": 100}}
        merged = merge_configs(base, override)
        assert merged["generation"]["num_candidates"] == 100
        assert merged["generation"]["seed"] == 42

    def test_save_and_reload_config(self, tmp_path):
        config = PipelineConfig()
        config.generation.num_candidates = 77
        path = tmp_path / "saved.yaml"
        save_config(config, path)

        reloaded = load_config(base_path=path)
        assert reloaded.generation.num_candidates == 77
