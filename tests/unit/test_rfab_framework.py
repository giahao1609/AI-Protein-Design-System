"""Unit and mocked integration tests for RFab Framework Loader & URL resolution."""

from __future__ import annotations

import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from protein_design.generators.rfab import (
    MINIMAL_VHH_FRAMEWORK_PDB,
    FrameworkDownloadError,
    FrameworkResolutionError,
    FrameworkValidationError,
    RFabFrameworkLoader,
    RFabGenerator,
)
from protein_design.schemas import Target


def test_url_validation_valid_https(tmp_path: Path):
    loader = RFabFrameworkLoader(cache_dir=tmp_path)
    valid_url = "https://raw.githubusercontent.com/RosettaCommons/RFantibody/main/examples/frameworks/h-NbBCII10.pdb"
    assert loader.validate_url(valid_url) == valid_url


def test_url_validation_upgrades_http_to_https(tmp_path: Path):
    loader = RFabFrameworkLoader(cache_dir=tmp_path)
    http_url = "http://raw.githubusercontent.com/RosettaCommons/RFantibody/main/framework.pdb"
    upgraded = loader.validate_url(http_url)
    assert upgraded.startswith("https://")


def test_url_validation_rejects_invalid_scheme(tmp_path: Path):
    loader = RFabFrameworkLoader(cache_dir=tmp_path)
    with pytest.raises(FrameworkResolutionError, match="Invalid URL scheme"):
        loader.validate_url("ftp://example.com/framework.pdb")


def test_url_validation_rejects_missing_host(tmp_path: Path):
    loader = RFabFrameworkLoader(cache_dir=tmp_path)
    with pytest.raises(FrameworkResolutionError, match="missing network location"):
        loader.validate_url("https:///framework.pdb")


def test_validate_pdb_content_accepts_valid_pdb(tmp_path: Path):
    loader = RFabFrameworkLoader(cache_dir=tmp_path)
    loader.validate_pdb_content(MINIMAL_VHH_FRAMEWORK_PDB, "test_source")


def test_validate_pdb_content_rejects_html_error(tmp_path: Path):
    loader = RFabFrameworkLoader(cache_dir=tmp_path)
    html_error = "<!DOCTYPE html><html><head><title>404 Not Found</title></head><body>404 Not Found</body></html>"
    with pytest.raises(FrameworkValidationError, match="HTML/JSON error payload"):
        loader.validate_pdb_content(html_error, "mock_url")


def test_validate_pdb_content_rejects_short_content(tmp_path: Path):
    loader = RFabFrameworkLoader(cache_dir=tmp_path)
    with pytest.raises(FrameworkValidationError, match="suspiciously short"):
        loader.validate_pdb_content("ATOM 1\n", "mock_url")


def test_validate_pdb_content_rejects_non_pdb_text(tmp_path: Path):
    loader = RFabFrameworkLoader(cache_dir=tmp_path)
    junk = "This is a random text file that does not contain any protein structure records at all." * 2
    with pytest.raises(FrameworkValidationError, match="does not contain valid PDB records"):
        loader.validate_pdb_content(junk, "mock_url")


def test_resolve_framework_from_cache(tmp_path: Path):
    loader = RFabFrameworkLoader(cache_dir=tmp_path)
    cached_file = tmp_path / "h-NbBCII10.pdb"
    cached_file.write_text(MINIMAL_VHH_FRAMEWORK_PDB, encoding="utf-8")

    # Should hit cache without making network requests
    with patch("urllib.request.urlopen") as mock_url:
        resolved = loader.resolve_framework("h-NbBCII10")
        assert resolved.path == cached_file
        assert resolved.status.value == "CACHED"
        assert resolved.is_production_ready is True
        assert mock_url.call_count == 0


def test_resolve_framework_download_success(tmp_path: Path):
    loader = RFabFrameworkLoader(cache_dir=tmp_path)

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = MINIMAL_VHH_FRAMEWORK_PDB.encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        resolved = loader.resolve_framework("h-NbBCII10")
        assert resolved.path.exists()
        assert resolved.status.value == "VALID_DOWNLOADED"
        assert resolved.is_production_ready is True
        assert "ATOM" in resolved.path.read_text(encoding="utf-8")


def test_resolve_framework_retry_and_mirror_fallback(tmp_path: Path):
    loader = RFabFrameworkLoader(cache_dir=tmp_path, max_retries=2, backoff_factor=0.01)

    fail_resp = urllib.error.URLError("Connection refused")

    success_resp = MagicMock()
    success_resp.status = 200
    success_resp.read.return_value = MINIMAL_VHH_FRAMEWORK_PDB.encode("utf-8")
    success_resp.__enter__.return_value = success_resp

    # Primary fails twice, mirror succeeds
    with patch("urllib.request.urlopen", side_effect=[fail_resp, fail_resp, success_resp]):
        resolved = loader.resolve_framework("h-NbBCII10")
        assert resolved.path.exists()
        assert resolved.status.value == "VALID_DOWNLOADED"


def test_resolve_framework_offline_fallback(tmp_path: Path):
    loader = RFabFrameworkLoader(
        cache_dir=tmp_path,
        max_retries=1,
        backoff_factor=0.01,
        allow_offline_fallback=True,
    )

    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Network down")):
        resolved = loader.resolve_framework("h-NbBCII10")
        assert resolved.path.exists()
        assert resolved.status.value == "TEST_FIXTURE_FALLBACK"
        assert resolved.is_production_ready is False
        assert "VHH FRAMEWORK" in resolved.path.read_text(encoding="utf-8")


def test_resolve_framework_offline_fallback_disabled_raises(tmp_path: Path):
    loader = RFabFrameworkLoader(
        cache_dir=tmp_path,
        max_retries=1,
        backoff_factor=0.01,
        allow_offline_fallback=False,
    )

    with (
        patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Network down")),
        pytest.raises(FrameworkDownloadError, match="Could not resolve framework"),
    ):
        loader.resolve_framework("h-NbBCII10")


def test_rfab_generator_generates_candidates(tmp_path: Path):
    loader = RFabFrameworkLoader(cache_dir=tmp_path, allow_offline_fallback=True)
    generator = RFabGenerator(framework_loader=loader)

    target = Target(target_id="EGFR", name="EGFR", source="test", sequence="MKTVRQERLK")
    candidates = generator.generate(
        target=target,
        config={"framework_id": "h-NbBCII10"},
        num_candidates=3,
    )

    assert len(candidates) == 3
    assert candidates[0].generator == "rfab"
    assert "framework_path" in candidates[0].metadata
    assert candidates[0].metadata["framework_status"] == "TEST_FIXTURE_FALLBACK"
    assert candidates[0].metadata["framework_production_ready"] is False
    assert candidates[0].scientific_status.value == "GENERATED"


def test_rfab_generator_enforce_production_rejects_mock_fallback(tmp_path: Path):
    loader = RFabFrameworkLoader(cache_dir=tmp_path, allow_offline_fallback=True)
    generator = RFabGenerator(framework_loader=loader)

    target = Target(target_id="EGFR", name="EGFR", source="test", sequence="MKTVRQERLK")
    with (
        patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Network down")),
        pytest.raises(FrameworkDownloadError, match="Production enforcement rejected framework"),
    ):
        generator.generate(
            target=target,
            config={"framework_id": "h-NbBCII10", "enforce_production": True},
            num_candidates=1,
        )
