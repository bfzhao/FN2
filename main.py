#!/usr/bin/env python3
"""
FN2 Agent main entry point
"""

import argparse
import asyncio
import os
import platform
import subprocess
import sys

from fastapi import FastAPI

from config.settings import runtime
from utils.trace import Trace, init_log_file
from fn2.fn2_manager import FN2Manager
from fn2.attention_notifier import get_notifier, setup_console_handler, setup_web_handler, create_attention_handler
from services.web_service import setup_web_service
from utils.daemon import daemonize


# Global FastAPI app instance
app = FastAPI(
    title="FN2 Agent API",
    description="FN2 Agent Web API",
    version="1.0.0"
)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='FN2 Agent')
    parser.add_argument('--daemon', action='store_true',
                        help='Run in daemon mode (background)')
    parser.add_argument('--web', action='store_true',
                        help='Run as web service (non-daemon)')
    return parser.parse_args()


def setup_runtime_config(args):
    """Setup runtime configuration from arguments."""
    runtime["daemon"] = args.daemon
    # In daemon mode, always set web to True
    runtime["web"] = args.web or args.daemon


async def main():
    """Main entry point."""
    Trace.log("Main", f"main() function called, PID: {os.getpid()}")

    # Log runtime config
    Trace.log("Main", f"Runtime config: {runtime}")

    # Setup attention handler based on mode
    Trace.log("Main", "Setting up attention handler")
    attention_handler = create_attention_handler()
    if runtime.get('daemon', False):
        Trace.log("Main", "Setting up web handler")
        setup_web_handler()
    else:
        Trace.log("Main", "Setting up console handler")
        setup_console_handler()

    # Initialize FN2Manager
    Trace.log("Main", "Initializing FN2Manager")
    fn2_manager = None
    try:
        # Create DryRun instance if dryrun mode is enabled
        dryrun_instance = None
        if runtime.get("dryrun", False):
            from fn2.dryrun import DryRun
            dryrun_instance = DryRun()

        fn2_manager = FN2Manager(
            escalate=attention_handler,
            dryrun=dryrun_instance
        )
        Trace.log("Main", "FN2Manager initialized")
        # Start Board TaskGroup
        Trace.log("Main", "Starting Board TaskGroup")
        await fn2_manager.get_board().__aenter__()
        Trace.log("Main", "Board TaskGroup started")
    except Exception as e:
        Trace.log("Main", f"Error initializing FN2Manager: {str(e)}")
        # Continue even if FN2Manager initialization fails
        # We'll just have a non-functional service, but at least it will start
        Trace.log("Main", "Continuing with service startup despite FN2Manager initialization failure")

    # Setup web service only if web or daemon mode is enabled
    if runtime.get('daemon', False) or runtime.get('web', False):
        Trace.log("Main", "Setting up web service")
        try:
            # Setup web service with fn2_manager
            setup_web_service(app, fn2_manager)
            Trace.log("Main", "Web service setup completed")
            Trace.log("Main", f"App routes: {[route.path for route in app.routes]}")
        except Exception as e:
            Trace.log("Main", f"Error setting up web service: {str(e)}")
    else:
        Trace.log("Main", "Skipping web service setup (not in web/daemon mode)")

    Trace.log("Main", "Starting service")
    try:
        if runtime.get('daemon', False) or runtime.get('web', False):
            # Daemon mode: run web service with uvicorn
            Trace.log("Main", "FN2 Agent started in daemon mode")
            Trace.log("Main", "Starting web server with uvicorn")

            # Run uvicorn server
            # Use port 8021 for both web and daemon modes
            port = 8021

            # For daemon mode, redirect uvicorn logs to a file
            log_file = None
            if runtime.get('daemon', False):
                log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'log', 'uvicorn.log')
                Trace.log("Main", f"Redirecting uvicorn logs to: {log_file}")

            # Run uvicorn server in a separate thread
            import threading
            def run_server():
                import uvicorn
                config = uvicorn.Config(
                    app=app,
                    host="0.0.0.0",
                    port=port,
                    log_level="info"
                )
                server = uvicorn.Server(config)
                import asyncio
                asyncio.run(server.serve())

            # Start the server thread
            server_thread = threading.Thread(target=run_server)
            server_thread.daemon = True
            server_thread.start()

            Trace.log("Main", f"Starting web server on port {port}")
            Trace.log("Main", f"Web mode: {runtime.get('web', False)}")
            Trace.log("Main", f"Daemon mode: {runtime.get('daemon', False)}")
            Trace.log("Main", "Web server started in background thread")

            # Keep the main thread running
            while True:
                await asyncio.sleep(3600)
        else:
            # Interactive mode: run console interface
            Trace.log("Main", "Starting interactive mode")
            if fn2_manager:
                from fn2.interactive_mode import InteractiveMode
                interactive = InteractiveMode(fn2_manager)
                await interactive.run()
            else:
                Trace.log("Main", "Cannot start interactive mode: FN2Manager is not initialized")
    except (KeyboardInterrupt, asyncio.CancelledError):
        Trace.log("Main", "Break to exit...")
    except Exception as e:
        Trace.log("Main", f"Error starting service: {str(e)}")
        Trace.log("Main", f"Unexpected error: {str(e)}")
    finally:
        Trace.log("Main", "safe exited")


if __name__ == "__main__":
    # Parse arguments
    args = parse_args()

    # Setup runtime config
    setup_runtime_config(args)

    # Initialize log file before daemonize
    init_log_file()

    # For daemon mode, we'll run the service directly without forking
    # This ensures that FastAPI app and routes are properly initialized
    if runtime.get('daemon', False):
        # Set web mode to True in daemon mode
        runtime['web'] = True
        # Set daemon mode environment variable
        os.environ['FN2_DAEMON_MODE'] = '1'
        print("Starting in daemon mode")

    # Run main
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
