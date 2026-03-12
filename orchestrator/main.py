import typer
from pathlib import Path
from lifecycle import spawn, teardown
from reconciler import validate_diff

app = typer.Typer(help="Hardened Agentic Coder — local isolated coding agent")


@app.command()
def run(
    repo: Path = typer.Option(..., help="Path to the local git repository"),
    task: str = typer.Option(..., help="Coding task description for the agent"),
):
    """
    Spin up a sandboxed coding agent, run a task, and propose a diff.
    """
    # 1. Validate repo
    if not repo.exists() or not (repo / ".git").exists():
        typer.echo(f"[ERROR] {repo} is not a valid git repository", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"[*] Repo     : {repo}")
    typer.echo(f"[*] Task     : {task}")

    # 2. Spawn sandbox
    typer.echo("[*] Spawning sandbox...")
    container_id = spawn(repo)
    typer.echo(f"[+] Sandbox up : {container_id[:12]}")

    try:
        # 3. Placeholder — MCP server call (Phase 3)
        typer.echo("[*] Agent running... (MCP stub — Phase 3)")

        # 4. Validate diff
        typer.echo("[*] Validating diff...")
        diff = validate_diff(container_id, repo)

        if not diff:
            typer.echo("[!] No changes proposed by agent.")
            raise typer.Exit(code=0)

        typer.echo("\n--- PROPOSED DIFF ---")
        typer.echo(diff)
        typer.echo("---------------------\n")

        # 5. Human confirmation
        confirm = typer.confirm("Apply this diff to your repo?")
        if confirm:
            typer.echo("[+] Diff applied.")
        else:
            typer.echo("[!] Diff rejected — repo unchanged.")

    finally:
        # 6. Always teardown
        typer.echo("[*] Tearing down sandbox...")
        teardown(container_id)
        typer.echo("[+] Sandbox destroyed.")


if __name__ == "__main__":
    app()
