"""
Configuration.
"""

llm = {
    "base_url": "http://172.29.80.1:11434/v1",
    "api_key": "ollama",
    "model": "qwen3:4b-q4_K_M"
}

nfn = {
    "max_iterations": 3,
    "uncertainty_threshold": 0.15
}

skills = {
    "directory": "skills"
}

runtime = {
    "dryrun": True,
    "success": 0.8,
    "trace": {
        "main": True,
        "task": True,
        "controller": True,
        "board": False,
        "analyzer": True,
        "executor": True,
        "synthesizer": True,
        "llm": True,
        "dryrun": True,
        "matcher": True,
        "web": True,
    },
    "log_folder": "log",
    "log_to_file": True,
    "auto_fail_system_escalation": True,
    "auto_retry_tasks": False,
    "daemon": False
}
