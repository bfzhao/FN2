VERIFY_PROMPT = """You are a strict verifier.
Goal: {goal}

Current observation (including real execution results): {observation}

Final answer: {final_answer}

Please verify whether the final answer is generated based on real execution results (0.0~1.0 floating point number, output only the number):
- 0.0 = Completely based on real results, answer is accurate
- 0.1-0.3 = Based on real results, with minor deviations
- 0.4-0.6 = Partially based on real results, with obvious deviations
- 0.7-0.9 = Basically not based on real results, mainly fabricated
- 1.0 = Completely not based on real results, completely fabricated

Output only one floating point number, for example 0.42
"""