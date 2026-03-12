"""
LLM synthesizer for FN2 framework
"""

import json
from typing import List
from trace import Trace
from board import TaskResult, Action
from llm_synthesizer_prompt import SYNTHESIZER_PROMPT
from llm_wrapper import LLMWrapper

class LLMSynthesizer:
    """
    Synthesizer is responsible for synthesizing the execution results into final result conclusion.
    """
    def __init__(self):
        self.llm_wrapper = LLMWrapper()

    def _build_prompt(self, actions: List[Action]) -> str:
        execution_results = []
        for i, action in enumerate(actions):
            execution_results.append({
                "action_index": i,
                "operation": action.operation,
                "success": action.result.success if action.result else False,
                "result": action.result.result if action.result else ""
            })

        return f"""
Execute the operation plan and synthesize the results.

Execution Results:
{json.dumps(execution_results, indent=2)}

Please analyze the execution results and provide a final synthesis.

Return JSON in this format:

{{
  "final_result": "",
  "success": false,
  "uncertainty": 0.0,
  "summary": ""
}}

Do not add explanation.
Only JSON.
"""

    async def synthesize(self, actions: List[Action]) -> TaskResult:
        """
        Synthesize the execution results into a final task result.
        """
        prompt = self._build_prompt(actions)
        content = self.llm_wrapper.generate(
            temperature=0.2,
            prompt=SYNTHESIZER_PROMPT,
            question=prompt
        )

        try:
            result = json.loads(content)
        except json.JSONDecodeError:
            Trace.error("LLM", f"LLMSynthesizer synthesize failed, content={content}")
            return TaskResult(
                success=False,
                uncertainty=1.0,
                result="Synthesizer returned invalid JSON"
            )

        success = result.get("success", False)
        uncertainty = result.get("uncertainty", 0.0)
        final_result = result.get("final_result", "")

        return TaskResult(
            success=success,
            uncertainty=uncertainty,
            result=final_result
        )
