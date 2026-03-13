"""
Trace log support.
"""

import os
import datetime
from config import runtime

LOG_FILE = None
if runtime["log_to_file"]:
    log_dir = runtime.get("log_folder", "log")
    os.makedirs(log_dir, exist_ok=True)
    log_file_path = os.path.join(log_dir, "agent.log")
    LOG_FILE = open(log_file_path, 'a', encoding='utf-8')

class Trace:
    """
    Trace class was used to log message to console or log file.
    """
    _COLORS = {
        'reset': '\033[0m',
        'red': '\033[31m',
        'green': '\033[32m',
        'yellow': '\033[33m',
        'blue': '\033[34m',
        'magenta': '\033[35m',
        'cyan': '\033[36m',
        'white': '\033[37m'
    }

    @staticmethod
    def _format_timestamp():
        return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

    _COMPONENT_COLORS = {
        'Task': 'cyan',
        'Board': 'blue',
        'Controller': 'green',
        'Analyzer': 'yellow',
        'Executor': 'magenta',
        'Synthesizer': 'red',
        'LLM': 'green',
        'Main': 'white',
        'DryRun': 'white'
    }

    log_icons = {
        'info': '✅',
        'warning': '⚠️',
        'error': '❌',
    }

    @staticmethod
    def _build_message(component: str, message: str, level: str = 'info') -> (str, str):
        component_color = Trace._COMPONENT_COLORS.get(component, 'white')
        component_color_code = Trace._COLORS.get(component_color, Trace._COLORS['white'])
        time_color_code = Trace._COLORS['yellow']
        reset_code = Trace._COLORS['reset']
        timestamp = Trace._format_timestamp()

        icon = Trace.log_icons.get(level, '✅')
        console_message = (
            f"{time_color_code}[{timestamp}]{reset_code} "
            f"{component_color_code}{icon}[{component}]{reset_code} {message}"
        )
        file_message = f"[{timestamp}] [{component}] {message}"

        return (console_message, file_message)

    @staticmethod
    def _log(component: str, message: str, level: str):
        if not runtime["trace"].get(component.lower(), False):
            return

        console_message, file_message = Trace._build_message(component, message, level)
        if runtime["log_to_file"] and LOG_FILE:
            LOG_FILE.write(file_message + '\n')
            LOG_FILE.flush()
        else:
            print(console_message, flush=True)

    @staticmethod
    def log(component: str, message):
        """
        Log info message.
        """
        Trace._log(component, message, level='info')

    @staticmethod
    def warn(component: str, message):
        """
        Log warning message.
        """
        Trace._log(component, message, level='warning')

    @staticmethod
    def error(component: str, message):
        """
        Log error message.
        """
        Trace._log(component, message, level='error')
