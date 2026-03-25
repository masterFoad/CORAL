"""Frontier-CS Research single-problem grader.

Evaluates Python solution(s) for one specific problem via Docker-based evaluation.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

import yaml

from coral.grader import TaskGrader
from coral.types import Score, ScoreBundle

DEFAULT_TIMEOUT = 600


class Grader(TaskGrader):
    """Single-problem grader for a Frontier-CS research problem."""

    def evaluate(self) -> ScoreBundle:
        problems_dir = self.args.get("problems_dir")
        problem_id = self.args.get("problem_id")

        if not problems_dir:
            return self.fail("grader arg 'problems_dir' is required")
        if not problem_id:
            return self.fail("grader arg 'problem_id' is required")

        problems_path = Path(problems_dir)
        problem_dir = problems_path / problem_id
        if not problem_dir.exists():
            return self.fail(f"Problem directory not found: {problem_dir}")

        solutions_dir = Path(self.codebase_path) / "solutions"
        solution_entries = _discover_solutions(solutions_dir, problem_id) if solutions_dir.exists() else []

        # Count sub-problems (variants with evaluator.py)
        total = sum(1 for _ in problem_dir.rglob("evaluator.py"))
        if total == 0:
            total = 1  # Single problem without evaluator discovery

        if not solution_entries:
            return self.score(0.0, feedback=f"No solutions found for {problem_id} (0/{total})")

        scores: dict[str, Score] = {}
        total_score = 0.0
        attempted = 0

        for sub_id, sol_path in sorted(solution_entries):
            score_key = sub_id.replace("/", "_")
            sub_problem_dir = problems_path / sub_id

            if not sub_problem_dir.exists():
                scores[score_key] = Score(value=0.0, name=score_key, explanation="problem dir not found")
                attempted += 1
                continue

            try:
                problem_score, status_str = _evaluate_with_docker(sub_problem_dir, sol_path)
            except Exception as e:
                scores[score_key] = Score(value=0.0, name=score_key, explanation=f"error: {e}")
                attempted += 1
                continue

            scores[score_key] = Score(value=problem_score, name=score_key, explanation=status_str)
            total_score += problem_score
            attempted += 1

        avg_score = total_score / total if total > 0 else 0.0

        return ScoreBundle(
            scores=scores,
            aggregated=avg_score,
            feedback=f"{problem_id}: {attempted}/{total} variants | Average: {avg_score:.4f}",
        )


def _evaluate_with_docker(problem_dir: Path, solution_path: Path) -> tuple[float, str]:
    """Run a solution through the problem's Docker-based evaluator."""
    config_path = problem_dir / "config.yaml"
    if not config_path.exists():
        return 0.0, "no config.yaml"

    with open(config_path) as f:
        config = yaml.safe_load(f)

    docker_image = config.get("docker_image", "frontier-cs-research")
    timeout = config.get("timeout", DEFAULT_TIMEOUT)
    gpu = config.get("gpu", False)

    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir) / "workspace"
        workspace.mkdir()

        for item in problem_dir.iterdir():
            dest = workspace / item.name
            if item.is_dir():
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)

        shutil.copy2(solution_path, workspace / "solution.py")

        cmd = ["docker", "run", "--rm", "-v", f"{workspace}:/workspace", "-w", "/workspace"]
        if gpu:
            cmd.extend(["--gpus", "all"])
        cmd.extend([docker_image, "bash", "evaluate.sh"])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return 0.0, "timeout"

        if result.returncode != 0:
            stderr_tail = result.stderr.strip().split("\n")[-3:]
            return 0.0, f"exit code {result.returncode}: {' '.join(stderr_tail)}"

        score = _parse_score_from_output(result.stdout)
        if score is None:
            return 0.0, "no score in output"
        return score, "ok"


def _parse_score_from_output(stdout: str) -> float | None:
    for line in reversed(stdout.strip().split("\n")):
        line = line.strip()
        try:
            return float(line)
        except ValueError:
            continue
    return None


def _discover_solutions(solutions_dir: Path, problem_id: str) -> list[tuple[str, Path]]:
    """Find solution.py files for the given problem_id."""
    entries = []
    problem_sol_dir = solutions_dir / problem_id
    if not problem_sol_dir.exists():
        return entries

    for sol_file in problem_sol_dir.rglob("solution.py"):
        rel = sol_file.parent.relative_to(solutions_dir)
        entries.append((str(rel), sol_file))

    # If there's a direct solution.py in the problem dir
    direct = problem_sol_dir / "solution.py"
    if direct.exists() and (problem_id, direct) not in entries:
        entries.append((problem_id, direct))

    return entries
