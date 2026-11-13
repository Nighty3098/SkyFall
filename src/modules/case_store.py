"""Persistent, unified storage for an investigation case.

A case used to be a tree of timestamped Markdown files.  That is convenient for
grepping but cannot answer the questions an analyst actually asks: *which note
belongs to which entity?*, *what exactly did the request look like?*, *which
graph version did we roll back from?*.

This module adds a small SQLite store (``<case>/case.db``) next to the existing
folder layout.  It is deliberately Qt-free so it can be used by tests, MCP
tools and future CLI clients.

Stored data
-----------
* **notes** — title, Markdown body, tags, timestamps;
* **attachments** — screenshots, files and other evidence copied into the
  case, with SHA-256 and size (optionally linked to a note);
* **request logs** — module, target, URL, method, status, duration, headers and
  bodies; the raw request/response is also written to ``logs/requests``;
* **graph versions** — full graph snapshots with content hashes, labels,
  actions and parent ids, supporting history and rollback;
* **activity** — a small audit trail for case-level operations.
"""

from __future__ import annotations

import hashlib
import json
import mimetypes
import re
import sqlite3
import uuid
from collections.abc import Iterable
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_MAX_INLINE = 256_000
DEFAULT_KEEP_VERSIONS = 200


def _utcnow() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str, sort_keys=True)


def _safe_name(value: str, fallback: str = "file") -> str:
    name = Path(str(value or "")).name
    name = re.sub(r"[^\w.\-() ]+", "_", name, flags=re.UNICODE).strip(" ._")
    return name[:120] or fallback


def _clip(value: Any, limit: int = DEFAULT_MAX_INLINE) -> str | None:
    if value is None:
        return None
    text = str(value)
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n… [truncated, {len(text) - limit} chars omitted]"


def _tags(value: Iterable[str] | str | None) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        items = re.split(r"[,;]", value)
    else:
        items = list(value)
    cleaned = []
    for item in items:
        item = str(item).strip()
        if item and item not in cleaned:
            cleaned.append(item)
    return ", ".join(cleaned)


