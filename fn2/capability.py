from typing import List
import json

# -------------------------------
# 1. Capability: abstract ability
# -------------------------------
class Capability:
    def __init__(self, name: str, description: str):
        self.name = name            # name of capability, e.g., "Text Generation"
        self.description = description  # description of ability

# -------------------------------
# 2. Action: action category
# -------------------------------
class Action:
    def __init__(self, name: str, capability_name: str, description: str):
        self.name = name             # action name, e.g., "text_generation"
        self.capability_name = capability_name  # which capability it belongs to
        self.description = description

# -------------------------------
# 3. Skill: concrete ability implementation
# -------------------------------
class Skill:
    def __init__(self, name: str, action_name: str, description: str, properties: dict):
        self.name = name             # skill name, e.g., "GPT_text_gen"
        self.action_name = action_name
        self.description = description
        self.properties = properties # dictionary: stability, cost, available, etc.

# -------------------------------
# 4. Extension: tool or platform
# -------------------------------
class Extension:
    def __init__(self, name: str, skill_list: List[str], description: str):
        self.name = name                # tool/platform name, e.g., "OpenAI_API"
        self.skill_list = skill_list    # list of skill names it provides
        self.description = description

def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

capabilities = load_json("capabilities.json")
actions = load_json("actions.json")
skills = load_json("skills.json")
extensions = load_json("extensions.json")
