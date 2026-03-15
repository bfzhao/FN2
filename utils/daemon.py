import os
import sys
import platform
import subprocess
from config.settings import runtime


def daemonize():
    """
    Cross-platform daemonize function.
    Works on Unix/Linux/macOS using fork(), and Windows using subprocess.
    """
    # Check if we're already in daemon mode (to prevent recursive spawning)
    if os.environ.get('FN2_DAEMON_MODE') == '1':
        print("Already in daemon mode, returning")
        return

    print(f"Starting daemonization process, PID: {os.getpid()}")

    # For Unix/Linux/macOS, use fork()
    if platform.system() != 'Windows':
        # First fork
        try:
            pid = os.fork()
            if pid > 0:
                # Parent process
                print(f"Daemon started with PID: {pid}")
                sys.exit(0)
        except OSError as e:
            print(f"First fork failed: {e}")
            sys.exit(1)

        # Decouple from parent environment
        os.setsid()
        os.chdir('/')
        os.umask(0)

        # Second fork
        try:
            pid = os.fork()
            if pid > 0:
                # First child process
                sys.exit(0)
        except OSError as e:
            print(f"Second fork failed: {e}")
            sys.exit(1)

        # Redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()

        # Close all standard file descriptors
        si = open(os.devnull, 'r')
        so = open(os.devnull, 'a+')
        se = open(os.devnull, 'a+')

        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())

        # Set daemon mode environment variable
        os.environ['FN2_DAEMON_MODE'] = '1'

        print("Daemonization completed successfully")
        # The daemon process continues to run from here
        return
    else:
        # For Windows, use subprocess
        script_path = sys.argv[0]
        args = [arg for arg in sys.argv[1:] if arg != '--daemon']
        # Add --web argument if needed
        if runtime.get('web', False) and '--web' not in args:
            args.append('--web')

        env = os.environ.copy()
        env['FN2_DAEMON_MODE'] = '1'

        # Use pythonw.exe if available to avoid console window
        python_exe = sys.executable.replace('python.exe', 'pythonw.exe')
        if not os.path.exists(python_exe):
            python_exe = sys.executable

        # Set cwd to the script's directory to ensure relative paths work correctly
        cwd = os.path.dirname(os.path.abspath(script_path))

        # Start the daemon process
        process = subprocess.Popen(
            [python_exe, script_path] + args,
            env=env,
            cwd=cwd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
        )

        print(f"Daemon started with PID: {process.pid}")
        sys.exit(0)
