from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from coral.grader import TaskGrader
from coral.types import ScoreBundle


class AgentGrader(TaskGrader):
    """
    Spawns an agent (e.g., Claude Code or OpenCode) as a Judge in an isolated
    workspace. The agent is given a rubric to explore the codebase, run tests,
    and evaluate the code. It outputs a JSON score and feedback.
    """

    def evaluate(self) -> float | ScoreBundle:
        rubric = self.args.get(
            "rubric", "Evaluate the codebase and provide a score between 0.0 and 1.0."
        )
        agent_command = self.args.get("agent_command", ["claude", "-p", "{prompt}"])

        prompt = (
            f"You are a Judge Agent evaluating a worker's code submission.\n\n"
            f"RUBRIC:\n{rubric}\n\n"
            f"Your instructions:\n"
            f"1. Explore the workspace, read files, run tests, or use tools to evaluate the submission.\n"
            f"2. When you are finished, output a single JSON object on its own line containing your final evaluation.\n"
            f'3. The JSON must exactly match this format: {{"score": float, "feedback": "str"}}\n'
            f"4. 'score' must be a float (e.g., 0.0 to 1.0).\n"
            f"5. Do NOT output any text after the JSON object.\n"
        )

        with tempfile.TemporaryDirectory() as tempdir:
            isolated_path = Path(tempdir) / "workspace"

            # Create an isolated environment by copying the codebase
            # Ignore .git and .coral to avoid messing with the main workspace's state
            shutil.copytree(
                self.codebase_path,
                isolated_path,
                ignore=shutil.ignore_patterns(".git", ".coral"),
            )

            # Write prompt to file in case the command wants to read it from a file
            prompt_path = isolated_path / "JUDGE_PROMPT.txt"
            prompt_path.write_text(prompt, encoding="utf-8")

            # Prepare the command
            cmd = []
            for arg in agent_command:
                if isinstance(arg, str):
                    cmd.append(
                        arg.format(prompt=prompt, prompt_path=str(prompt_path), rubric=rubric)
                    )
                else:
                    cmd.append(arg)

            try:
                result = subprocess.run(
                    cmd,
                    cwd=isolated_path,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                )
                stdout = result.stdout
                stderr = result.stderr
            except subprocess.TimeoutExpired as e:
                stdout = (
                    e.stdout
                    if isinstance(e.stdout, str)
                    else (e.stdout.decode() if e.stdout else "")
                )
                stderr = (
                    e.stderr
                    if isinstance(e.stderr, str)
                    else (e.stderr.decode() if e.stderr else "")
                )
                return self.fail(
                    explanation=f"Judge agent timed out after {self.timeout}s.",
                    feedback=f"Stdout:\n{stdout[-1000:]}\n\nStderr:\n{stderr[-1000:]}",
                )
            except Exception as e:
                return self.fail(
                    explanation=f"Error running Judge agent: {e}",
                )

            return self._parse_result(stdout, stderr)

    def _parse_result(self, stdout: str, stderr: str) -> ScoreBundle:
        output = stdout + "\n" + stderr

        # Scan lines in reverse for a JSON object containing "score"
        for line in reversed(output.splitlines()):
            line = line.strip()
            if line.startswith("{") and line.endswith("}"):
                try:
                    data = json.loads(line)
                    if "score" in data:
                        return self.bundle(
                            value=float(data["score"]),
                            feedback=data.get("feedback", ""),
                        )
                except json.JSONDecodeError:
                    continue

        return self.fail(
            explanation="Failed to parse JSON with 'score' and 'feedback' from Judge agent output.",
            feedback=f"Stdout:\n{stdout[-1000:]}\n\nStderr:\n{stderr[-1000:]}",
        )
