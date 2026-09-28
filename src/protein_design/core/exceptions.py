"""Domain-specific exceptions for the protein design system."""

from __future__ import annotations


class ProteinDesignError(Exception):
    """Base exception for all protein design errors."""
    pass


class ConfigError(ProteinDesignError):
    """Error in configuration loading or validation."""
    pass


class SchemaValidationError(ProteinDesignError):
    """Error in data schema validation."""
    pass


class StorageError(ProteinDesignError):
    """Error in storage operations."""
    pass


class GenerationError(ProteinDesignError):
    """Error during candidate generation."""

    def __init__(self, message: str, candidate_id: str | None = None):
        super().__init__(message)
        self.candidate_id = candidate_id


class PredictionError(ProteinDesignError):
    """Error during structure prediction."""

    def __init__(self, message: str, candidate_id: str | None = None):
        super().__init__(message)
        self.candidate_id = candidate_id


class ValidationError(ProteinDesignError):
    """Error during candidate validation."""

    def __init__(self, message: str, candidate_id: str | None = None):
        super().__init__(message)
        self.candidate_id = candidate_id


class PipelineError(ProteinDesignError):
    """Error in pipeline orchestration."""
    pass


class CandidateLifecycleError(ProteinDesignError):
    """Invalid candidate status transition."""

    def __init__(self, candidate_id: str, from_status: str, to_status: str):
        super().__init__(
            f"Invalid transition for {candidate_id}: {from_status} → {to_status}"
        )
        self.candidate_id = candidate_id
        self.from_status = from_status
        self.to_status = to_status
