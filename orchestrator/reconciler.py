def validate_diff(container_id, repo) -> str:
    """Read and validate the diff produced inside the sandbox."""
    raise NotImplementedError


def apply_diff(container_id: str, repo) -> None:
    """Apply the validated diff to the real repo."""
    raise NotImplementedError
