from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from fn2.fn2_manager import FN2Manager

from api.routes import setup_routes


def setup_web_service(app: FastAPI, fn2_manager: FN2Manager):
    """Setup web service with fn2_manager"""
    # Set fn2_manager in app state
    app.state.fn2_manager = fn2_manager

    # Setup static files
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    web_dir = os.path.join(parent_dir, 'web')
    static_dir = os.path.join(web_dir, 'static')
    index_path = os.path.join(static_dir, 'index.html')

    print(f"Current directory: {current_dir}")
    print(f"Web directory: {web_dir}")
    print(f"Static directory: {static_dir}")
    print(f"Index path: {index_path}")
    print(f"Static directory exists: {os.path.exists(static_dir)}")
    print(f"Index file exists: {os.path.exists(index_path)}")

    # Mount static files
    if os.path.exists(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
        print("Static files mounted successfully")
    else:
        print("Static directory does not exist, skipping mount")

    # Setup routes
    setup_routes(app)

    # Root route
    @app.get("/")
    async def root():
        if os.path.exists(index_path):
            return FileResponse(index_path)
        else:
            return {"message": "FN2 Agent Web Interface"}

    return app
