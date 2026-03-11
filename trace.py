import time
import os
from config import runtime

log_file = None
if runtime["log_to_file"]:
    try:
        log_dir = runtime.get("log_folder", "log")
        os.makedirs(log_dir, exist_ok=True)
        log_file_path = os.path.join(log_dir, "agent.log")
        log_file = open(log_file_path, 'a', encoding='utf-8')
    except Exception as e:
        print(f"failed to open log file: {e}")

class Trace:
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
        import datetime
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

        console_message = f"{time_color_code}[{timestamp}]{reset_code} {component_color_code}{Trace.log_icons.get(level, '✅')}[{component}]{reset_code} {message}"
        file_message = f"[{timestamp}] [{component}] {message}"

        return (console_message, file_message)
    
    @staticmethod
    def log(component: str, message):
        if not runtime["trace"].get(component.lower(), False):
            return

        console_message, file_message = Trace._build_message(component, message)
        if runtime["log_to_file"] and log_file:
            try:
                log_file.write(file_message + '\n')
                log_file.flush()
            except Exception as e:
                pass
        else:
            print(console_message, flush=True)

    @staticmethod
    def error(component: str, message):
        console_message, file_message = Trace._build_message(component, message, level='error')
        if runtime["log_to_file"] and log_file:
            try:
                log_file.write(file_message + '\n')
                log_file.flush()
            except Exception as e:
                pass

        print(console_message, flush=True)
