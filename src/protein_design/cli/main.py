"""CLI — Command-line interface for the protein design system.

Commands:
    protein-design run demo       Run dummy end-to-end pipeline
    protein-design target add     Add a target from YAML
    protein-design target list    List all targets
    protein-design candidate list List candidates
    protein-design candidate inspect <id>  Show candidate details
    protein-design audit report   Show audit/decision history
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from protein_design.logging import setup_logging

app = typer.Typer(
    name="protein-design",
    help="AI Protein Design System — Changjiang Cup 2026",
    add_completion=False,
)
console = Console()

# Sub-commands
run_app = typer.Typer(help="Run pipeline commands")
target_app = typer.Typer(help="Manage targets")
candidate_app = typer.Typer(help="Manage candidates")
audit_app = typer.Typer(help="Audit and decisions")
benchmark_app = typer.Typer(help="Benchmark management")

app.add_typer(run_app, name="run")
app.add_typer(target_app, name="target")
app.add_typer(candidate_app, name="candidate")
app.add_typer(audit_app, name="audit")
app.add_typer(benchmark_app, name="benchmark")


def _get_project_root() -> Path:
    """Find the project root by looking for pyproject.toml."""
    current = Path.cwd()
    for parent in [current, *current.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    return current


def _get_db():
    """Get the metadata store."""
    from protein_design.storage.database import MetadataStore

    root = _get_project_root()
    db = MetadataStore(root / "protein_design.db")
    db.initialize()
    return db


def _get_artifacts():
    """Get the artifact store."""
    from protein_design.storage.artifacts import ArtifactStore

    root = _get_project_root()
    return ArtifactStore(root / "candidates")


# ---------------------------------------------------------------------------
# run demo
# ---------------------------------------------------------------------------

@run_app.command("demo")
def run_demo(
    num_candidates: int = typer.Option(10, "--num", "-n", help="Number of candidates"),
    seed: int = typer.Option(42, "--seed", "-s", help="Random seed"),
    config_file: Optional[Path] = typer.Option(None, "--config", "-c", help="Config YAML"),
):
    """Run the dummy end-to-end pipeline demo."""
    setup_logging()

    from protein_design.config.loader import PipelineConfig, load_config
    from protein_design.core.pipeline import Pipeline
    from protein_design.generators.dummy import DummyGenerator
    from protein_design.predictors.dummy import DummyPredictor
    from protein_design.validation.dummy import DummyValidator
    from protein_design.schemas import Target

    console.print("\n[bold green]== AI Protein Design System -- Demo Pipeline ==[/bold green]\n")

    # Load config
    if config_file:
        config = load_config(base_path=config_file)
    else:
        config = PipelineConfig()

    config.generation.num_candidates = num_candidates
    config.generation.random_seed = seed

    # Create a demo target
    target = Target(
        target_id="demo_target_001",
        name="Demo Target (Dummy)",
        source="demo",
        sequence="MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLA",
        source_references=["demo_pipeline_test"],
    )

    # Initialize components
    db = _get_db()
    artifacts = _get_artifacts()
    generator = DummyGenerator()
    predictor = DummyPredictor()
    validator = DummyValidator()

    pipeline = Pipeline(
        config=config,
        generator=generator,
        predictor=predictor,
        validator=validator,
        db=db,
        artifacts=artifacts,
    )

    # Run pipeline
    console.print(f"  Target:      [cyan]{target.name}[/cyan]")
    console.print(f"  Generator:   [cyan]{generator.name} v{generator.version}[/cyan]")
    console.print(f"  Predictor:   [cyan]{predictor.name} v{predictor.version}[/cyan]")
    console.print(f"  Validator:   [cyan]{validator.name}[/cyan]")
    console.print(f"  Candidates:  [cyan]{num_candidates}[/cyan]")
    console.print(f"  Seed:        [cyan]{seed}[/cyan]")
    console.print()

    run = pipeline.run(target)

    # Report results
    status_color = "green" if run.status.value == "COMPLETED" else "yellow"
    console.print(f"\n[bold]Pipeline completed: [{status_color}]{run.status.value}[/{status_color}][/bold]")

    if run.output_summary:
        table = Table(title="Results Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        for key, value in run.output_summary.items():
            table.add_row(key, str(value))
        console.print(table)

    # Show candidates
    candidates = db.list_candidates(target_id=target.target_id)
    if candidates:
        ctable = Table(title=f"Candidates ({len(candidates)} total)")
        ctable.add_column("ID", style="cyan")
        ctable.add_column("Length", style="white")
        ctable.add_column("Status", style="green")
        ctable.add_column("pLDDT", style="yellow")
        ctable.add_column("ipTM", style="yellow")
        for c in candidates[:20]:  # Show first 20
            plddt = c.metrics.get("plddt", "-")
            iptm = c.metrics.get("iptm", "-")
            ctable.add_row(
                c.candidate_id,
                str(c.length),
                c.status.value,
                str(plddt),
                str(iptm),
            )
        console.print(ctable)

    console.print(f"\n  Run ID:     [dim]{run.run_id}[/dim]")
    console.print(f"  Database:   [dim]{db.db_path}[/dim]")
    console.print(f"  Artifacts:  [dim]{artifacts.base_dir}[/dim]")
    console.print()

    db.close()


# ---------------------------------------------------------------------------
# target commands
# ---------------------------------------------------------------------------

@target_app.command("list")
def target_list():
    """List all registered targets."""
    setup_logging()
    db = _get_db()
    targets = db.list_targets()

    if not targets:
        console.print("[yellow]No targets found.[/yellow]")
        return

    table = Table(title="Targets")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="white")
    table.add_column("Sequence Length", style="green")
    table.add_column("Source", style="dim")

    for t in targets:
        table.add_row(t.target_id, t.name, str(t.sequence_length), t.source)

    console.print(table)
    db.close()


@target_app.command("add")
def target_add(
    yaml_file: Path = typer.Argument(..., help="Path to target YAML file"),
):
    """Add a target from a YAML file."""
    setup_logging()
    import yaml
    from protein_design.schemas import Target

    with open(yaml_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    target = Target(**data)
    db = _get_db()
    db.save_target(target)
    console.print(f"[green]Target added: {target.target_id} ({target.name})[/green]")
    db.close()


# ---------------------------------------------------------------------------
# candidate commands
# ---------------------------------------------------------------------------

@candidate_app.command("list")
def candidate_list(
    target: Optional[str] = typer.Option(None, "--target", "-t", help="Filter by target ID"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status"),
    limit: int = typer.Option(50, "--limit", "-l", help="Max results"),
):
    """List candidates with optional filters."""
    setup_logging()
    db = _get_db()
    candidates = db.list_candidates(target_id=target, status=status, limit=limit)

    if not candidates:
        console.print("[yellow]No candidates found.[/yellow]")
        return

    table = Table(title=f"Candidates ({len(candidates)} shown)")
    table.add_column("ID", style="cyan")
    table.add_column("Target", style="dim")
    table.add_column("Length", style="white")
    table.add_column("Generator", style="blue")
    table.add_column("Status", style="green")
    table.add_column("Scientific", style="magenta")

    for c in candidates:
        table.add_row(
            c.candidate_id,
            c.target_id,
            str(c.length),
            c.generator,
            c.status.value,
            c.scientific_status.value,
        )

    console.print(table)
    db.close()


@candidate_app.command("inspect")
def candidate_inspect(
    candidate_id: str = typer.Argument(..., help="Candidate ID"),
):
    """Show detailed information about a candidate."""
    setup_logging()
    db = _get_db()
    candidate = db.get_candidate(candidate_id)

    if candidate is None:
        console.print(f"[red]Candidate not found: {candidate_id}[/red]")
        raise typer.Exit(1)

    console.print(f"\n[bold cyan]Candidate: {candidate.candidate_id}[/bold cyan]\n")

    # Basic info
    info_table = Table(show_header=False, box=None)
    info_table.add_column("Field", style="dim")
    info_table.add_column("Value")
    info_table.add_row("Target", candidate.target_id)
    info_table.add_row("Generator", f"{candidate.generator} v{candidate.generator_version}")
    info_table.add_row("Design Type", candidate.design_type.value)
    info_table.add_row("Length", str(candidate.length))
    info_table.add_row("Status", candidate.status.value)
    info_table.add_row("Scientific Status", candidate.scientific_status.value)
    info_table.add_row("Seed", str(candidate.seed))
    info_table.add_row("Sequence Hash", candidate.sequence_hash[:16] + "...")
    info_table.add_row("Created", str(candidate.created_at))
    console.print(info_table)

    # Sequence
    console.print(f"\n[bold]Sequence:[/bold]")
    console.print(f"  {candidate.sequence[:80]}{'...' if len(candidate.sequence) > 80 else ''}")

    # Metrics
    if candidate.metrics:
        console.print(f"\n[bold]Metrics:[/bold]")
        for k, v in candidate.metrics.items():
            console.print(f"  {k}: {v}")

    # Status history
    if candidate.status_history:
        console.print(f"\n[bold]Status History:[/bold]")
        hist_table = Table()
        hist_table.add_column("From", style="dim")
        hist_table.add_column("To", style="cyan")
        hist_table.add_column("Stage", style="blue")
        hist_table.add_column("Reason", style="white")
        hist_table.add_column("Timestamp", style="dim")
        for h in candidate.status_history:
            hist_table.add_row(
                h.from_status.value,
                h.to_status.value,
                h.stage,
                h.reason,
                str(h.timestamp)[:19],
            )
        console.print(hist_table)

    # Provenance
    if candidate.provenance:
        console.print(f"\n[bold]Provenance:[/bold]")
        prov = candidate.provenance
        prov_table = Table(show_header=False, box=None)
        prov_table.add_column("Field", style="dim")
        prov_table.add_column("Value")
        prov_table.add_row("Run ID", prov.run_id)
        prov_table.add_row("Generator", f"{prov.generator} v{prov.generator_version}")
        prov_table.add_row("Config Hash", prov.config_hash[:16] + "...")
        prov_table.add_row("Git Commit", prov.git_commit or "N/A")
        prov_table.add_row("Hardware", prov.hardware or "N/A")
        prov_table.add_row("Seed", str(prov.random_seed))
        console.print(prov_table)

    console.print()
    db.close()


# ---------------------------------------------------------------------------
# audit commands
# ---------------------------------------------------------------------------

@audit_app.command("report")
def audit_report():
    """Show audit/decision history."""
    setup_logging()
    from protein_design.evidence.registry import EvidenceRegistry

    db = _get_db()
    registry = EvidenceRegistry(db)

    decisions = registry.get_decision_history()
    if not decisions:
        console.print("[yellow]No decisions recorded yet.[/yellow]")
        db.close()
        return

    table = Table(title="Decision History")
    table.add_column("ID", style="cyan")
    table.add_column("Question", style="white")
    table.add_column("Decision", style="green")
    table.add_column("Confidence", style="yellow")
    table.add_column("Author", style="dim")
    table.add_column("Date", style="dim")

    for d in decisions:
        table.add_row(
            d.decision_id,
            d.question[:50],
            d.decision[:50],
            f"{d.confidence:.2f}",
            d.author,
            str(d.date)[:10],
        )

    console.print(table)
    db.close()


if __name__ == "__main__":
    app()
