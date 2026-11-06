"""Tests for user transform plugins and the modular transform registry."""

import asyncio
import os
import tempfile
import textwrap
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from src.controllers.graph_transform_controller import (  # noqa: E402
    GraphTransformController,
)
from src.libs.graph_lib import EdgeItem, GraphWidget, NodeItem  # noqa: E402
from src.transforms import (  # noqa: E402
    ChildNodeDef,
    PluginLoader,
    coerce_transform_result,
    ensure_plugin_dir,
)

_app = QApplication.instance() or QApplication([])


def _write_plugin(directory: Path, name: str, source: str) -> Path:
    path = directory / name
    path.write_text(textwrap.dedent(source), encoding="utf-8")
    return path


PLUGIN_SOURCE = """
from src.transforms import ChildNodeDef, TransformDef, TransformResult


def echo(value, modules):
    del modules
    return TransformResult(
        children=[
            ChildNodeDef(
                title=f"Echo {value}",
                entity_type="Custom",
                content="plugin result",
            )
        ]
    )


TRANSFORMS = [
    TransformDef(
        name="Echo Plugin",
        description="Plugin test transform",
        input_types=["Domain"],
        output_type="Custom",
        relationship="related_to",
        handler=echo,
    )
]
"""


class PluginDiscoveryTest(unittest.TestCase):
    def test_plugin_is_loaded_and_listed_for_its_entity_type(self):
        with tempfile.TemporaryDirectory() as directory:
            _write_plugin(Path(directory), "echo_plugin.py", PLUGIN_SOURCE)
            controller = GraphTransformController(None, {}, plugin_dir=directory)

            node = type("Node", (), {"entity_type": "Domain"})()
            names = [transform.name for transform in controller.get_transforms(node)]

            self.assertIn("Echo Plugin", names)
            self.assertEqual(controller.plugin_loader.errors, [])

    def test_get_transforms_function_is_supported(self):
        source = """
        from src.transforms import ChildNodeDef, TransformDef, TransformResult


        def handler(value, modules):
            del modules
            return TransformResult(children=[ChildNodeDef(title=value)])


        def get_transforms():
            return [
                TransformDef(
                    name="Factory Plugin",
                    input_types=["IP"],
                    handler=handler,
                )
            ]
        """
        with tempfile.TemporaryDirectory() as directory:
            _write_plugin(Path(directory), "factory_plugin.py", source)
            controller = GraphTransformController(None, {}, plugin_dir=directory)
            node = type("Node", (), {"entity_type": "IP"})()
            names = [transform.name for transform in controller.get_transforms(node)]
            self.assertIn("Factory Plugin", names)

    def test_broken_plugin_does_not_break_builtins(self):
        with tempfile.TemporaryDirectory() as directory:
            _write_plugin(
                Path(directory),
                "broken_plugin.py",
                "raise RuntimeError('broken plugin')\n",
            )
            controller = GraphTransformController(None, {}, plugin_dir=directory)
            node = type("Node", (), {"entity_type": "IP"})()
            names = [transform.name for transform in controller.get_transforms(node)]

            self.assertIn("Shodan Host", names)
            self.assertEqual(len(controller.plugin_loader.errors), 1)
            self.assertIn("broken plugin", controller.plugin_loader.errors[0])

    def test_plugin_directory_is_created_with_readme(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "nested" / "transforms"
            ensure_plugin_dir(target)
            self.assertTrue(target.is_dir())
            self.assertTrue((target / "README.md").is_file())

    def test_loader_reloads_when_a_plugin_is_added(self):
        with tempfile.TemporaryDirectory() as directory:
            _write_plugin(Path(directory), "echo_plugin.py", PLUGIN_SOURCE)
            loader = PluginLoader(directory, check_interval=0)
            self.assertEqual([item.name for item in loader.transforms], ["Echo Plugin"])

            _write_plugin(
                Path(directory),
                "second_plugin.py",
                PLUGIN_SOURCE.replace("Echo Plugin", "Second Plugin"),
            )
            self.assertTrue(loader.refresh_if_changed())
            self.assertEqual(
                [item.name for item in loader.transforms],
                ["Echo Plugin", "Second Plugin"],
            )


class PluginExecutionTest(unittest.TestCase):
    def setUp(self):
        self.gw = GraphWidget()
        self.gw._status_timer.stop()

    def test_sync_plugin_handler_creates_graph_nodes(self):
        with tempfile.TemporaryDirectory() as directory:
            _write_plugin(Path(directory), "echo_plugin.py", PLUGIN_SOURCE)
            controller = GraphTransformController(self.gw, {}, plugin_dir=directory)
            node = self.gw.add_node(QPointF(10, 20), "Domain")
            node.title = "example.com"
            node.update()
            transform = next(
                item
                for item in controller.get_transforms(node)
                if item.name == "Echo Plugin"
            )
            self.gw._undo_stack.clear()

            count = asyncio.run(controller._execute_async(node, transform))

            self.assertEqual(count, 1)
            self.assertEqual(len(self.gw._undo_stack), 1)
            nodes = [
                item for item in self.gw._scene.items() if isinstance(item, NodeItem)
            ]
            edges = [
                item for item in self.gw._scene.items() if isinstance(item, EdgeItem)
            ]
            self.assertEqual(len(nodes), 2)
            self.assertEqual(len(edges), 1)
            self.assertIn("Echo example.com", {item.title for item in nodes})

    def test_async_plugin_handler_is_awaited(self):
        source = """
        from src.transforms import ChildNodeDef, TransformDef, TransformResult


        async def handler(value, modules):
            del modules
            return TransformResult(children=[ChildNodeDef(title=f"Async {value}")])


        TRANSFORMS = [
            TransformDef(
                name="Async Plugin",
                input_types=["Domain"],
                handler=handler,
            )
        ]
        """
        with tempfile.TemporaryDirectory() as directory:
            _write_plugin(Path(directory), "async_plugin.py", source)
            controller = GraphTransformController(self.gw, {}, plugin_dir=directory)
            node = self.gw.add_node(QPointF(10, 20), "Domain")
            node.title = "example.com"
            node.update()
            transform = next(
                item
                for item in controller.get_transforms(node)
                if item.name == "Async Plugin"
            )

            count = asyncio.run(controller._execute_async(node, transform))
            self.assertEqual(count, 1)


class ResultCoercionTest(unittest.TestCase):
    def test_mapping_and_string_results_are_supported(self):
        mapping = coerce_transform_result(
            {"children": [{"title": "Child"}], "content": "done"}
        )
        self.assertEqual(mapping.children[0].title, "Child")
        self.assertEqual(mapping.content, "done")

        text = coerce_transform_result("plain text")
        self.assertEqual(text.content, "plain text")

        children = coerce_transform_result([ChildNodeDef(title="Child")])
        self.assertEqual(children.children[0].title, "Child")


if __name__ == "__main__":
    unittest.main()
