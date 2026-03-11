import json
from typing import List
from openai import OpenAI
from config import llm
from board import TaskResult, Action

class LLMSynthesizer:
    def __init__(self):
        self.client = OpenAI(base_url=llm["base_url"], api_key=llm["api_key"])
        self.model = llm["model"]

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
        prompt = self._build_prompt(actions)
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0.2,
            messages=[
                {
                    "role": "system",
                    "content": "You are a Synthesizer in a negative feedback architecture. Your role is to synthesize execution results into a final task result."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        content = response.choices[0].message.content.strip()

        try:
            result = json.loads(content)
        except json.JSONDecodeError:
            # TODO: should retry for format error
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
