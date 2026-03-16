import shutil
import tempfile
import uuid
import os
from pathlib import Path

import git
import podman

CONTAINER_IMAGE = "localhost/hardened-agent-sandbox:1.0"
SANDBOX_MEMORY = "2g"
SANDBOX_CPUS = 2.0


def _podman_client() -> podman.PodmanClient:
    """Return a PodmanClient connected to the rootless socket."""
    socket_path = f"unix://{os.environ['XDG_RUNTIME_DIR']}/podman/podman.sock"
    return podman.PodmanClient(base_url=socket_path)


def spawn(repo: Path, docs: Path | None = None) -> str:
    """
    Create a shadow clone of the repo and spin up a hardened sandbox container.

    Args:
        repo: Path to the local git repository.

    Returns:
        The container ID of the running sandbox.
    """
    # 1. Shadow clone en RAM
    shadow_dir = Path(
        tempfile.mkdtemp(prefix=f"agent-{uuid.uuid4().hex[:8]}-", dir="/dev/shm")
    )
    git.Repo.clone_from(str(repo), str(shadow_dir))

    # Shadow clone en RAM — /dev/shm est tmpfs, éphémère par nature
    # noexec géré côté container via les options de mount Podman

    # 3. Connexion au socket Podman rootless
    client = _podman_client()

    # 3.1. Préparer les mounts
    mounts = [
        {
            "type": "bind",
            "source": str(shadow_dir),
            "target": "/workspace",
            "options": ["rw", "noexec"],
        },
    ]

    # Monter la doc en read-only si fournie
    if docs and docs.exists():
        mounts.append(
            {
                "type": "bind",
                "source": str(docs),
                "target": "/docs",
                "options": ["ro"],
            }
        )

    # 4. Démarrer le container durci*
    container = client.containers.run(
        CONTAINER_IMAGE,
        command=["sleep", "infinity"],
        detach=True,
        remove=False,
        mounts=mounts,
        security_opt=["no-new-privileges"],
        cap_drop=["ALL"],
        read_only=True,
        network_mode="none",
        mem_limit=SANDBOX_MEMORY,
        cpu_quota=int(SANDBOX_CPUS * 100000),
        labels={"agent.shadow_dir": str(shadow_dir)},
    )

    return container.id


def teardown(container_id: str) -> None:
    """
    Stop and remove the sandbox container, then clean up the shadow clone.

    Args:
        container_id: The container ID returned by spawn().
    """
    client = _podman_client()
    container = client.containers.get(container_id)

    shadow_dir = container.labels.get("agent.shadow_dir")

    container.stop()
    container.remove()

    # Nettoyer le shadow clone en RAM
    if shadow_dir and Path(shadow_dir).exists():
        shutil.rmtree(shadow_dir)
