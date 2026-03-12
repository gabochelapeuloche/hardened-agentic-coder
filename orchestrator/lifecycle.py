def spawn(repo) -> str:
    """Spin up a sandboxed container with a shadow clone of the repo."""
    raise NotImplementedError


def teardown(container_id: str) -> None:
    """Destroy the sandbox container."""
    raise NotImplementedError
