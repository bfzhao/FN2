from board import Action, ActionType, ActionResult
from config import llm
import json
import uuid
from typing import Dict, Any, List
from openai import OpenAI
from llm_analyzer_prompt import system_prompt

class LLMAnalyzer:
    """
    LLM analyzer for request analysis
    """

    def __init__(self):
        self.client = OpenAI(base_url=llm["base_url"], api_key=llm["api_key"])
        self.model = llm["model"]

    def _build_prompt(self, request: str) -> str:
        # Build prompt according to new output specification
        return f"""
Request:
{request}


Do not answer the request.
Only generate step by step action to complete the request.
"""

    async def analyze(self, request: str) -> List[Action]:
        prompt = self._build_prompt(request)
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0.2,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        content = response.choices[0].message.content.strip()

        try:
            analysis = json.loads(content)
        except json.JSONDecodeError:
            raise ValueError("Analyzer returned invalid JSON")

        # Generate Action list based on analysis results
        actions = []
        
        # Check if clarification is needed
        clarification = analysis.get("clarification_required", None)
        if clarification:
            question = clarification.get("question", [])
            if question:
                actions.append(Action(
                    type=ActionType.INQUERY,
                    inquery=question
                ))
            else:
                Trace.warn("LLM", "No question in clarification_required")
        else:
            # Generate OPERATION type Action
            sub_tasks = analysis.get("sub_tasks", [])
            if sub_tasks:
                for task in sub_tasks:
                    # Build detailed operation description
                    operation_desc = f"{task.get('purpose', 'None')}: {task.get('description', 'Unknown description')}"
                    # operation_desc += f"\n- 验证方法: {task.get('verification_method', '无')}"
                    
                    actions.append(Action(
                        type=ActionType.OPERATION,
                        request=request,
                        operation=operation_desc
                    ))
            else:
                Trace.warn("LLM", "No sub_tasks in analysis")
        return actions

    def self_check(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform secondary review
        """
        prompt = f"""
Review the following analysis JSON and detect inconsistencies,
missing steps, or under-specified success criteria.

Return corrected JSON only.

{json.dumps(analysis, indent=2)}
"""

        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0.1,
            messages=[
                {"role": "system", "content": "You are a strict analysis auditor."},
                {"role": "user", "content": prompt}
            ]
        )

        content = response.choices[0].message.content.strip()

        try:
            corrected = json.loads(content)
            return corrected
        except:
            return analysis
    
