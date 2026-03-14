import json
import os
import sys
import uuid
import re
import ollama
import podman
from datetime import datetime
from scrubber import scrub_input, scrub_output
from telemetry import log_session
from token_counter import count_tokens

OLLAMA_MODEL = "deepseek-coder-v2:16b"
MAX_ITERATIONS = 5

REACT_SYSTEM_PROMPT = """You are a coding agent operating inside a sandboxed environment.
You have access to the following actions:

- read_file: Read a file from the workspace
- write_file: Write or modify a file in the workspace
- run_tests: Run the test suite in the workspace
- task_complete: Signal that the task is complete

You must respond ONLY with a JSON object in this exact format:
{
    "thought": "your reasoning about what to do next",
    "action": "one of: read_file, write_file, run_tests, task_complete",
    "params": {}
}

For read_file: params = {"path": "/workspace/filename"}
For write_file: params = {"path": "/workspace/filename", "content": "file content"}
For run_tests: params = {}
For task_complete: params = {"summary": "what was done"}

Never output anything outside the JSON object.
The workspace is at /workspace. Only modify files in /workspace.
"""

VERBOSE = True

def set_verbose(value: bool) -> None:
    """Enable or disable verbose logging."""
    global VERBOSE
    VERBOSE = value

def _log(msg: str) -> None:
    """Print a message to stderr if verbose mode is enabled."""
    if VERBOSE:
        print(msg, file=sys.stderr)

def _extract_json(raw: str) -> str:
    """Strip markdown code fences from LLM response."""
    # Retire ```json ... ``` ou ``` ... ```
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", raw, re.DOTALL)
    if match:
        return match.group(1)
    return raw.strip()

def _podman_client() -> podman.PodmanClient:
    """Return a PodmanClient connected to the rootless socket."""
    socket_path = f"unix://{os.environ['XDG_RUNTIME_DIR']}/podman/podman.sock"
    return podman.PodmanClient(base_url=socket_path)


def execute_action(container_id: str, action: str, params: dict) -> str:
    """
    Execute a ReAct action inside the sandbox container.

    Args:
        container_id: The running sandbox container ID.
        action: The action name.
        params: Action parameters.

    Returns:
        The observation string to feed back to the LLM.
    """
    client = _podman_client()
    container = client.containers.get(container_id)

    if action == "read_file":
        path = params.get("path", "")
        exit_code, output = container.exec_run(["cat", path])
        return output.decode() if output else "[empty file]"

    elif action == "write_file":
        path = params.get("path", "")
        content = params.get("content", "")
        exit_code, output = container.exec_run(
            ["sh", "-c", f"cat > {path} << 'AGENT_EOF'\n{content}\nAGENT_EOF"]
        )
        return f"[written {len(content)} chars to {path}]"

    elif action == "run_tests":
        exit_code, output = container.exec_run(
            ["sh", "-c", "cd /workspace && python -m pytest -x -q 2>&1 || true"]
        )
        return output.decode() if output else "[no output]"

    elif action == "task_complete":
        return f"[task complete] {params.get('summary', '')}"

    else:
        return f"[unknown action: {action}]"


def react_loop(container_id: str, task: str) -> str:
    """
    Run the ReAct loop for a given task inside the sandbox.

    Args:
        container_id: The running sandbox container ID.
        task: The coding task description.

    Returns:
        A summary of what was done.
    """
    messages = [
        {"role": "system", "content": REACT_SYSTEM_PROMPT},
        {"role": "user", "content": f"Task: {task}"},
    ]

    for iteration in range(MAX_ITERATIONS):
        # Appel LLM
        response = ollama.chat(model=OLLAMA_MODEL, messages=messages)
        raw = response["message"]["content"]

        # Parser la réponse JSON
        try:
            step = json.loads(_extract_json(raw))
        except json.JSONDecodeError:
            # Le LLM n'a pas respecté le format JSON — on le signale et on continue
            messages.append({"role": "assistant", "content": raw})
            messages.append(
                {
                    "role": "user",
                    "content": "Your response was not valid JSON. Please respond with a JSON object only.",
                }
            )
            continue

        thought = step.get("thought", "")
        action = step.get("action", "")
        params = step.get("params", {})

        # Logger l'iteration sur stderr pour debug
        _log(f"[{iteration+1}/{MAX_ITERATIONS}] {action}: {thought[:80]}")

        # Ajouter la réponse de l'agent à l'historique
        messages.append({"role": "assistant", "content": raw})

        # Condition de sortie
        if action == "task_complete":
            return params.get("summary", "task complete")

        # Exécuter l'action et récupérer l'observation
        observation = execute_action(container_id, action, params)
        observation = scrub_output(observation)

        # Ajouter l'observation à l'historique
        messages.append({"role": "user", "content": f"Observation: {observation}"})

    return "max iterations reached"


def handle_request(request: dict) -> dict:
    """
    Process a single MCP request from the orchestrator.

    Args:
        request: A dict with keys 'task', 'project_id', 'feature_tag', 'container_id'.

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

    # 3. Boucle ReAct
    container_id = request.get("container_id", "")
    summary = react_loop(container_id, clean_task)

    # 4. Scrub sortant
    clean_summary = scrub_output(summary)

    # 5. Compter completion tokens
    completion_tokens = count_tokens(clean_summary)

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

    return {"summary": clean_summary, "session_id": session_id}

def main() -> None:
    """
    MCP server main loop — reads JSON requests from stdin, writes responses to stdout.
    """
    
    if os.environ.get("AGENT_VERBOSE", "").lower() in ("1", "true", "yes"):
        set_verbose(True)

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
