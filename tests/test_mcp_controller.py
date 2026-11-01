import subprocess
import unittest
from unittest import mock

from src.mcp_controller import McpController


class _GraphBridge:
    def __init__(self):
        self.started = 0
        self.stopped = 0

    def start(self, *args):
        self.started += 1

    def stop(self):
        self.stopped += 1


class _Process:
    def __init__(self, returncode=None):
        self.returncode = returncode
        self.terminated = False

    def poll(self):
        return self.returncode

    def terminate(self):
        self.terminated = True
        self.returncode = 0

    def wait(self, timeout=None):
        return self.returncode


class McpControllerTest(unittest.TestCase):
    def setUp(self):
        self.controller = McpController(ui=object())
        self.bridge = _GraphBridge()
        self.controller._graph_bridge = self.bridge
        self.controller._graph_widget = object()
        self.controller._node_item_cls = object

    def test_popen_failure_rolls_back_bridge(self):
        with (
            mock.patch("src.mcp_controller.get_or_create_token", return_value="token"),
            mock.patch(
                "src.mcp_controller.subprocess.Popen", side_effect=OSError("failed")
            ),
        ):
            self.controller.start()

        self.assertIsNone(self.controller._process)
        self.assertEqual(self.bridge.started, 1)
        self.assertEqual(self.bridge.stopped, 1)

    def test_immediate_child_exit_stops_bridge(self):
        process = _Process(returncode=1)
        with (
            mock.patch("src.mcp_controller.get_or_create_token", return_value="token"),
            mock.patch("src.mcp_controller.subprocess.Popen", return_value=process),
            mock.patch("src.mcp_controller.QTimer.singleShot"),
        ):
            self.controller.start()
            self.controller._check_started()

        self.assertIsNone(self.controller._process)
        self.assertEqual(self.bridge.started, 1)
        self.assertEqual(self.bridge.stopped, 1)

    def test_child_output_is_not_left_in_undrained_pipes(self):
        process = _Process()
        with (
            mock.patch("src.mcp_controller.get_or_create_token", return_value="token"),
            mock.patch(
                "src.mcp_controller.subprocess.Popen", return_value=process
            ) as popen,
            mock.patch("src.mcp_controller.QTimer.singleShot"),
        ):
            self.controller.start()

        self.assertIs(popen.call_args.kwargs["stdout"], subprocess.DEVNULL)
        self.assertIs(popen.call_args.kwargs["stderr"], subprocess.DEVNULL)
        self.controller.stop()
        self.assertTrue(process.terminated)
        self.assertGreaterEqual(self.bridge.stopped, 1)


if __name__ == "__main__":
    unittest.main()
