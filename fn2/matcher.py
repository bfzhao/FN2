"""
Matcher 
"""
import json
import subprocess
import os
import re
from utils.trace import Trace
from typing import Dict, Any, List, Tuple
from fn2.llm_wrapper import LLMWrapper
from fn2.matcher_prompt import MATCHER_PROMPT
from fn2.matcher_verify_prompt import VERIFY_PROMPT
from fn2.board import Action

SKILLS_DIR = "skills"
MAX_ITERATIONS = 3
ERROR_THRESHOLD = 0.15

def load_skills(skills_dir: str = None) -> Dict[str, Dict]:
    if skills_dir is None:
        skills_dir = SKILLS_DIR

    skills = {}
    if not os.path.exists(skills_dir):
        return skills

    for skill_name in os.listdir(skills_dir):
        skill_path = os.path.join(skills_dir, skill_name)
        if os.path.isdir(skill_path):
            skill_file = os.path.join(skill_path, "SKILL.md")
            if os.path.exists(skill_file):
                try:
                    with open(skill_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # Simple frontmatter parsing
                        if content.startswith('---'):
                            parts = content.split('---', 2)
                            if len(parts) >= 3:
                                frontmatter = parts[1].strip()
                                body = parts[2].strip()
                                # Extract name and description
                                name = ""
                                description = ""
                                commands = []
                                for line in frontmatter.split('\n'):
                                    if line.startswith('name:'):
                                        name = line.split(':', 1)[1].strip().strip('"')
                                    elif line.startswith('description:'):
                                        description = line.split(':', 1)[1].strip().strip('"')
                                    elif line.startswith('commands:'):
                                        # Parse command list
                                        cmd_str = line.split(':', 1)[1].strip()
                                        if cmd_str.startswith('[') and cmd_str.endswith(']'):
                                            # JSON format
                                            commands = json.loads(cmd_str)
                                        elif cmd_str:
                                            # Comma-separated
                                            commands = [c.strip().strip('"') for c in cmd_str.split(',')]
                                if name:
                                    skills[name] = {
                                        "name": name,
                                        "description": description,
                                        "content": body,
                                        "commands": commands
                                    }
                except Exception as e:
                    print(f"Failed to load skill {skill_name}: {e}")

    return skills

def calculator(expression: str) -> float:
    """Simple calculator tool"""
    try:
        return eval(expression, {"__builtins__": {}})  # Secure limited eval
    except Exception as e:
        return f"Calculation error: {str(e)}"

def shell_exec(command: str) -> str:
    """Execute shell commands (with safety protection)"""
    dangerous_patterns = [
        "rm -rf", "rm -r", "rm -f", "rmdir",
        "mkfs", "dd if=", "dd of=",
        "chmod", "chown",
        "useradd", "userdel", "passwd",
        "apt-get", "yum", "dnf", "pacman",
        "sudo", "su ",
        "systemctl", "service ",
        "curl | sh", "wget | sh",
        "eval ", "exec ",
        "> /", ">> /", ">", ">>",
        ":(){:|:&};:", "fork bomb"
    ]

    command_lower = command.lower().strip()

    for pattern in dangerous_patterns:
        if pattern.lower() in command_lower:
            return f"❌ Command execution rejected: {command}\nReason: Contains dangerous operation '{pattern}'"

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            check=False,
            timeout=30
        )
        output = []
        if result.stdout:
            output.append(f"Standard output:\n{result.stdout}")
        if result.stderr:
            output.append(f"Standard error:\n{result.stderr}")
        output.append(f"Exit code: {result.returncode}")
        return "\n".join(output)
    except subprocess.TimeoutExpired:
        return "Command execution timed out (>30s)"
    except Exception as e:
        return f"Execution error: {str(e)}"

SKILLS = load_skills()

TOOLS = {
    "calculator": {
        "function": calculator,
        "description": "Execute mathematical expressions, e.g., '2 + 3 * 4'",
        "parameters": {"expression": "str"}
    },
    "shell_exec": {
        "function": shell_exec,
        "description": "Execute shell commands, e.g., 'ls -la', 'pwd', 'uname -a'",
        "parameters": {"command": "str"}
    }
}

def call_tool(tool_name: str, params: Dict) -> Any:
    """Call tool"""
    if tool_name in TOOLS:
        func = TOOLS[tool_name]["function"]
        return func(**params)
    return f"Unknown tool: {tool_name}"

def execute_tool_call(tool_call: Dict) -> str:
    """Execute single tool call"""
    tool_name = tool_call.get("tool")
    params = tool_call.get("params", {})
    result = call_tool(tool_name, params)
    return f"{tool_name}({params}) → {result}"

def execute_skill_command(command: str, params: Dict = None) -> str:
    """Execute single skill command"""
    if params:
        for key, value in params.items():
            command = command.replace(f"<{key}>", str(value))

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            check=False,
            timeout=30
        )
        output = f"Command: {command}\n"
        if result.stdout:
            output += f"Output:\n{result.stdout}"
        if result.stderr:
            output += f"Error:\n{result.stderr}"
        output += f"Exit code: {result.returncode}"
        return output
    except subprocess.TimeoutExpired:
        return f"Command '{command}' timed out"
    except Exception as e:
        return f"Command '{command}' failed: {str(e)}"

