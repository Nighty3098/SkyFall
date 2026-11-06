"""Graph transform controller.

The controller only handles graph interaction.  Built-in transforms live in
``src.transforms.builtin``; user transforms are discovered from
``~/.skyfall/transforms`` (or ``SKYFALL_TRANSFORMS_DIR``) by the transform
registry.
"""

from __future__ import annotations

import asyncio
import inspect

from PySide6.QtCore import QPointF

from src.modules.graph_layout import child_arc_positions
from src.transforms import (
    ChildNodeDef,
    TransformDef,
    TransformRegistry,
    TransformResult,
    coerce_transform_result,
)
from src.transforms.builtin import build_builtin_registry
from src.transforms.builtin_handlers import *  # noqa: F403
from src.transforms.helpers import _transform_input
from src.transforms.loader import PluginLoader

_DEFAULT_PLUGIN_DIR = object()


class GraphTransformController:
    def __init__(self, graph_widget, modules, plugin_dir=_DEFAULT_PLUGIN_DIR):
        self._graph = graph_widget
        self._modules = modules
        if plugin_dir is None:
            loader = None
        elif plugin_dir is _DEFAULT_PLUGIN_DIR:
            loader = PluginLoader()
        else:
            loader = PluginLoader(plugin_dir)
        self._registry = TransformRegistry(build_builtin_registry(), loader)

    @property
    def plugin_loader(self):
        return self._registry.plugin_loader

    def reload_plugins(self) -> None:
        """Force a reload of custom transforms from disk."""

        self._registry.reload_plugins()

    def get_transforms(self, node):
        if node is None:
            return []
        return self._registry.get_transforms(node.entity_type)

    def _notify(self, message):
        graph = self._graph
        if graph is not None and hasattr(graph, "status_message"):
            graph.status_message(message)

    def execute(self, node, transform_def):
        if node is None or transform_def is None:
            return
        self._notify(f"Running {transform_def.name}\u2026")
        self._active_tasks = getattr(self, "_active_tasks", set())
        task = asyncio.ensure_future(self._execute_async(node, transform_def))
        self._active_tasks.add(task)
        task.add_done_callback(self._active_tasks.discard)

    def execute_many(self, nodes, transform_def):
        """Run one transform against several nodes as a single undo step."""
        nodes = [node for node in (nodes or []) if node is not None]
        if not nodes or transform_def is None:
            return
        self._active_tasks = getattr(self, "_active_tasks", set())
        task = asyncio.ensure_future(self._execute_many_async(nodes, transform_def))
        self._active_tasks.add(task)
        task.add_done_callback(self._active_tasks.discard)

    async def _execute_many_async(self, nodes, transform_def):
        graph = self._graph
        self._notify(f"Running {transform_def.name} on {len(nodes)} nodes\u2026")
        begin = getattr(graph, "begin_bulk_edit", None)
        end = getattr(graph, "end_bulk_edit", None)
        if callable(begin):
            begin()
        total = 0
        created = []
        try:
            for node in nodes:
                node_transform = next(
                    (
                        candidate
                        for candidate in self.get_transforms(node)
                        if candidate.name == transform_def.name
                    ),
                    transform_def,
                )
                total += await self._execute_async(
                    node, node_transform, report=False, created=created
                )
        finally:
            if callable(end):
                end()
        if created:
            scene = graph.scene() if callable(getattr(graph, "scene", None)) else None
            if scene is not None:
                scene.clearSelection()
            for child in created:
                try:
                    visible = child.scene() is not None
                except RuntimeError:
                    visible = False
                if visible:
                    child.setSelected(True)
        self._notify(
            f"{transform_def.name}: {total} result"
            f"{'s' if total != 1 else ''} from {len(nodes)} node"
            f"{'s' if len(nodes) != 1 else ''}"
        )

    async def _execute_async(self, node, transform_def, report=True, created=None):
        scene = getattr(node, "scene", None)
        if callable(scene) and scene() is None:
            return 0
        title = (node.title or "").strip()
        content = (node.content or "").strip()
        etype = node.entity_type
        default_prefix = f"New {etype}"

        input_value = _transform_input(node, etype, title, content, default_prefix)
        if transform_def.use_content and content:
            input_value = content
        if not input_value:
            if report:
                self._notify(f"{transform_def.name}: no usable input value")
            return 0

        try:
            if not callable(transform_def.handler):
                result = TransformResult(
                    content=f"{transform_def.name} failed: no handler configured"
                )
            else:
                raw_result = transform_def.handler(input_value, self._modules)
                if inspect.isawaitable(raw_result):
                    raw_result = await raw_result
                result = coerce_transform_result(raw_result)
        except Exception as exc:  # noqa: BLE001 - report failures in the graph
            result = TransformResult(content=f"{transform_def.name} failed: {exc}")
        if callable(scene) and scene() is None:
            return 0

        children = list(result.children)
        if not children and result.content:
            children.append(
                ChildNodeDef(
                    title=result.content.split("\n")[0][:60],
                    entity_type=transform_def.output_type or "Custom",
                    content=result.content,
                    evidence=list(result.evidence),
                )
            )
        if not children:
            if report:
                self._notify(f"{transform_def.name}: no results")
            return 0

        graph = self._graph
        if graph is None:
            return 0
        begin = getattr(graph, "begin_bulk_edit", None)
        end = getattr(graph, "end_bulk_edit", None)
        if callable(begin):
            begin()
        child_nodes = []
        try:
            for cd in children:
                pos = node.pos() + QPointF(
                    220 + len(child_nodes) * 80,
                    -40 * len(children) + len(child_nodes) * 80,
                )
                child = graph.add_node(pos, cd.entity_type)
                child.title = cd.title
                child.content = cd.content
                child.evidence = cd.evidence
                child.update()
                child_nodes.append(child)

                graph.add_edge(node, child, source_port="right", target_port="left")
                if transform_def.relationship:
                    for edge in child._edges:
                        if edge.target == child or edge.source == child:
                            edge.relationship_type = transform_def.relationship
                            edge.update()

            if child_nodes:
                self._layout_children(node, child_nodes)
        finally:
            if callable(end):
                end()

        if created is not None:
            created.extend(child_nodes)
        scene_obj = getattr(graph, "scene", None)
        if callable(scene_obj):
            scene = scene_obj()
            if scene is not None:
                scene.clearSelection()
        for child in child_nodes:
            child.setSelected(True)
        if report:
            self._notify(
                f"{transform_def.name}: {len(child_nodes)} result"
                f"{'s' if len(child_nodes) != 1 else ''}"
            )
        return len(child_nodes)

    def _layout_children(self, parent, children):
        count = len(children)
        if count == 0:
            return

        positions = child_arc_positions(
            parent.pos(),
            count,
            parent_size=(parent._width, parent._height),
            child_size=(children[0]._width, children[0]._height),
            arc_deg=min(130 + count * 3, 270),
        )
        for child, (x, y) in zip(children, positions):
            child.setPos(x, y)

    def get_all_types(self):
        return self._registry.get_all_types()


__all__ = [
    "ChildNodeDef",
    "GraphTransformController",
    "TransformDef",
    "TransformResult",
]
