#!/usr/bin/env python3
"""
FN2 Agent main entry point
"""

import argparse
import asyncio
import os
import sys
import threading
import signal
import datetime
import uvicorn

from fastapi import FastAPI
from config.settings import runtime
from utils.trace import Trace, init_log_file
from utils.daemon import daemonize
from fn2.board import Event
from fn2.fn2_manager import FN2Manager
from fn2.attention_notifier import setup_console_handler, create_attention_handler, create_task_status_handler
from fn2.interactive_mode import InteractiveMode
from fn2.dryrun import DryRun
from services.web_service import setup_web_service


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
                        help='Run as web service (background)')
    parser.add_argument('--web', action='store_true',
                        help='Run as web service (non-daemon)')
    parser.add_argument('--port', type=int,
                        help='Port to run the web service on')
    parser.add_argument('--host', type=str,
                        help='Host to bind the web service to')
    return parser.parse_args()


def setup_runtime_config(args):
    """Setup runtime configuration from arguments."""
    runtime["daemon"] = args.daemon
    runtime["web"] = args.web or args.daemon

    # Set log_to_file based on mode
    # Check if we're in daemon mode (either from args or environment variable)
    is_daemon = args.daemon or os.environ.get('FN2_DAEMON_MODE') == '1'
    if is_daemon:
        runtime["log_to_file"] = True
    elif args.web:
        runtime["log_to_file"] = False

    if args.port is not None:
        runtime["port"] = args.port
    if args.host is not None:
        runtime["host"] = args.host


async def main():
    """Main entry point."""
    Trace.log("Main", f"main() function called, PID: {os.getpid()}")

    # Log runtime config
    Trace.log("Main", f"Runtime config: {runtime}")

    # Setup console attention for interactive mode
    if not runtime.get('web', False):
        Trace.log("Main", "Setting up console handler")
        setup_console_handler()

    # Initialize FN2Manager
    Trace.log("Main", "Initializing FN2Manager")
    fn2_manager = None
    attention_handler = create_attention_handler()
    task_status_handler = create_task_status_handler()

    try:
        # Create DryRun instance if dryrun mode is enabled
        dryrun_instance = None
        if runtime.get("dryrun", False):
            Trace.log("Main", "DryRun mode enabled")
            dryrun_instance = DryRun()

        fn2_manager = FN2Manager(
            escalate=attention_handler,
            dryrun=dryrun_instance
        )

        # Register task status handler for all task events
        board = fn2_manager.get_board()
        board.register_event(Event.TASK_NEW, [task_status_handler])
        board.register_event(Event.TASK_ACCEPTED, [task_status_handler])
        board.register_event(Event.TASK_AMBIGUOUS, [task_status_handler])
        board.register_event(Event.TASK_ANALYZED, [task_status_handler])
        board.register_event(Event.TASK_EXECUTED, [task_status_handler])
        board.register_event(Event.TASK_SYNTHESIZED, [task_status_handler])
        board.register_event(Event.TASK_VERIFIED, [task_status_handler])
        board.register_event(Event.TASK_ESCALATED, [task_status_handler])
        board.register_event(Event.TASK_ACKNOWLEDGED, [task_status_handler])

        # Start Board TaskGroup
        async with fn2_manager.get_board():
            if runtime.get('web', False):
                # Setup web service with fn2_manager
                setup_web_service(app, fn2_manager)
                Trace.log("Main", "Web service setup completed")
                Trace.log("Main", f"App routes: {[route.path for route in app.routes]}")

                # Run uvicorn server
                port = runtime.get('port')
                host = runtime.get('host')

                # Run uvicorn server in a separate thread
                def run_server():
                    # Non-daemon mode: log to console
                    config = uvicorn.Config(
                        app=app,
                        host=host,
                        port=port,
                        log_level="info",
                        access_log=True
                    )

                    server = uvicorn.Server(config)
                    asyncio.run(server.serve())

                # Start the server thread
                server_thread = threading.Thread(target=run_server)
                server_thread.daemon = True  # Set to daemon so it exits when main thread exits
                server_thread.start()

                Trace.log("Main", f"Starting web server on {host}:{port}")
                Trace.log("Main", "Web server started")

                # Keep main thread running with short sleep to allow event loop to process tasks
                # Use a simple loop that can be interrupted by KeyboardInterrupt
                while True:
                    try:
                        await asyncio.sleep(0.1)
                    except KeyboardInterrupt:
                        Trace.log("Main", "Keyboard interrupt received, shutting down...")
                        break
            else:
                Trace.log("Main", "Running in interactive mode")
                interactive = InteractiveMode(fn2_manager)
                await interactive.run()
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

    # Check if we're already in daemon mode
    if os.environ.get('FN2_DAEMON_MODE') == '1':
        # This is the daemon process
        # Set web mode to True in daemon mode
        runtime['web'] = True
        # Set log to file in daemon mode
        runtime['log_to_file'] = True

        # Initialize log file
        init_log_file()

        # Log daemon startup
        Trace.log("Main", "Daemon process initialized, starting main function")
        Trace.log("Main", f"Runtime config in daemon mode: {runtime}")

        # Run main
        try:
            asyncio.run(main())
        except Exception as e:
            Trace.error("Main", f"Daemon startup error: {str(e)}")
            import traceback
            Trace.error("Main", f"Daemon startup traceback: {traceback.format_exc()}")
        finally:
            Trace.log("Main", "Daemon process exiting")
    else:
        # For daemon mode, daemonize the process
        if runtime.get('daemon', False):
            # Set web mode to True in daemon mode
            runtime['web'] = True
            # Set log to file in daemon mode
            runtime['log_to_file'] = True

            print("Starting in daemon mode")
            print("The service will run in the background")

            # Create log directory if it doesn't exist
            project_dir = os.path.dirname(os.path.abspath(__file__))
            log_dir = os.path.join(project_dir, 'log')
            os.makedirs(log_dir, exist_ok=True)

            # Daemonize the process
            daemonize()

            # This code should never be reached in daemon mode
            sys.exit(0)
        else:
            # For non-daemon mode, run normally
            # Initialize log file
            init_log_file()

            # Run main
            try:
                asyncio.run(main())
            except KeyboardInterrupt:
                sys.exit(0)
