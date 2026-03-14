import json
import sys
import uuid
from datetime import datetime

import ollama

from scrubber import scrub_input, scrub_output
from telemetry import log_session
from token_counter import count_tokens

OLLAMA_MODEL = "deepseek-coder-v2:16b"


def handle_request(request: dict) -> dict:
    """
    Process a single MCP request from the orchestrator.

    Args:
        request: A dict with keys 'task' and 'project_id'.

    Returns:
        A dict with keys 'diff' and 'session_id'.
    """
    session_id = str(uuid.uuid4())
    started_at = datetime.now()

    # 1. Scrub prompt entrant
    raw_task = request.get("task", "")
    clean_task = scrub_input(raw_task)

    # 2. Compter les prompt tokens
    prompt_tokens = count_tokens(clean_task)

    # 3. Appel Ollama
    response = ollama.chat(
        model=OLLAMA_MODEL,
        messages=[{"role": "user", "content": clean_task}],
    )
    raw_output = response["message"]["content"]

    # 4. Compter les completion tokens
    completion_tokens = count_tokens(raw_output)

    # 5. Scrub diff sortant
    clean_output = scrub_output(raw_output)

    ended_at = datetime.now()

    # 6. Logger la session
    log_session(
        session_id=session_id,
        feature_tag=request.get("feature_tag", "unknown"),
        project_id=request.get("project_id", "unknown"),
        task=clean_task,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        started_at=started_at,
        ended_at=ended_at,
    )

    return {"diff": clean_output, "session_id": session_id}


def main() -> None:
    """
    MCP server main loop — reads JSON requests from stdin, writes responses to stdout.
    """
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            response = handle_request(request)
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
        except json.JSONDecodeError as e:
            error = {"error": f"Invalid JSON: {e}"}
            sys.stdout.write(json.dumps(error) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
