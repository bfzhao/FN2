"""
LLM wrapper for local language model
"""

from openai import OpenAI
from config import llm

class LLMWrapper:
    """
    LLM wrapper for OpenAI API
    """
    client: OpenAI

    def __init__(self):
        self.client = OpenAI(base_url=llm["base_url"], api_key=llm["api_key"])
        self.model = llm["model"]

    def generate(self, prompt: str, question: str,
        max_tokens: int = 1024, temperature: float = 0.7) -> str:
        """
        Generate text from prompt.
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": prompt
                },
                {
                    "role": "user",
                    "content": question
                },
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content
