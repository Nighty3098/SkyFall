"""Documentation shown in ``~/.skyfall/transforms/README.md``."""

PLUGIN_README = """# SkyFall custom transforms

Put trusted Python files in this directory. SkyFall loads every ``*.py`` file
on startup and refreshes the transform list automatically when a file changes.

Only run code you trust: plugins are executed with the same permissions as
SkyFall.

## Minimal plugin

```python
from src.transforms import ChildNodeDef, TransformDef, TransformResult


def my_handler(value, modules):
    # ``value`` is the node title/content selected in the graph.
    # ``modules`` gives access to SkyFall's modules, for example:
    #     shodan = modules.get("shodan_search")
    return TransformResult(
        children=[
            ChildNodeDef(
                title=f"Result for {value}",
                entity_type="Custom",
                content="Explain what was found here.",
                evidence=["https://example.com/source"],
            )
        ],
        content=f"Lookup finished for {value}",
    )


TRANSFORMS = [
    TransformDef(
        name="My Custom Transform",
        description="What this transform does",
        input_types=["Domain", "IP", "Custom"],
        output_type="Custom",
        relationship="related_to",
        handler=my_handler,
    )
]
```

The handler may be synchronous or asynchronous. It must return one of:

- ``TransformResult``;
- a ``ChildNodeDef`` or a list of them;
- a string (shown as content);
- a mapping with ``children`` / ``content`` / ``evidence`` keys;
- ``None`` when there is no result.

Set ``use_content=True`` on the ``TransformDef`` to pass the full node content
instead of the title-derived value. A broken plugin is logged as a warning and
skipped, so other plugins and built-in transforms keep working.

Alternatively, define ``get_transforms()`` and return the list from it:

```python
def get_transforms():
    return [TransformDef(...)]
```

Supported entity types: ``Person``, ``Domain``, ``IP``, ``Email``, ``Phone``,
``MAC``, ``Username``, ``Crypto``, ``Organization``, ``Passport``, ``Photo``,
``Geolocation``, ``URL``, ``ASN``, ``Netblock``, ``Port``, ``Service``,
``Certificate``, ``Hash``, ``SocialMedia``, ``Device``, ``Event``, ``Document``,
``Vehicle``, ``Malware``, ``Nameserver``, ``Phrase`` and ``Custom``.

Use unique transform names. If a plugin uses the same name as a built-in
transform for the same entity type, the built-in one wins and the duplicate is
ignored.
"""
