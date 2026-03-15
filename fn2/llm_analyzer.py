"""
An LLM analyzer implementation.
"""

import json
from typing import List
from utils.trace import Trace
from fn2.board import Action, ActionType
from fn2.llm_analyzer_prompt import ANALYSIS_PROMPT
from fn2.llm_wrapper import LLMWrapper

class LLMAnalyzer:
    """
    LLM analyzer for request analysis
    """

    def __init__(self):
        self.llm_wrapper = LLMWrapper()

    async def analyze(self, request: str) -> List[Action]:
        """
        Analyze the request and return a list of actions.
        """
        content = self.llm_wrapper.generate(
            temperature=0.2,
            prompt=ANALYSIS_PROMPT,
            question=request
        )
        print(content)

        try:
            analysis = json.loads(content)
        except json.JSONDecodeError:
            Trace.error("LLM", "Analyzer returned invalid JSON")

        # Generate Action list based on analysis results
        actions = []

        # Check if clarification is needed
        clarification = analysis.get("clarification_required", {})
        question = clarification.get("question", [])
        if question:
            actions.append(Action(
                type=ActionType.INQUERY,
                inquery=question
            ))
        else:
            sub_tasks = analysis.get("sub_tasks", [])
            if sub_tasks:
                for task in sub_tasks:
                    purpose = task.get('purpose')
                    description = task.get('description')
                    if purpose is None or description is None:
                        Trace.warn("LLM", f"purpose or description is None for task: {task}")
                        continue
                    actions.append(Action(
                        type=ActionType.OPERATION,
                        request=request,
                        operation="purpose: " + purpose + "\n" + "description: " + description
                    ))
            else:
                Trace.warn("LLM", "No sub_tasks in analysis")
        return actions
