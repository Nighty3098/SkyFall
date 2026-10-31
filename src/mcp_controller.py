import os
import subprocess
import sys
from pathlib import Path

import httpx
from loguru import logger
from PySide6.QtCore import QTimer

from src.security import TOKEN_ENV, get_or_create_token


class McpController:
    def __init__(self, ui):
        self.ui = ui
        self._process: subprocess.Popen | None = None
        self._host = "127.0.0.1"
        self._port = 9877
        self._graph_bridge = None

        self._update_ui_status()

    def set_graph_bridge(self, graph_widget, node_item_cls):
        from src.graph_bridge import GraphBridgeServer

        self._graph_bridge = GraphBridgeServer()
        self._graph_widget = graph_widget
        self._node_item_cls = node_item_cls

    @property
    def url(self) -> str:
        return f"http://{self._host}:{self._port}"

    @property
    def is_running(self) -> bool:
        if self._process is None:
            return False
        return self._process.poll() is None

    def start(self):
        if self.is_running:
            logger.warning("MCP server already running")
            return

        token = get_or_create_token()

        if self._graph_bridge and self._graph_widget:
            self._graph_bridge.start(self._graph_widget, self._node_item_cls, token)

        project_root = Path(__file__).parent.parent
        server_script = str(Path(__file__).parent / "skyfall_mcp_server.py")
        cmd = [
            sys.executable,
            server_script,
            "--transport",
            "sse",
            "--host",
            self._host,
            "--port",
            str(self._port),
        ]

        env = os.environ.copy()
        env[TOKEN_ENV] = token

        logger.info(f"Starting SkyFall MCP Server on {self.url}")
        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(project_root),
                env=env,
            )
        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}")
            self._update_ui_status()
            return

        QTimer.singleShot(1500, self._check_started)

    def _check_started(self):
        if not self.is_running:
            stderr = ""
            if self._process and self._process.stderr:
                stderr = self._process.stderr.read().decode(errors="replace")[:500]
            logger.error(f"MCP server exited immediately. stderr: {stderr}")
            self._update_ui_status()
            return

        try:
            with httpx.Client(timeout=3) as client:
                resp = client.get(f"{self.url}/sse")
                # 401 is expected when "Require MCP Auth" is enabled.
                if resp.status_code in (200, 401, 405, 406):
                    logger.success(f"MCP server running at {self.url}")
                else:
                    logger.warning(f"MCP server responded with {resp.status_code}")
        except httpx.ConnectError:
            logger.error("MCP server not responding")
            self.stop()
            return
        except Exception as e:
            logger.debug(f"MCP server check: {e}")

        self._update_ui_status()

    def stop(self):
        if self._process is None:
            self._update_ui_status()
            return

        logger.info("Stopping SkyFall MCP Server")
        try:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait(timeout=3)
        except Exception as e:
            logger.error(f"Error stopping MCP server: {e}")
        finally:
            self._process = None
            if self._graph_bridge:
                self._graph_bridge.stop()
            self._update_ui_status()

    def toggle(self):
        if self.is_running:
            self.stop()
        else:
            self.start()

    def _update_ui_status(self):
        running = self.is_running
        label = getattr(self.ui, "mcpStatusLabel", None)
        btn = getattr(self.ui, "mcpToggleButton", None)

        if label:
            if running:
                label.setText(f"Running at {self.url}")
            else:
                label.setText("Stopped")

        if btn:
            btn.setText("Stop MCP Server" if running else "Start MCP Server")

    def cleanup(self):
        self.stop()
