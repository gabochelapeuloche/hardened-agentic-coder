import podman
import git
import os
import tempfile
from pathlib import Path


def _podman_client() -> podman.PodmanClient:
    """Return a PodmanClient connected to the rootless socket."""
    socket_path = f"unix://{os.environ['XDG_RUNTIME_DIR']}/podman/podman.sock"
    return podman.PodmanClient(base_url=socket_path)


def validate_diff(container_id: str, repo: Path) -> str:
    """Read and validate the diff produced inside the sandbox."""

    client = _podman_client()
    container = client.containers.get(container_id)
    shadow_dir = container.labels.get("agent.shadow_dir")

    shadow_repo = git.Repo(shadow_dir)

    # Stager tous les changements y compris nouveaux fichiers
    shadow_repo.git.add("--all")

    # Diff entre l'index et le dernier commit (ou tree vide si repo sans commit)
    try:
        diff = shadow_repo.git.diff("HEAD", "--cached")
    except git.GitCommandError:
        # Repo sans commit — comparer avec le tree vide
        diff = shadow_repo.git.diff("--cached")

    return diff


def apply_diff(container_id: str, repo: Path) -> None:
    """Apply the validated diff to the real repo."""

    diff = validate_diff(container_id, repo)

    # Écrire le diff dans un fichier temporaire
    with tempfile.NamedTemporaryFile(mode="w", suffix=".patch", delete=False) as f:
        f.write(diff)
        patch_path = f.name

        # print(f"[DEBUG] patch path: {patch_path}", file=sys.stderr)
        # print(f"[DEBUG] diff repr: {repr(diff[:200])}", file=sys.stderr)

    real_repo = git.Repo(repo)
    real_repo.git.apply("--allow-empty", patch_path)

    # Nettoyer le fichier temporaire
    Path(patch_path).unlink()
