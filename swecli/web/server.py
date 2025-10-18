"""FastAPI web server for SWE-CLI UI."""

from __future__ import annotations

import asyncio
import webbrowser
from pathlib import Path
from threading import Thread
from typing import Optional

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

from swecli.web.routes import chat_router, sessions_router, config_router
from swecli.web.websocket import websocket_endpoint
from swecli.web.state import init_state
from swecli.core.management import (
    ConfigManager,
    SessionManager,
    ModeManager,
    UndoManager,
)
from swecli.core.approval import ApprovalManager


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI app
    """
    app = FastAPI(
        title="SWE-CLI Web UI",
        description="Web interface for SWE-CLI AI coding assistant",
        version="0.1.0",
    )

    # CORS middleware for development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Vite dev server
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register API routes
    app.include_router(chat_router)
    app.include_router(sessions_router)
    app.include_router(config_router)

    # WebSocket endpoint
    app.add_websocket_route("/ws", websocket_endpoint)

    # Health check
    @app.get("/api/health")
    async def health_check():
        return {"status": "ok", "service": "swecli-web-ui"}

    # Serve static files (frontend build)
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
    else:
        # Development: Return placeholder HTML
        @app.get("/")
        async def root():
            return HTMLResponse("""
<!DOCTYPE html>
<html>
<head>
    <title>SWE-CLI Web UI</title>
    <style>
        body {
            font-family: system-ui, -apple-system, sans-serif;
            max-width: 800px;
            margin: 100px auto;
            padding: 20px;
            background: #0f172a;
            color: #e2e8f0;
        }
        .container {
            background: #1e293b;
            padding: 40px;
            border-radius: 12px;
            border: 1px solid #334155;
        }
        h1 {
            color: #60a5fa;
            margin-bottom: 20px;
        }
        .status {
            background: #1e3a8a;
            color: #93c5fd;
            padding: 12px 20px;
            border-radius: 6px;
            margin: 20px 0;
            border: 1px solid #2563eb;
        }
        .info {
            color: #94a3b8;
            line-height: 1.8;
        }
        code {
            background: #0f172a;
            padding: 2px 8px;
            border-radius: 4px;
            color: #fbbf24;
            font-family: 'Monaco', 'Courier New', monospace;
        }
        a {
            color: #60a5fa;
            text-decoration: none;
        }
        a:hover {
            text-decoration: underline;
        }
        .endpoints {
            margin-top: 30px;
        }
        .endpoint {
            background: #0f172a;
            padding: 10px 15px;
            margin: 8px 0;
            border-radius: 6px;
            border-left: 3px solid #10b981;
        }
        .method {
            color: #10b981;
            font-weight: bold;
            margin-right: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 SWE-CLI Web UI</h1>

        <div class="status">
            ✅ Server is running
        </div>

        <div class="info">
            <p><strong>Status:</strong> Development mode</p>
            <p>The React frontend is not yet built. To develop the UI:</p>
            <ol>
                <li>Navigate to <code>swecli/web-ui/</code></li>
                <li>Run <code>npm install</code></li>
                <li>Run <code>npm run dev</code></li>
                <li>Frontend will be available at <a href="http://localhost:5173">http://localhost:5173</a></li>
            </ol>
        </div>

        <div class="endpoints">
            <h2 style="color: #60a5fa; font-size: 20px;">Available API Endpoints</h2>

            <div class="endpoint">
                <span class="method">GET</span>
                <code>/api/health</code> - Health check
            </div>

            <div class="endpoint">
                <span class="method">GET</span>
                <code>/api/chat/messages</code> - Get chat history
            </div>

            <div class="endpoint">
                <span class="method">POST</span>
                <code>/api/chat/query</code> - Send query to AI
            </div>

            <div class="endpoint">
                <span class="method">GET</span>
                <code>/api/sessions</code> - List all sessions
            </div>

            <div class="endpoint">
                <span class="method">GET</span>
                <code>/api/config</code> - Get configuration
            </div>

            <div class="endpoint">
                <span class="method">GET</span>
                <code>/api/config/providers</code> - List AI providers
            </div>

            <div class="endpoint">
                <span class="method">WS</span>
                <code>/ws</code> - WebSocket for real-time updates
            </div>
        </div>

        <p style="margin-top: 30px; color: #64748b;">
            📚 API Documentation: <a href="/docs">/docs</a>
        </p>
    </div>
</body>
</html>
            """)

    return app


def start_server(
    config_manager: ConfigManager,
    session_manager: SessionManager,
    mode_manager: ModeManager,
    approval_manager: ApprovalManager,
    undo_manager: UndoManager,
    host: str = "127.0.0.1",
    port: int = 8080,
    open_browser: bool = True,
) -> Thread:
    """Start the web server in a background thread.

    Args:
        config_manager: Configuration manager
        session_manager: Session manager
        mode_manager: Mode manager
        approval_manager: Approval manager
        undo_manager: Undo manager
        host: Host to bind to
        port: Port to listen on
        open_browser: Whether to open browser automatically

    Returns:
        Thread running the server
    """
    # Initialize shared state
    init_state(
        config_manager,
        session_manager,
        mode_manager,
        approval_manager,
        undo_manager,
    )

    # Create app
    app = create_app()

    # Open browser after a short delay
    if open_browser:
        def open_browser_delayed():
            import time
            time.sleep(1.5)  # Wait for server to start
            url = f"http://{host}:{port}"
            webbrowser.open(url)

        Thread(target=open_browser_delayed, daemon=True).start()

    # Run server in thread
    def run_server():
        import logging
        import warnings
        import sys

        # Suppress ALL warnings from websockets and runtime
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        warnings.filterwarnings("ignore", category=RuntimeWarning)
        warnings.filterwarnings("ignore", module="websockets")

        # Suppress all uvicorn/websockets logs to avoid polluting terminal
        logging.getLogger("uvicorn").setLevel(logging.CRITICAL)
        logging.getLogger("uvicorn.error").setLevel(logging.CRITICAL)
        logging.getLogger("uvicorn.access").setLevel(logging.CRITICAL)
        logging.getLogger("websockets").setLevel(logging.CRITICAL)
        logging.getLogger("websockets.server").setLevel(logging.CRITICAL)
        logging.getLogger("websockets.legacy.server").setLevel(logging.CRITICAL)

        # Redirect stderr for this thread to suppress any remaining warnings
        import io
        sys.stderr = io.StringIO()  # Capture stderr to suppress warnings

        # Custom log config to disable all non-critical logs
        log_config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(message)s",
                },
            },
            "handlers": {
                "default": {
                    "class": "logging.NullHandler",
                },
            },
            "loggers": {
                "uvicorn": {"handlers": ["default"], "level": "CRITICAL"},
                "uvicorn.error": {"handlers": ["default"], "level": "CRITICAL"},
                "uvicorn.access": {"handlers": ["default"], "level": "CRITICAL"},
            },
        }

        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="critical",
            access_log=False,
            log_config=log_config,
        )

    server_thread = Thread(target=run_server, daemon=True)
    server_thread.start()

    return server_thread
