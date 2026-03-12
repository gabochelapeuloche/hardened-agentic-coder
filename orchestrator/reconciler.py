import podman
import git
from pathlib import Path


def validate_diff(container_id: str, repo: Path) -> str:
    """Read and validate the diff produced inside the sandbox."""

    # Instancie le client podman pour récupérer le mount fs dans les labels
    client = podman.PodmanClient()
    container = client.containers.get(container_id)
    shadow_dir = container.labels.get("agent.shadow_dir")

    # returns the diff file in a string
    shadow_repo = git.Repo(shadow_dir)
    return shadow_repo.git.diff()


def apply_diff(container_id: str, repo: Path) -> None:
    """Apply the validated diff to the real repo."""

    # Récupérer le diff depuis le shadow clone
    diff = validate_diff(container_id, repo)

    # Appliquer sur le vrai repo
    real_repo = git.Repo(repo)
    real_repo.git.apply(diff)
