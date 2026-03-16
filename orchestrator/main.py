import typer
import subprocess
import os
import json
from pathlib import Path
from lifecycle import spawn, teardown
from reconciler import apply_diff, validate_diff

app = typer.Typer(help="Hardened Agentic Coder — local isolated coding agent")


@app.command()
def run(
    repo: Path = typer.Option(..., help="Path to the local git repository"),
    task: str = typer.Option(..., help="Coding task description for the agent"),
    docs: Path | None = typer.Option(
        None, help="Path to documentation directory (read-only)"
    ),
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
    container_id = spawn(repo, docs=docs)
    typer.echo(f"[+] Sandbox up : {container_id[:12]}")

    try:
        # 3. Appel MCP server
        typer.echo("[*] Agent running...")
        mcp_request = json.dumps(
            {
                "task": task,
                "project_id": repo.name,
                "feature_tag": "feature",
                "container_id": container_id,
            }
        )

        mcp_python = (
            Path(__file__).parent.parent / "mcp-server" / ".venv" / "bin" / "python3"
        )
        mcp_server = Path(__file__).parent.parent / "mcp-server" / "server.py"

        mcp_proc = subprocess.run(
            [str(mcp_python), str(mcp_server)],
            input=mcp_request,
            stdout=subprocess.PIPE,  # capture stdout (la réponse JSON)
            stderr=None,  # stderr va directement sur le terminal
            text=True,
            env={**os.environ, "AGENT_VERBOSE": "1"},
        )

        # Afficher les logs verbose du MCP server
        # if mcp_proc.stderr:
        #     typer.echo(mcp_proc.stderr)

        # Parser la réponse
        mcp_response = json.loads(mcp_proc.stdout)
        typer.echo(f"[+] Agent done : {mcp_response.get('summary', '')}")

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
            apply_diff(container_id, repo)
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
