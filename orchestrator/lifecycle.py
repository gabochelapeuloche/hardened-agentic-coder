import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

import git
import podman

CONTAINER_IMAGE = "docker.io/library/alpine:3.21"
SANDBOX_MEMORY = "2g"
SANDBOX_CPUS = 2.0


def spawn(repo: Path) -> str:
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

    # 2. Remonter le shadow dir en noexec sur le host
    subprocess.run(
        ["mount", "--bind", "-o", "remount,noexec", str(shadow_dir), str(shadow_dir)],
        check=True,
    )

    # 3. Connexion au socket Podman rootless
    client = podman.PodmanClient()

    # 4. Démarrer le container durci
    container = client.containers.run(
        CONTAINER_IMAGE,
        command=["sleep", "infinity"],
        detach=True,
        remove=False,
        mounts=[
            {
                "type": "bind",
                "source": str(shadow_dir),
                "target": "/workspace",
                "options": ["rw"],
            }
        ],
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
    client = podman.PodmanClient()
    container = client.containers.get(container_id)

    shadow_dir = container.labels.get("agent.shadow_dir")

    container.stop()
    container.remove()

    # Nettoyer le shadow clone en RAM
    if shadow_dir and Path(shadow_dir).exists():
        shutil.rmtree(shadow_dir)
