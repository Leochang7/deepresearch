import typer

app = typer.Typer(
    name="deepresearch",
    help="DeepResearch Agent - multi-agent deep research system",
    no_args_is_help=True,
)


@app.command()
def run(
    question: str = typer.Argument(help="Research question"),
    config: str | None = typer.Option(
        None, "--config", "-c", help="Path to config file"
    ),
) -> None:
    """Run a deep research task."""
    typer.echo(f"Question: {question}")
    typer.echo("Not yet implemented.")


@app.command()
def init() -> None:
    """Initialize a new deepresearch project."""
    typer.echo("Not yet implemented.")


@app.command()
def index_corpus(
    path: str = typer.Argument(help="Path to corpus directory"),
) -> None:
    """Index a local corpus for retrieval."""
    typer.echo(f"Corpus: {path}")
    typer.echo("Not yet implemented.")


@app.command()
def eval(
    run_id: str = typer.Argument(help="Run ID to evaluate"),
) -> None:
    """Evaluate a completed research run."""
    typer.echo(f"Run: {run_id}")
    typer.echo("Not yet implemented.")


@app.command()
def inspect(
    run_id: str = typer.Argument(help="Run ID to inspect"),
) -> None:
    """Inspect trace and outputs of a research run."""
    typer.echo(f"Run: {run_id}")
    typer.echo("Not yet implemented.")


@app.command()
def config() -> None:
    """Show current configuration."""
    typer.echo("Not yet implemented.")
