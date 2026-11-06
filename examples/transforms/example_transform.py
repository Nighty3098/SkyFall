"""Example SkyFall transform plugin.

Copy this file to ``~/.skyfall/transforms/`` and edit it.  SkyFall will load it
automatically and show the transform in the graph context menu.
"""

from src.transforms import ChildNodeDef, TransformDef, TransformResult


def example_handler(value: str, modules: dict) -> TransformResult:
    """Return one custom child node for the selected graph node."""

    # ``modules`` exposes SkyFall's connected modules, for example:
    #     shodan = modules.get("shodan")
    #     settings = modules.get("settings")
    del modules

    return TransformResult(
        children=[
            ChildNodeDef(
                title=f"Result: {value}",
                entity_type="Custom",
                content=f"Custom lookup finished for {value}",
                evidence=["https://example.com/"],
            )
        ],
        content=f"Example transform handled {value}",
    )


TRANSFORMS = [
    TransformDef(
        name="Example: Echo Node",
        description="Show a custom child node for the selected entity",
        input_types=["Domain", "IP", "Email", "Username", "Custom"],
        output_type="Custom",
        relationship="related_to",
        handler=example_handler,
    )
]
