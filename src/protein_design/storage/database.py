"""SQLite metadata store for candidates, targets, experiments, evidence, and decisions.

Design rationale:
- SQLite scales to 100k+ candidates without external database infrastructure
- JSON columns store flexible nested data (metrics, provenance)
- All queries go through this module — no raw SQL elsewhere
- Candidates are NEVER deleted, even when failed/rejected
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Optional

from protein_design.schemas import (
    Candidate,
    DecisionRecord,
    EvidenceRecord,
    ExperimentRun,
    Target,
)
from protein_design.logging import get_logger

log = get_logger(module="storage.database")


class MetadataStore:
    """SQLite-backed metadata store.

    Handles serialization/deserialization of Pydantic models to/from SQLite.
    Uses JSON columns for flexible nested data.
    """

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    def initialize(self) -> None:
        """Create all tables if they don't exist."""
        self.conn.executescript(_SCHEMA_SQL)
        log.info("database_initialized", db_path=str(self.db_path))

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    # -------------------------------------------------------------------
    # Targets
    # -------------------------------------------------------------------

    def save_target(self, target: Target) -> None:
        """Insert or update a target."""
        data = target.model_dump_json()
        self.conn.execute(
            """INSERT INTO targets (target_id, name, sequence, target_hash, data)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(target_id) DO UPDATE SET
                   name=excluded.name,
                   sequence=excluded.sequence,
                   target_hash=excluded.target_hash,
                   data=excluded.data""",
            (target.target_id, target.name, target.sequence, target.target_hash, data),
        )
        self.conn.commit()
        log.info("target_saved", target_id=target.target_id, name=target.name)

    def get_target(self, target_id: str) -> Optional[Target]:
        """Retrieve a target by ID."""
        row = self.conn.execute(
            "SELECT data FROM targets WHERE target_id = ?", (target_id,)
        ).fetchone()
        if row is None:
            return None
        return Target.model_validate_json(row["data"])

    def list_targets(self) -> list[Target]:
        """List all targets."""
        rows = self.conn.execute("SELECT data FROM targets ORDER BY rowid").fetchall()
        return [Target.model_validate_json(row["data"]) for row in rows]

    # -------------------------------------------------------------------
    # Candidates
    # -------------------------------------------------------------------

    def save_candidate(self, candidate: Candidate) -> None:
        """Insert or update a candidate. Candidates are NEVER deleted."""
        data = candidate.model_dump_json()
        self.conn.execute(
            """INSERT INTO candidates
               (candidate_id, target_id, sequence, sequence_hash, status, scientific_status, generator, data)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(candidate_id) DO UPDATE SET
                   status=excluded.status,
                   scientific_status=excluded.scientific_status,
                   data=excluded.data""",
            (
                candidate.candidate_id,
                candidate.target_id,
                candidate.sequence,
                candidate.sequence_hash,
                candidate.status.value,
                candidate.scientific_status.value,
                candidate.generator,
                data,
            ),
        )
        self.conn.commit()

    def get_candidate(self, candidate_id: str) -> Optional[Candidate]:
        """Retrieve a candidate by ID."""
        row = self.conn.execute(
            "SELECT data FROM candidates WHERE candidate_id = ?", (candidate_id,)
        ).fetchone()
        if row is None:
            return None
        return Candidate.model_validate_json(row["data"])

    def list_candidates(
        self,
        target_id: Optional[str] = None,
        status: Optional[str] = None,
        generator: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Candidate]:
        """List candidates with optional filters."""
        query = "SELECT data FROM candidates WHERE 1=1"
        params: list = []

        if target_id:
            query += " AND target_id = ?"
            params.append(target_id)
        if status:
            query += " AND status = ?"
            params.append(status)
        if generator:
            query += " AND generator = ?"
            params.append(generator)

        query += " ORDER BY rowid LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = self.conn.execute(query, params).fetchall()
        return [Candidate.model_validate_json(row["data"]) for row in rows]

    def count_candidates(
        self,
        target_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> int:
        """Count candidates with optional filters."""
        query = "SELECT COUNT(*) as cnt FROM candidates WHERE 1=1"
        params: list = []

        if target_id:
            query += " AND target_id = ?"
            params.append(target_id)
        if status:
            query += " AND status = ?"
            params.append(status)

        row = self.conn.execute(query, params).fetchone()
        return row["cnt"] if row else 0

    def candidate_exists_by_hash(self, sequence_hash: str) -> bool:
        """Check if a candidate with the same sequence hash already exists."""
        row = self.conn.execute(
            "SELECT 1 FROM candidates WHERE sequence_hash = ? LIMIT 1",
            (sequence_hash,),
        ).fetchone()
        return row is not None

    # -------------------------------------------------------------------
    # Experiment Runs
    # -------------------------------------------------------------------

    def save_run(self, run: ExperimentRun) -> None:
        """Insert or update an experiment run."""
        data = run.model_dump_json()
        self.conn.execute(
            """INSERT INTO experiment_runs (run_id, target_id, status, data)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(run_id) DO UPDATE SET
                   status=excluded.status,
                   data=excluded.data""",
            (run.run_id, run.target_id, run.status.value, data),
        )
        self.conn.commit()

    def get_run(self, run_id: str) -> Optional[ExperimentRun]:
        """Retrieve a run by ID."""
        row = self.conn.execute(
            "SELECT data FROM experiment_runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        if row is None:
            return None
        return ExperimentRun.model_validate_json(row["data"])

    def list_runs(
        self,
        target_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> list[ExperimentRun]:
        """List experiment runs."""
        query = "SELECT data FROM experiment_runs WHERE 1=1"
        params: list = []

        if target_id:
            query += " AND target_id = ?"
            params.append(target_id)
        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY rowid"
        rows = self.conn.execute(query, params).fetchall()
        return [ExperimentRun.model_validate_json(row["data"]) for row in rows]

    # -------------------------------------------------------------------
    # Evidence Records
    # -------------------------------------------------------------------

    def save_evidence(self, evidence: EvidenceRecord) -> None:
        """Insert or update an evidence record."""
        data = evidence.model_dump_json()
        self.conn.execute(
            """INSERT INTO evidence_records (evidence_id, claim, evidence_level, data)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(evidence_id) DO UPDATE SET
                   data=excluded.data""",
            (evidence.evidence_id, evidence.claim, evidence.evidence_level.value, data),
        )
        self.conn.commit()

    def get_evidence(self, evidence_id: str) -> Optional[EvidenceRecord]:
        """Retrieve an evidence record by ID."""
        row = self.conn.execute(
            "SELECT data FROM evidence_records WHERE evidence_id = ?", (evidence_id,)
        ).fetchone()
        if row is None:
            return None
        return EvidenceRecord.model_validate_json(row["data"])

    def list_evidence(self, claim: Optional[str] = None) -> list[EvidenceRecord]:
        """List evidence records."""
        if claim:
            rows = self.conn.execute(
                "SELECT data FROM evidence_records WHERE claim LIKE ? ORDER BY evidence_level",
                (f"%{claim}%",),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT data FROM evidence_records ORDER BY evidence_level"
            ).fetchall()
        return [EvidenceRecord.model_validate_json(row["data"]) for row in rows]

    # -------------------------------------------------------------------
    # Decision Records
    # -------------------------------------------------------------------

    def save_decision(self, decision: DecisionRecord) -> None:
        """Insert a decision record. Decisions are NEVER overwritten."""
        data = decision.model_dump_json()
        self.conn.execute(
            """INSERT INTO decision_records (decision_id, question, decision, data)
               VALUES (?, ?, ?, ?)""",
            (decision.decision_id, decision.question, decision.decision, data),
        )
        self.conn.commit()

    def get_decision(self, decision_id: str) -> Optional[DecisionRecord]:
        """Retrieve a decision record by ID."""
        row = self.conn.execute(
            "SELECT data FROM decision_records WHERE decision_id = ?", (decision_id,)
        ).fetchone()
        if row is None:
            return None
        return DecisionRecord.model_validate_json(row["data"])

    def list_decisions(self) -> list[DecisionRecord]:
        """List all decision records (never deleted, versioned)."""
        rows = self.conn.execute(
            "SELECT data FROM decision_records ORDER BY rowid"
        ).fetchall()
        return [DecisionRecord.model_validate_json(row["data"]) for row in rows]


# ---------------------------------------------------------------------------
# SQL Schema
# ---------------------------------------------------------------------------

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS targets (
    target_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    sequence TEXT NOT NULL,
    target_hash TEXT NOT NULL,
    data TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS candidates (
    candidate_id TEXT PRIMARY KEY,
    target_id TEXT NOT NULL,
    sequence TEXT NOT NULL,
    sequence_hash TEXT NOT NULL,
    status TEXT NOT NULL,
    scientific_status TEXT NOT NULL,
    generator TEXT NOT NULL,
    data TEXT NOT NULL,
    FOREIGN KEY (target_id) REFERENCES targets(target_id)
);

CREATE INDEX IF NOT EXISTS idx_candidates_target ON candidates(target_id);
CREATE INDEX IF NOT EXISTS idx_candidates_status ON candidates(status);
CREATE INDEX IF NOT EXISTS idx_candidates_hash ON candidates(sequence_hash);
CREATE INDEX IF NOT EXISTS idx_candidates_generator ON candidates(generator);

CREATE TABLE IF NOT EXISTS experiment_runs (
    run_id TEXT PRIMARY KEY,
    target_id TEXT NOT NULL,
    status TEXT NOT NULL,
    data TEXT NOT NULL,
    FOREIGN KEY (target_id) REFERENCES targets(target_id)
);

CREATE TABLE IF NOT EXISTS evidence_records (
    evidence_id TEXT PRIMARY KEY,
    claim TEXT NOT NULL,
    evidence_level INTEGER NOT NULL,
    data TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS decision_records (
    decision_id TEXT PRIMARY KEY,
    question TEXT NOT NULL,
    decision TEXT NOT NULL,
    data TEXT NOT NULL
);
"""
