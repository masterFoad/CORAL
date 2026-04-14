"""Grader system for CORAL."""

from coral.grader.base import BaseGrader
from coral.grader.task_grader import TaskGrader
from coral.grader.builtin.agent_grader import AgentGrader
from coral.grader.builtin.llm_grader import LLMGrader
from coral.grader.builtin.function_grader import FunctionGrader, function_grader
from coral.grader.protocol import GraderInterface

__all__ = [
    "AgentGrader",
    "BaseGrader",
    "FunctionGrader",
    "GraderInterface",
    "LLMGrader",
    "TaskGrader",
    "function_grader",
]
