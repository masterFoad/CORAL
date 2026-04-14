"""LLM-based grader using LiteLLM."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from litellm import completion

from coral.grader.task_grader import TaskGrader
from coral.types import ScoreBundle

logger = logging.getLogger(__name__)


class LLMGrader(TaskGrader):
    """Grader that uses LiteLLM to evaluate a submission based on a rubric.

    Reads an artifact file from the codebase, formats a prompt with a rubric,
    and asks an LLM for a JSON response containing a score and feedback.
    """

    def evaluate(self) -> float | ScoreBundle:
        """Evaluate the submission using an LLM."""
        artifact_path_str = self.args.get("artifact_path")
        if not artifact_path_str:
            return self.fail(explanation="LLMGrader requires 'artifact_path' in args")

        artifact_file = Path(self.codebase_path) / artifact_path_str
        if not artifact_file.exists():
            return self.fail(explanation=f"Artifact file not found: {artifact_path_str}")

        try:
            content = artifact_file.read_text()
        except Exception as e:
            return self.fail(explanation=f"Failed to read artifact: {e}")

        rubric = self.args.get(
            "rubric", "Evaluate the following content and assign a score between 0.0 and 1.0."
        )
        model = self.args.get("model", "gpt-4o")

        system_prompt = (
            "You are an expert grader. Evaluate the provided submission against the rubric.\n"
            "You MUST output your response in JSON format exactly as follows:\n"
            "{\n"
            '  "score": <float between 0.0 and 1.0>,\n'
            '  "feedback": "<string with detailed feedback>"\n'
            "}"
        )

        user_prompt = f"Rubric:\n{rubric}\n\nSubmission Content:\n{content}"

        try:
            response = completion(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
            )

            result_str = response.choices[0].message.content
            if not result_str:
                return self.fail(explanation="LLM returned empty response")

            result_json = json.loads(result_str)

            # Extract score safely
            score_val = result_json.get("score")
            if score_val is None:
                return self.fail(explanation="LLM response did not contain a 'score' field")
            score = float(score_val)

            # Extract feedback
            feedback = str(result_json.get("feedback", ""))

            return self.bundle(value=score, explanation="LLM Graded", feedback=feedback)

        except Exception as e:
            logger.exception("LLM grading failed")
            return self.fail(explanation=f"LLM grading failed: {e}")
