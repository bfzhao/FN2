import os
import sys
import platform
import subprocess
from config.settings import runtime


def daemonize():
    """
    Cross-platform daemonize function.
    Uses subprocess to spawn a detached background process.
    """
    # Check if we're already in daemon mode (to prevent recursive spawning)
    if os.environ.get('FN2_DAEMON_MODE') == '1':
        return

    print(f"Starting daemonization process, PID: {os.getpid()}")

    # Get absolute path of the script
    script_path = os.path.abspath(sys.argv[0])
    
    # Build arguments for the daemon process
    args = [arg for arg in sys.argv[1:] if arg != '--daemon']
    
    # Add --web argument if needed
    if runtime.get('web', False) and '--web' not in args:
        args.append('--web')
    
    # Add port and host arguments from runtime config only if not already in args
    if runtime.get('port') is not None and '--port' not in args:
        args.extend(['--port', str(runtime['port'])])
    if runtime.get('host') is not None and '--host' not in args:
        args.extend(['--host', runtime['host']])

    # Set up environment
    env = os.environ.copy()
    env['FN2_DAEMON_MODE'] = '1'

    # Get the script's directory for cwd
    cwd = os.path.dirname(script_path)
    
    # Create log files for daemon stdout/stderr
    project_dir = os.path.dirname(os.path.abspath(__file__))
    log_dir = os.path.join(project_dir, 'log')
    os.makedirs(log_dir, exist_ok=True)
    stdout_log = os.path.join(log_dir, 'daemon_stdout.log')
    stderr_log = os.path.join(log_dir, 'daemon_stderr.log')

    if platform.system() == 'Windows':
        # Windows: use pythonw.exe if available
        python_exe = sys.executable.replace('python.exe', 'pythonw.exe')
        if not os.path.exists(python_exe):
            python_exe = sys.executable
        
        # Start the daemon process
        with open(stdout_log, 'a') as stdout_f, open(stderr_log, 'a') as stderr_f:
            process = subprocess.Popen(
                [python_exe, script_path] + args,
                env=env,
                cwd=cwd,
                stdout=stdout_f,
                stderr=stderr_f,
                stdin=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
            )
        print(f"Daemon started with PID: {process.pid}")
    else:
        # Unix/Linux/macOS: use double-fork via subprocess with start_new_session
        with open(stdout_log, 'a') as stdout_f, open(stderr_log, 'a') as stderr_f:
            process = subprocess.Popen(
                [sys.executable, script_path] + args,
                env=env,
                cwd=cwd,
                stdout=stdout_f,
                stderr=stderr_f,
                stdin=subprocess.DEVNULL,
                start_new_session=True
            )
        print(f"Daemon started with PID: {process.pid}")
    
    sys.exit(0)