def execute_skill_call(skill_call: Dict) -> List[str]:
    """Execute single skill call"""
    skill_name = skill_call.get("skill")
    params = skill_call.get("params", {})

    if skill_name not in SKILLS:
        return [f"Unknown skill: {skill_name}"]

    skill_info = SKILLS[skill_name]
    skill_commands = skill_info.get("commands", [])

    if not skill_commands:
        return [f"Skill '{skill_name}' has no predefined commands"]

    results = []
    for cmd in skill_commands:
        result = execute_skill_command(cmd, params)
        results.append(result)

    return results

class Matcher:
    def __init__(self, step: Action):
        self.llm_wrapper = LLMWrapper()
        self.state = {"history": []}
        self.goal = step.operation
        self.plan = None
        self.try_count = 0

    def run(self):
        Trace.log("Matcher", f"Start matching plan, goal: {self.goal}, try_count: {self.try_count}")
        while self.try_count < MAX_ITERATIONS:
            success, final_answer = self._run()
            if success:
                return success, final_answer

            self.try_count += 1
            # Don't assign the return value of match() to self.plan
            # match() already sets self.plan when successful
            self.match()

        Trace.log("Matcher", f"Failed to match plan after {MAX_ITERATIONS} attempts")
        return False, None

    def _run(self):
        print(self.plan)
        tool_results, skill_results = self._execute_plan(self.plan)
        results = tool_results.copy()
        if skill_results:
            results.append("Skill execution results:\n" + "\n---\n".join(skill_results))

        entry = {
            "thought": self.plan.get("thought", ""),
            "actions": self.plan.get("tool_calls", []),
            "results": results,
            # "error": self.error_score
        }
        self.state["history"].append(json.dumps(entry, ensure_ascii=False))

        if self.plan.get("final_answer"):
            if skill_results or results:
                print("Skill/tool execution results:")
                for r in skill_results:
                    print(f"  {r[:200]}...")
                for r in results:
                    if not any(sr.startswith("Skill") for sr in skill_results):
                        print(f"  {r[:200]}...")
                Trace.log("Matcher", f"Final answer: {self.plan["final_answer"]}")

                # Update observation with real execution results
                real_results_str = "\n".join(skill_results + results)
                updated_error = self._validate_final_answer(real_results_str, self.plan["final_answer"])
                Trace.log("Matcher", f"Error score based on real results: {updated_error:.3f}")

                if updated_error <= ERROR_THRESHOLD:
                    Trace.log("Matcher", "Converged! Task completed.")
                    return True, self.plan["final_answer"]
                else:
                    Trace.log("Matcher", "Final answer inconsistent with real results, continuing to optimize...")
            else:
                Trace.log("Matcher", "Warning: Attempting to return final answer without executing any tools or skills")
        else:
            Trace.log("Matcher:", json.dumps(self.plan, indent=2, ensure_ascii=False))

        return False, None

    def match(self, feedback: str = "") -> Dict:
        available_tools = "\n".join([
            f"- {name}: {info['description']}"
            for name, info in TOOLS.items()
        ])

        available_skills = "\n".join([
            f"- {name}: {info['description']}"
            for name, info in SKILLS.items()
        ])

        observation = f"{feedback}\n".join(self.state["history"][-5:])
        prompt = MATCHER_PROMPT.format(
            available_tools=available_tools,
            available_skills=available_skills,
            observation=observation
        )

        content = self.llm_wrapper.generate(
            prompt=prompt,
            question=self.goal,
            temperature=0.3
        )

        json_str = content.strip()
        if json_str.startswith("```json"):
            json_str = json_str[7:-3].strip()

        print(json_str)
        try:
            # Check if JSON string is complete
            if json_str.count('{') != json_str.count('}'):
                print("JSON string is incomplete - missing closing braces")
                # Try to fix by adding missing braces
                open_braces = json_str.count('{')
                close_braces = json_str.count('}')
                if open_braces > close_braces:
                    json_str += '}' * (open_braces - close_braces)
                    print("Fixed JSON string:", json_str)

            plan = json.loads(json_str)
            answer = plan.get("conclusion", {}).get("answer", "").lower()
            print(f"Extracted answer: '{answer}'")
            if answer in ["是", "yes"]:
                self.plan = plan
                return True
            else:
                return False
        except Exception as e:
            print(f"parse plan error: {e}, json_str: {json_str}")
            return False

    def _validate_final_answer(self, observation: str, final_answer: str) -> float:
        prompt = VERIFY_PROMPT.format(
            goal=self.plan,
            observation=observation,
            final_answer=final_answer
        )

        score_text = self.llm_wrapper.generate(
            prompt="",
            question=prompt,
            temperature=0.1,
            max_tokens=4096
        )
        try:
            match = re.search(r'\d+\.\d+', score_text)
            if match:
                score = float(match.group())
            else:
                Trace.log("Matcher", f"not expect float score: {score_text}")
                score = float(score_text)
            return max(0.0, min(1.0, score))
        except Exception as e:
            Trace.error("Matcher", f"execute verify prompt error, return 0.9 always: {e}")
            return 0.9

    def _execute_plan(self, plan: Dict) -> Tuple[List[str], List[str]]:
        tool_results = []
        skill_results = []

        for cmd in plan.get("tool_calls", []):
            result = execute_tool_call(cmd)
            tool_results.append(result)

        for cmd in plan.get("skill_calls", []):
            results = execute_skill_call(cmd)
            skill_results.extend(results)

        return tool_results, skill_results