def _tags_list(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _graph_content_hash(snapshot: dict[str, Any]) -> str:
    """Stable hash of what the graph *means*, ignoring node positions.

    Moving cards around should not create a new version, but changing a title,
    an entity type, evidence or an edge must.
    """
    nodes = []
    for node in snapshot.get("nodes", []):
        nodes.append(
            {
                "id": str(node.get("id", "")),
                "title": node.get("title", ""),
                "content": node.get("content", ""),
                "entity_type": node.get("entity_type", ""),
                "evidence": node.get("evidence") or [],
                "metadata": node.get("metadata") or {},
            }
        )
    nodes.sort(key=lambda item: item["id"])
    edges = []
    for edge in snapshot.get("edges", []):
        edges.append(
            {
                "source": str(edge.get("source", "")),
                "target": str(edge.get("target", "")),
                "label": edge.get("label", ""),
                "relationship_type": edge.get("relationship_type", ""),
                "style": edge.get("style", ""),
            }
        )
    edges.sort(key=lambda item: (item["source"], item["target"], item["label"]))
    payload = {"nodes": nodes, "edges": edges}
    return hashlib.sha256(_json(payload).encode("utf-8")).hexdigest()


def _snapshot_hash(snapshot: dict[str, Any]) -> str:
    return hashlib.sha256(_json(snapshot).encode("utf-8")).hexdigest()


_SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS notes (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    body TEXT NOT NULL DEFAULT '',
    tags TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS attachments (
    id TEXT PRIMARY KEY,
    note_id TEXT REFERENCES notes(id) ON DELETE SET NULL,
    kind TEXT NOT NULL,
    path TEXT NOT NULL,
    original_name TEXT NOT NULL,
    caption TEXT NOT NULL DEFAULT '',
    sha256 TEXT NOT NULL,
    size INTEGER NOT NULL,
    mime TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_attachments_note ON attachments(note_id);
CREATE INDEX IF NOT EXISTS idx_attachments_kind ON attachments(kind);

CREATE TABLE IF NOT EXISTS request_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    module TEXT NOT NULL DEFAULT '',
    target TEXT NOT NULL DEFAULT '',
    method TEXT NOT NULL DEFAULT '',
    url TEXT NOT NULL DEFAULT '',
    status_code INTEGER,
    duration_ms REAL,
    request_headers TEXT,
    request_body TEXT,
    response_headers TEXT,
    response_body TEXT,
    error TEXT,
    raw_path TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_requests_module ON request_logs(module);
CREATE INDEX IF NOT EXISTS idx_requests_target ON request_logs(target);
CREATE INDEX IF NOT EXISTS idx_requests_created ON request_logs(created_at);

CREATE TABLE IF NOT EXISTS graph_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    label TEXT NOT NULL DEFAULT '',
    action TEXT NOT NULL DEFAULT 'manual',
    created_at TEXT NOT NULL,
    snapshot TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    snapshot_hash TEXT NOT NULL,
    nodes INTEGER NOT NULL DEFAULT 0,
    edges INTEGER NOT NULL DEFAULT 0,
    parent_id INTEGER,
    note TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_versions_created ON graph_versions(created_at);
CREATE INDEX IF NOT EXISTS idx_versions_hash ON graph_versions(content_hash);

CREATE TABLE IF NOT EXISTS activity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL,
    message TEXT NOT NULL,
    data TEXT,
    created_at TEXT NOT NULL
);
"""


class CaseStore:
    """SQLite-backed store for one case directory."""

    def __init__(self, root: str | Path, max_inline: int = DEFAULT_MAX_INLINE):
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.db_path = self.root / "case.db"
        self.max_inline = max_inline
        self._ensure_dirs()
        self._init_schema()

    # ------------------------------------------------------------------ setup

    def _ensure_dirs(self) -> None:
        for name in (
            "notes",
            "evidence",
            "screenshots",
            "logs",
            "logs/requests",
            "graph",
            "graph/versions",
        ):
            (self.root / name).mkdir(parents=True, exist_ok=True)

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(_SCHEMA)
            conn.execute(
                "INSERT OR IGNORE INTO meta(key, value) VALUES (?, ?)",
                ("created_at", _utcnow()),
            )
            conn.execute(
                "INSERT OR IGNORE INTO meta(key, value) VALUES (?, ?)",
                ("schema_version", "1"),
            )

    # ------------------------------------------------------------------ notes

    def create_note(
        self, title: str, body: str = "", tags: Iterable[str] | str | None = None
    ) -> dict[str, Any]:
        note_id = uuid.uuid4().hex
        now = _utcnow()
        title = str(title or "").strip() or "Untitled note"
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO notes(id, title, body, tags, created_at, updated_at)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (note_id, title, str(body or ""), _tags(tags), now, now),
            )
        self.log_activity(
            "note_created", f"Note created: {title}", {"note_id": note_id}
        )
        return self.get_note(note_id) or {}

    def update_note(
        self,
        note_id: str,
        title: str | None = None,
        body: str | None = None,
        tags: Iterable[str] | str | None = None,
    ) -> dict[str, Any] | None:
        current = self.get_note(note_id)
        if current is None:
            return None
        updates = {
            "title": current["title"]
            if title is None
            else str(title).strip() or "Untitled note",
            "body": current["body"] if body is None else str(body),
            "tags": _tags(current["tags"]) if tags is None else _tags(tags),
            "updated_at": _utcnow(),
        }
        with self._connect() as conn:
            conn.execute(
                "UPDATE notes SET title = ?, body = ?, tags = ?, updated_at = ?"
                " WHERE id = ?",
                (
                    updates["title"],
                    updates["body"],
                    updates["tags"],
                    updates["updated_at"],
                    note_id,
                ),
            )
        return self.get_note(note_id)

    def get_note(self, note_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM notes WHERE id = ?", (note_id,)
            ).fetchone()
        if row is None:
            return None
        note = dict(row)
        note["tags"] = _tags_list(note.get("tags"))
        note["attachments"] = self.list_attachments(note_id=note_id)
        return note

    def list_notes(self, limit: int = 500) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM notes ORDER BY updated_at DESC LIMIT ?", (int(limit),)
            ).fetchall()
        notes = []
        for row in rows:
            note = dict(row)
            note["tags"] = _tags_list(note.get("tags"))
            note["attachment_count"] = self._attachment_count(note["id"])
            notes.append(note)
        return notes

    def delete_note(self, note_id: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        if cur.rowcount:
            self.log_activity(
                "note_deleted", f"Note deleted: {note_id}", {"note_id": note_id}
            )
            return True
        return False

    def _attachment_count(self, note_id: str) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM attachments WHERE note_id = ?", (note_id,)
            ).fetchone()
        return int(row["n"]) if row else 0

    # ------------------------------------------------------------- attachments

    def add_screenshot(
        self,
        data: bytes | bytearray,
        caption: str = "",
        note_id: str | None = None,
        filename: str = "",
    ) -> dict[str, Any]:
        """Save a screenshot captured from a widget into the case."""
        name = _safe_name(
            filename or f"screenshot_{datetime.now():%Y-%m-%d_%H-%M-%S}.png"
        )
        if not Path(name).suffix:
            name += ".png"
        return self._write_attachment(
            data=bytes(data),
            kind="screenshot",
            target_dir=self.root / "screenshots",
            original_name=name,
            caption=caption,
            note_id=note_id,
            mime="image/png",
        )

    def add_attachment(
        self,
        path: str | Path,
        kind: str = "file",
        caption: str = "",
        note_id: str | None = None,
        copy: bool = True,
    ) -> dict[str, Any] | None:
        source = Path(path).expanduser()
        if not source.is_file():
            return None
        target_dir = self.root / ("screenshots" if kind == "screenshot" else "evidence")
        if copy:
            data = source.read_bytes()
            mime = mimetypes.guess_type(source.name)[0] or ""
            return self._write_attachment(
                data=data,
                kind=kind,
                target_dir=target_dir,
                original_name=source.name,
                caption=caption,
                note_id=note_id,
                mime=mime,
            )
        return self.add_attachment_path(
            source, kind=kind, caption=caption, note_id=note_id
        )

    def add_attachment_path(
        self,
        path: str | Path,
        kind: str = "file",
        caption: str = "",
        note_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Register an existing file without copying it into the case."""
        source = Path(path).expanduser().resolve()
        if not source.is_file():
            return None
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        return self._insert_attachment(
            kind=kind,
            path=str(source),
            original_name=source.name,
            caption=caption,
            note_id=note_id,
            sha256=digest,
            size=source.stat().st_size,
            mime=mimetypes.guess_type(source.name)[0] or "",
        )

    def _write_attachment(
        self,
        data: bytes,
        kind: str,
        target_dir: Path,
        original_name: str,
        caption: str,
        note_id: str | None,
        mime: str,
    ) -> dict[str, Any]:
        target_dir.mkdir(parents=True, exist_ok=True)
        name = _safe_name(original_name)
        target = target_dir / name
        if target.exists():
            target = target_dir / f"{target.stem}_{uuid.uuid4().hex[:8]}{target.suffix}"
        target.write_bytes(data)
        digest = hashlib.sha256(data).hexdigest()
        return self._insert_attachment(
            kind=kind,
            path=str(target),
            original_name=original_name,
            caption=caption,
            note_id=note_id,
            sha256=digest,
            size=len(data),
            mime=mime,
        )

    def _insert_attachment(
        self,
        *,
        kind: str,
        path: str,
        original_name: str,
        caption: str,
        note_id: str | None,
        sha256: str,
        size: int,
        mime: str,
    ) -> dict[str, Any]:
        attachment_id = uuid.uuid4().hex
        now = _utcnow()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO attachments(id, note_id, kind, path, original_name,"
                " caption, sha256, size, mime, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    attachment_id,
                    note_id,
                    str(kind),
                    path,
                    original_name,
                    str(caption or ""),
                    sha256,
                    int(size),
                    str(mime or ""),
                    now,
                ),
            )
        self.log_activity(
            "attachment_added",
            f"{kind} added: {original_name}",
            {"attachment_id": attachment_id, "path": path},
        )
        return self.get_attachment(attachment_id) or {}

    def get_attachment(self, attachment_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM attachments WHERE id = ?", (attachment_id,)
            ).fetchone()
        return dict(row) if row else None

    def list_attachments(
        self,
        note_id: str | None = None,
        kind: str | None = None,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        query = "SELECT * FROM attachments"
        clauses: list[str] = []
        params: list[Any] = []
        if note_id is not None:
            clauses.append("note_id = ?")
            params.append(note_id)
        if kind is not None:
            clauses.append("kind = ?")
            params.append(kind)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(int(limit))
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def delete_attachment(self, attachment_id: str, delete_file: bool = False) -> bool:
        attachment = self.get_attachment(attachment_id)
        if attachment is None:
            return False
        with self._connect() as conn:
            conn.execute("DELETE FROM attachments WHERE id = ?", (attachment_id,))
        if delete_file:
            try:
                Path(attachment["path"]).unlink(missing_ok=True)
            except OSError:
                pass
        return True

    # ------------------------------------------------------------- request logs

    def log_request(
        self,
        module: str,
        target: str = "",
        *,
        method: str = "",
        url: str = "",
        status_code: int | None = None,
        duration_ms: float | None = None,
        request_headers: Any = None,
        request_body: Any = None,
        response_headers: Any = None,
        response_body: Any = None,
        error: str = "",
        save_raw: bool = True,
    ) -> dict[str, Any]:
        now = _utcnow()
        raw_path = ""
        if save_raw:
            raw_path = str(
                self._write_raw_request(
                    module=module,
                    target=target,
                    method=method,
                    url=url,
                    status_code=status_code,
                    duration_ms=duration_ms,
                    request_headers=request_headers,
                    request_body=request_body,
                    response_headers=response_headers,
                    response_body=response_body,
                    error=error,
                    created_at=now,
                )
            )
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO request_logs(module, target, method, url, status_code,"
                " duration_ms, request_headers, request_body, response_headers,"
                " response_body, error, raw_path, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    str(module or ""),
                    str(target or ""),
                    str(method or ""),
                    str(url or ""),
                    status_code,
                    duration_ms,
                    _clip(_json(request_headers))
                    if request_headers is not None
                    else None,
                    _clip(request_body, self.max_inline),
                    _clip(_json(response_headers))
                    if response_headers is not None
                    else None,
                    _clip(response_body, self.max_inline),
                    str(error or "") or None,
                    raw_path,
                    now,
                ),
            )
            request_id = int(cur.lastrowid)
        return self.get_request(request_id) or {}

    def log_response(
        self,
        module: str,
        target: str,
        response: Any,
        duration_ms: float | None = None,
    ) -> dict[str, Any]:
        """Convenience adapter for ``requests.Response`` objects."""
        return self.log_request(
            module=module,
            target=target,
            method=getattr(response, "request", None)
            and getattr(response.request, "method", ""),
            url=getattr(response, "url", ""),
            status_code=getattr(response, "status_code", None),
            duration_ms=duration_ms,
            request_headers=getattr(
                getattr(response, "request", None), "headers", None
            ),
            request_body=getattr(getattr(response, "request", None), "body", None),
            response_headers=getattr(response, "headers", None),
            response_body=getattr(response, "text", None),
        )

    def _write_raw_request(self, **fields: Any) -> Path:
        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S_%f")
        module = _safe_name(str(fields.get("module") or "request"), "request")
        path = self.root / "logs" / "requests" / f"{stamp}_{module}.log"
        lines = [
            "SkyFall raw request log",
            f"created_at: {fields.get('created_at')}",
            f"module: {fields.get('module')}",
            f"target: {fields.get('target')}",
            f"method: {fields.get('method')}",
            f"url: {fields.get('url')}",
            f"status_code: {fields.get('status_code')}",
            f"duration_ms: {fields.get('duration_ms')}",
            "",
            "=== request headers ===",
            _pretty(fields.get("request_headers")),
            "",
            "=== request body ===",
            _pretty(fields.get("request_body")),
            "",
            "=== response headers ===",
            _pretty(fields.get("response_headers")),
            "",
            "=== response body ===",
            _pretty(fields.get("response_body")),
            "",
            "=== error ===",
            _pretty(fields.get("error")),
            "",
        ]
        path.write_text("\n".join(lines), encoding="utf-8")
        return path

    def list_requests(
        self, limit: int = 200, module: str | None = None, target: str | None = None
    ) -> list[dict[str, Any]]:
        query = "SELECT * FROM request_logs"
        clauses = []
        params: list[Any] = []
        if module:
            clauses.append("module = ?")
            params.append(module)
        if target:
            clauses.append("target = ?")
            params.append(target)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(int(limit))
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def get_request(self, request_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM request_logs WHERE id = ?", (int(request_id),)
            ).fetchone()
        return dict(row) if row else None

    # -------------------------------------------------------------- graph versions

    def save_graph_version(
        self,
        snapshot: dict[str, Any],
        label: str = "",
        action: str = "manual",
        parent_id: int | None = None,
        note: str = "",
        dedupe: bool = True,
        keep: int = DEFAULT_KEEP_VERSIONS,
    ) -> dict[str, Any]:
        if not isinstance(snapshot, dict):
            raise TypeError("graph snapshot must be a dictionary")
        content_hash = _graph_content_hash(snapshot)
        snapshot_hash = _snapshot_hash(snapshot)
        if dedupe:
            latest = self.latest_graph_version(include_snapshot=False)
            if latest and latest["content_hash"] == content_hash:
                return {**latest, "created": False}
        nodes = len(snapshot.get("nodes") or [])
        edges = len(snapshot.get("edges") or [])
        now = _utcnow()
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO graph_versions(label, action, created_at, snapshot,"
                " content_hash, snapshot_hash, nodes, edges, parent_id, note)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    str(label or ""),
                    str(action or "manual"),
                    now,
                    _json(snapshot),
                    content_hash,
                    snapshot_hash,
                    nodes,
                    edges,
                    parent_id,
                    str(note or ""),
                ),
            )
            version_id = int(cur.lastrowid)
        self.prune_graph_versions(keep=keep)
        self.log_activity(
            "graph_version",
            f"Graph version saved: {label or action}",
            {"version_id": version_id, "nodes": nodes, "edges": edges},
        )
        version = self.get_graph_version(version_id)
        return {**(version or {}), "created": True}

    def list_graph_versions(
        self, limit: int = 100, include_snapshot: bool = False
    ) -> list[dict[str, Any]]:
        columns = (
            "*"
            if include_snapshot
            else (
                "id, label, action, created_at, content_hash, snapshot_hash,"
                " nodes, edges, parent_id, note"
            )
        )
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT {columns} FROM graph_versions ORDER BY id DESC LIMIT ?",
                (int(limit),),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_graph_version(self, version_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM graph_versions WHERE id = ?", (int(version_id),)
            ).fetchone()
        if row is None:
            return None
        version = dict(row)
        try:
            version["snapshot"] = json.loads(version["snapshot"])
        except (TypeError, json.JSONDecodeError):
            version["snapshot"] = {"nodes": [], "edges": []}
        return version

    def latest_graph_version(
        self, include_snapshot: bool = False
    ) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id FROM graph_versions ORDER BY id DESC LIMIT 1"
            ).fetchone()
        if row is None:
            return None
        version = self.get_graph_version(int(row["id"]))
        if version is None:
            return None
        if not include_snapshot:
            version.pop("snapshot", None)
        return version

    def delete_graph_version(self, version_id: int) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                "DELETE FROM graph_versions WHERE id = ?", (int(version_id),)
            )
        return bool(cur.rowcount)

    def prune_graph_versions(self, keep: int = DEFAULT_KEEP_VERSIONS) -> int:
        keep = max(1, int(keep))
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id FROM graph_versions ORDER BY id DESC LIMIT 1 OFFSET ?",
                (keep,),
            ).fetchone()
            if row is None:
                return 0
            cutoff = int(row["id"])
            cur = conn.execute("DELETE FROM graph_versions WHERE id <= ?", (cutoff,))
        return int(cur.rowcount)

    # ----------------------------------------------------------------- activity

    def log_activity(
        self, kind: str, message: str, data: dict[str, Any] | None = None
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO activity(kind, message, data, created_at)"
                " VALUES (?, ?, ?, ?)",
                (str(kind), str(message), _json(data) if data else None, _utcnow()),
            )

    def list_activity(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM activity ORDER BY id DESC LIMIT ?", (int(limit),)
            ).fetchall()
        return [dict(row) for row in rows]

    # ------------------------------------------------------------------- search

    def search(self, query: str, limit: int = 100) -> dict[str, list[dict[str, Any]]]:
        term = f"%{str(query or '').strip()}%"
        with self._connect() as conn:
            notes = [
                dict(row)
                for row in conn.execute(
                    "SELECT * FROM notes WHERE title LIKE ? OR body LIKE ?"
                    " OR tags LIKE ? ORDER BY updated_at DESC LIMIT ?",
                    (term, term, term, int(limit)),
                ).fetchall()
            ]
            requests = [
                dict(row)
                for row in conn.execute(
                    "SELECT * FROM request_logs WHERE module LIKE ? OR target LIKE ?"
                    " OR url LIKE ? OR response_body LIKE ?"
                    " ORDER BY id DESC LIMIT ?",
                    (term, term, term, term, int(limit)),
                ).fetchall()
            ]
            attachments = [
                dict(row)
                for row in conn.execute(
                    "SELECT * FROM attachments WHERE original_name LIKE ?"
                    " OR caption LIKE ? OR sha256 LIKE ?"
                    " ORDER BY created_at DESC LIMIT ?",
                    (term, term, term, int(limit)),
                ).fetchall()
            ]
        for note in notes:
            note["tags"] = _tags_list(note.get("tags"))
        return {"notes": notes, "requests": requests, "attachments": attachments}

    # -------------------------------------------------------------------- stats

    def stats(self) -> dict[str, Any]:
        with self._connect() as conn:

            def count(table: str) -> int:
                row = conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()
                return int(row["n"]) if row else 0

            return {
                "root": str(self.root),
                "db": str(self.db_path),
                "notes": count("notes"),
                "attachments": count("attachments"),
                "screenshots": len(
                    self.list_attachments(kind="screenshot", limit=100000)
                ),
                "requests": count("request_logs"),
                "graph_versions": count("graph_versions"),
                "activity": count("activity"),
            }

    # ------------------------------------------------------------------- export

    def export_note(
        self, note_id: str, directory: str | Path | None = None
    ) -> str | None:
        note = self.get_note(note_id)
        if note is None:
            return None
        target_dir = Path(directory) if directory else self.root / "notes"
        target_dir.mkdir(parents=True, exist_ok=True)
        safe_title = _safe_name(note["title"], "note")[:80]
        path = target_dir / f"{note['id'][:8]}_{safe_title}.md"
        lines = [f"# {note['title']}", ""]
        if note.get("tags"):
            lines.append("Tags: " + ", ".join(note["tags"]))
            lines.append("")
        lines.append(note.get("body") or "")
        for attachment in note.get("attachments") or []:
            lines.append("")
            caption = attachment.get("caption") or attachment.get("original_name")
            lines.append(f"![{caption}]({attachment.get('path')})")
        path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        return str(path)

    def close(self) -> None:
        """Compatibility no-op: connections are scoped per operation."""


def _pretty(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, indent=2, default=str)
    return str(value)


__all__ = ["CaseStore", "DEFAULT_KEEP_VERSIONS", "DEFAULT_MAX_INLINE"]
