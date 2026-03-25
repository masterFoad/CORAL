"""Frontier-CS Algorithmic single-problem grader.

Evaluates a single C++ solution against a go-judge server.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

from pathlib import Path

from coral.grader import TaskGrader
from coral.types import ScoreBundle

POLL_INTERVAL = 2
POLL_TIMEOUT = 1000


class Grader(TaskGrader):
    """Single-problem grader for a Frontier-CS algorithmic problem."""

    def evaluate(self) -> ScoreBundle:
        judge_url = self.args.get("judge_url", "http://localhost:8081")
        problem_id = self.args.get("problem_id")
        if not problem_id:
            return self.fail("grader arg 'problem_id' is required")

        solutions_dir = Path(self.codebase_path) / "solutions"
        sol_file = solutions_dir / f"{problem_id}.cpp"

        if not sol_file.exists():
            return self.score(0.0, feedback=f"No solution found: solutions/{problem_id}.cpp")

        code = sol_file.read_text(encoding="utf-8")

        try:
            score, status_str = _submit_and_poll(judge_url, problem_id, code)
        except Exception as e:
            return self.score(0.0, feedback=f"problem {problem_id}: error: {e}")

        return self.score(score, feedback=f"problem {problem_id}: {score:.2f} ({status_str})")


def _submit_and_poll(
    judge_url: str, problem_id: str, code: str
) -> tuple[float, str]:
    """Submit code to the judge and poll for results."""
    payload = json.dumps({
        "pid": problem_id,
        "code": code,
        "lang": "cpp",
    }).encode()
    req = urllib.request.Request(
        f"{judge_url}/submit",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req) as resp:
            submit_data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return 0.0, f"submit failed ({e.code})"

    submission_id = submit_data["submission_id"]

    deadline = time.monotonic() + POLL_TIMEOUT
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"{judge_url}/result/{submission_id}") as resp:
                result_data = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            return 0.0, f"poll failed ({e.code})"

        status = result_data.get("status", "")
        if status == "done":
            return float(result_data.get("score", 0.0)), "ok"
        if status == "error":
            return 0.0, f"error: {result_data.get('message', 'unknown')}"

        time.sleep(POLL_INTERVAL)

    return 0.0, "timeout"
