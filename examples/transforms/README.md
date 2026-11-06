# Custom SkyFall transforms

SkyFall automatically loads Python files from:

```text
~/.skyfall/transforms/
```

You can also override the directory for development:

```bash
export SKYFALL_TRANSFORMS_DIR=/path/to/my/transforms
```

## Quick start

1. Copy `example_transform.py` into `~/.skyfall/transforms/`.
2. Restart SkyFall or wait a couple of seconds — the transform picker reloads
   the directory automatically.
3. Right-click a graph node and pick your transform.

## Plugin contract

A plugin must expose either a `TRANSFORMS` list or a `get_transforms()` function
returning `TransformDef` objects:

```python
from src.transforms import ChildNodeDef, TransformDef, TransformResult


def handler(value, modules):
    del modules
    return TransformResult(
        children=[
            ChildNodeDef(
                title=f"Result for {value}",
                entity_type="Custom",
                content="Extra details go here",
                evidence=["https://example.com/source"],
            )
        ]
    )


TRANSFORMS = [
    TransformDef(
        name="My Transform",
        description="What it does",
        input_types=["Domain", "IP", "Custom"],
        output_type="Custom",
        relationship="related_to",
        handler=handler,
    )
]
```

The handler may be synchronous or asynchronous. It can return a
`TransformResult`, a `ChildNodeDef`, a list of children, a string, or a mapping
with `children` / `content` / `evidence` keys. Set `use_content=True` on a
`TransformDef` to pass the full node content instead of the title-derived
value.

Full field reference, module keys and troubleshooting:
[`DOC.md`](../../DOC.md#custom-graph-transforms).

Only install plugins you trust: plugin code runs with the same permissions as
SkyFall.
