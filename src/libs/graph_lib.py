import json
import math
import os
import re
import sys
import urllib.parse
import uuid

import networkx as nx
from PySide6.QtCore import QLineF, QPointF, QRectF, Qt, QUrl, Signal
from PySide6.QtGui import (
    QAction,
    QActionGroup,
    QBrush,
    QColor,
    QDesktopServices,
    QFont,
    QImage,
    QPainter,
    QPainterPath,
    QPainterPathStroker,
    QPen,
    QPixmap,
    QTextOption,
)
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QColorDialog,
    QComboBox,
    QDialog,
    QDockWidget,
    QFileDialog,
    QFormLayout,
    QGraphicsItem,
    QGraphicsPathItem,
    QGraphicsScene,
    QGraphicsView,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMenu,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

ENTITY_TYPES = [
    ("Person", "#4ecdc4", "\U0001f464"),
    ("Domain", "#45b7d1", "\U0001f310"),
    ("IP", "#f9ca24", "\U0001f4e1"),
    ("Email", "#6c5ce7", "\u2709\ufe0f"),
    ("Phone", "#fd79a8", "\U0001f4f1"),
    ("MAC", "#d35400", "\U0001f50c"),
    ("Username", "#00b894", "@"),
    ("Crypto", "#f39c12", "\u20bf"),
    ("Organization", "#e17055", "\U0001f3e2"),
    ("Passport", "#e84393", "\U0001f4c4"),
    ("Photo", "#a29bfe", "\U0001f5bc\ufe0f"),
    ("Geolocation", "#55efc4", "\U0001f4cd"),
    ("Custom", "#636e72", "\u2699\ufe0f"),
]

ENTITY_NAMES = [e[0] for e in ENTITY_TYPES]
ENTITY_COLORS = {e[0]: e[1] for e in ENTITY_TYPES}
ENTITY_SYMBOLS = {e[0]: e[2] for e in ENTITY_TYPES}

PORT_DIR = {
    "left": (-1, 0),
    "right": (1, 0),
    "top": (0, -1),
    "bottom": (0, 1),
}

RELATIONSHIP_TYPES = [
    "owns",
    "registered_at",
    "resolved_to",
    "member_of",
    "located_at",
    "communicates_with",
    "associated_with",
    "works_at",
    "created_by",
    "attends",
    "hosted_by",
    "linked_to",
]

EDGE_STYLES = {
    "normal": {"label": "Normal", "width": 3, "pen_style": Qt.PenStyle.SolidLine},
    "dashed": {"label": "Dashed", "width": 3, "pen_style": Qt.PenStyle.DashLine},
    "bold": {"label": "Bold", "width": 6, "pen_style": Qt.PenStyle.SolidLine},
}


def build_edge_path(src, tgt, sdir, tdir):
    path = QPainterPath()
    path.moveTo(src)
    dist = QLineF(src, tgt).length()
    if dist <= 0:
        path.lineTo(tgt)
        return path

    straight = min(24.0, dist * 0.3)
    bend = min(max(dist * 0.25, 16.0), 80.0)
    bend = min(bend, max((dist - 2 * straight) * 0.5, 4.0))

    p1 = QPointF(src.x() + sdir.x() * straight, src.y() + sdir.y() * straight)
    p2 = QPointF(tgt.x() + tdir.x() * straight, tgt.y() + tdir.y() * straight)
    c1 = QPointF(p1.x() + sdir.x() * bend, p1.y() + sdir.y() * bend)
    c2 = QPointF(p2.x() + tdir.x() * bend, p2.y() + tdir.y() * bend)

    path.lineTo(p1)
    path.cubicTo(c1, c2, p2)
    path.lineTo(tgt)
    return path


def _theme_colors(dark=None):
    from src.ui.theme import current_theme, get_palette

    if dark is None:
        palette = get_palette(current_theme())
    else:
        palette = get_palette("dark" if dark else "light")
    return {
        "card_bg": QColor(palette["surface"]),
        "card_border": QColor(palette["border"]),
        "card_title": QColor(palette["text"]),
        "card_content": QColor(palette["text_muted"]),
        "port_color": QColor(palette["text"]),
        "edge_color": QColor(palette["border"]),
    }


def _contrast_color(bg: QColor) -> QColor:
    lum = (bg.red() * 0.299 + bg.green() * 0.587 + bg.blue() * 0.114) / 255.0
    return QColor("#1a1a1a") if lum > 0.5 else QColor("#f5f5f5")


def _center_dialog(dialog):
    screen = QApplication.primaryScreen()
    if not screen:
        return
    sg = screen.availableGeometry()
    dialog.adjustSize()
    dialog.move(
        sg.center().x() - dialog.width() // 2,
        sg.center().y() - dialog.height() // 2,
    )


IMAGE_EXTS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".webp",
    ".tif",
    ".tiff",
    ".ico",
    ".avif",
    ".svg",
}

_MISSING = object()

_HTTP: QNetworkAccessManager | None = None
_REMOTE_CACHE: dict[str, QPixmap | None] = {}
_REMOTE_PENDING: set[str] = set()


def _is_image_path(path: str) -> bool:
    return os.path.splitext(path)[1].lower() in IMAGE_EXTS


def _http_manager() -> QNetworkAccessManager:
    global _HTTP
    if _HTTP is None:
        _HTTP = QNetworkAccessManager()
    return _HTTP


def _load_remote_pixmap(url: str, node: "NodeItem") -> QPixmap | None:
    cached = _REMOTE_CACHE.get(url, _MISSING)
    if cached is not _MISSING:
        return cached
    if url in _REMOTE_PENDING:
        return None
    _REMOTE_PENDING.add(url)
    request = QNetworkRequest(QUrl(url))
    request.setTransferTimeout(15000)
    request.setHeader(
        QNetworkRequest.KnownHeaders.UserAgentHeader,
        "Mozilla/5.0 (X11; Linux x86_64) SkyFall/1.0",
    )
    reply = _http_manager().get(request)
    reply.finished.connect(lambda r=reply: _on_remote_reply(r, url, node))
    return None


def _on_remote_reply(reply, url: str, node: "NodeItem"):
    _REMOTE_PENDING.discard(url)
    try:
        data = bytes(reply.readAll())
        pix = QPixmap()
        if data:
            pix.loadFromData(data)
        _REMOTE_CACHE[url] = pix if not pix.isNull() else None
    finally:
        reply.deleteLater()
    try:
        node.update()
    except RuntimeError:
        pass


MAP_ZOOM = 13
MAP_ZOOM_MIN = 5
MAP_ZOOM_MAX = 18
MAP_MAX_GRID = 6
_MAP_CACHE: dict[tuple, QPixmap | None] = {}
_MAP_PENDING: dict[tuple, list] = {}


def _map_key(lat: float, lon: float, grid: int, zoom: int = MAP_ZOOM) -> tuple:
    return (round(lat, 5), round(lon, 5), zoom, grid)


def _map_grid_for_size(node: "NodeItem", scale: float) -> int:
    w = (node._width - 20) * scale
    h = (node._get_height() - 32 - 6) * scale
    grid = math.ceil(max(w, h) * 1.15 / 256.0)
    return max(2, min(grid, MAP_MAX_GRID))


def _map_zoom_target(node: "NodeItem", scene_pos) -> "NodeItem | None":
    if node.entity_type != "Geolocation" or _resolve_coordinates(node) is None:
        return None
    local = node.mapFromScene(scene_pos)
    w, h = node._width, node._get_height()
    map_rect = QRectF(10, 32, w - 20, h - 38)
    return node if map_rect.contains(local) else None


def _parse_coord(text: str) -> float | None:
    try:
        return float(text.strip().rstrip("\u00b0"))
    except ValueError:
        return None


def _node_coordinates(node: "NodeItem") -> tuple[float, float] | None:
    match = re.fullmatch(
        r"\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*", node.title or ""
    )
    if match:
        lat, lon = float(match.group(1)), float(match.group(2))
        if -90 <= lat <= 90 and -180 <= lon <= 180:
            return lat, lon
    lat = lon = None
    for line in (node.content or "").splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip().lower()
            if key == "latitude":
                lat = _parse_coord(value)
            elif key == "longitude":
                lon = _parse_coord(value)
    if lat is not None and lon is not None and -90 <= lat <= 90 and -180 <= lon <= 180:
        return lat, lon
    return None


def _world_pixel(lat: float, lon: float, zoom: int) -> tuple[float, float]:
    n = 2**zoom
    lat_rad = math.radians(lat)
    x = (lon + 180.0) / 360.0 * n * 256.0
    y = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n * 256.0
    return x, y


_GEO_CACHE: dict[str, tuple[float, float] | None] = {}
_GEO_PENDING: set[str] = set()


def _location_query(node: "NodeItem") -> str:
    for source in (node.title, node.content or ""):
        text = (source or "").strip()
        if text:
            return text.splitlines()[0].strip()
    return ""


def _location_label(node: "NodeItem") -> str:
    coords = _node_coordinates(node)
    if coords:
        return f"{coords[0]:.5f}, {coords[1]:.5f}"
    label = _location_query(node)
    return label[:48] if label else ""


def _geocode_query(query: str, node: "NodeItem"):
    url = (
        "https://nominatim.openstreetmap.org/search"
        f"?format=jsonv2&limit=1&q={urllib.parse.quote(query)}"
    )
    request = QNetworkRequest(QUrl(url))
    request.setTransferTimeout(15000)
    request.setHeader(
        QNetworkRequest.KnownHeaders.UserAgentHeader,
        "Mozilla/5.0 (X11; Linux x86_64) SkyFall/1.0",
    )
    reply = _http_manager().get(request)
    reply.finished.connect(lambda r=reply: _on_geocode_reply(r, query, node))


def _on_geocode_reply(reply, query: str, node: "NodeItem"):
    _GEO_PENDING.discard(query)
    coords = None
    try:
        data = bytes(reply.readAll())
        if data:
            try:
                results = json.loads(data)
                if results:
                    lat = _parse_coord(str(results[0].get("lat", "")))
                    lon = _parse_coord(str(results[0].get("lon", "")))
                    if lat is not None and lon is not None:
                        coords = (lat, lon)
            except ValueError:
                pass
    finally:
        reply.deleteLater()
    _GEO_CACHE[query] = coords
    try:
        node.update()
    except RuntimeError:
        pass


def _resolve_coordinates(node: "NodeItem") -> tuple[float, float] | None:
    coords = _node_coordinates(node)
    if coords:
        return coords
    if node.entity_type != "Geolocation":
        return None
    query = _location_query(node)
    if not query:
        return None
    cached = _GEO_CACHE.get(query, _MISSING)
    if cached is not _MISSING:
        return cached
    if query not in _GEO_PENDING:
        _GEO_PENDING.add(query)
        _geocode_query(query, node)
    return None


def _load_map_pixmap(
    node: "NodeItem", grid: int = 2, zoom: int = MAP_ZOOM
) -> QPixmap | None:
    coords = _resolve_coordinates(node)
    if coords is None:
        return None
    key = _map_key(*coords, grid, zoom)
    cached = _MAP_CACHE.get(key, _MISSING)
    if cached is not _MISSING:
        return cached
    waiters = _MAP_PENDING.setdefault(key, [])
    waiters.append(node)
    if len(waiters) == 1:
        _download_map_tiles(key, *coords, grid, zoom)
    return None


def _invalidate_map_cache(node: "NodeItem"):
    coords = _resolve_coordinates(node)
    if coords is None:
        return
    rlat, rlon = round(coords[0], 5), round(coords[1], 5)
    for key in list(_MAP_CACHE):
        if key[0] == rlat and key[1] == rlon:
            del _MAP_CACHE[key]
    for key in list(_MAP_PENDING):
        if key[0] == rlat and key[1] == rlon:
            try:
                node.update()
            except RuntimeError:
                pass
            del _MAP_PENDING[key]


def _download_map_tiles(key: tuple, lat: float, lon: float, grid: int, zoom: int):
    x, y = _world_pixel(lat, lon, zoom)
    tx, ty = int(x // 256), int(y // 256)
    tx0, ty0 = tx - grid // 2, ty - grid // 2
    pending = {"n": 0}
    total = grid * grid
    tiles = [None] * total
    manager = _http_manager()
    for i in range(total):
        xt = tx0 + (i % grid)
        yt = ty0 + (i // grid)
        url = f"https://tile.openstreetmap.org/{zoom}/{xt}/{yt}.png"
        request = QNetworkRequest(QUrl(url))
        request.setTransferTimeout(15000)
        request.setHeader(
            QNetworkRequest.KnownHeaders.UserAgentHeader,
            "Mozilla/5.0 (X11; Linux x86_64) SkyFall/1.0",
        )
        reply = manager.get(request)
        pending["n"] += 1
        reply.finished.connect(
            lambda r=reply, i=i, t=tiles: _on_map_tile(
                r, key, i, t, pending, grid, tx0, ty0
            )
        )


def _on_map_tile(
    reply, key: tuple, index: int, tiles: list, pending: dict, grid, tx0, ty0
):
    try:
        data = bytes(reply.readAll())
        img = QImage()
        if data and img.loadFromData(data):
            tiles[index] = img
    finally:
        reply.deleteLater()
    pending["n"] -= 1
    if pending["n"] > 0:
        return
    size = grid * 256
    mosaic = QImage(size, size, QImage.Format.Format_RGB32)
    mosaic.fill(QColor("#DDDDDD"))
    painter = QPainter(mosaic)
    for i, tile in enumerate(tiles):
        if tile is None:
            continue
        xt = tx0 + (i % grid)
        yt = ty0 + (i // grid)
        painter.drawImage((xt - tx0) * 256, (yt - ty0) * 256, tile)
    painter.end()
    _MAP_CACHE[key] = QPixmap.fromImage(mosaic)
    for node in _MAP_PENDING.pop(key, []):
        try:
            node.update()
        except RuntimeError:
            pass


class NodeItem(QGraphicsItem):
    def __init__(
        self, title="Node", content="", entity_type="Custom", node_id=None, parent=None
    ):
        super().__init__(parent)
        self.id = node_id if node_id is not None else uuid.uuid4().hex
        self.title = title
        self.content = content
        self.entity_type = entity_type if entity_type in ENTITY_NAMES else "Custom"
        self.evidence = []
        self.color = None
        self._edges = []
        self._photo_cache = {}
        self._map_zoom = MAP_ZOOM
        self._width = 160
        self._height = 120
        self._port_radius = 6
        self._dragging_edge = False
        self._drag_port = None
        self._temp_edge = None
        self._resizing = False
        self._resize_start = QPointF()
        self._resize_size = QPointF()

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)
        self.setCacheMode(QGraphicsItem.CacheMode.DeviceCoordinateCache)

    def symbol(self):
        return ENTITY_SYMBOLS.get(self.entity_type, "\u2699\ufe0f")

    def _photo_evidence(self):
        if self.entity_type != "Photo":
            return []
        photos = []
        for ev in self.evidence:
            if not isinstance(ev, str) or not ev:
                continue
            if ev.startswith(("http://", "https://")):
                pix = _REMOTE_CACHE.get(ev, _MISSING)
                if pix is _MISSING:
                    pix = _load_remote_pixmap(ev, self)
            else:
                pix = self._photo_cache.get(ev, _MISSING)
                if pix is _MISSING:
                    pix = None
                    if _is_image_path(ev) and os.path.exists(ev):
                        pm = QPixmap(ev)
                        if not pm.isNull():
                            pix = pm
                    self._photo_cache[ev] = pix
            if pix is not None:
                photos.append(pix)
        return photos

    def _draw_scaled_pixmap(self, painter, pm, rect):
        if rect.width() < 2 or rect.height() < 2:
            return
        scaled = pm.scaled(
            int(rect.width()),
            int(rect.height()),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        if scaled.isNull():
            return
        x = rect.x() + (rect.width() - scaled.width()) / 2.0
        y = rect.y() + (rect.height() - scaled.height()) / 2.0
        clip = QPainterPath()
        clip.addRoundedRect(rect, 6, 6)
        painter.save()
        painter.setClipPath(clip)
        painter.drawPixmap(int(x), int(y), scaled)
        painter.restore()

    def _paint_photo_gallery(self, painter, photos, y_offset, area_h):
        count = len(photos)
        avail_w = self._width - 20
        gap = 5.0
        pad = 2.0
        if count == 0 or area_h <= 0 or avail_w <= 0:
            return
        target = 90.0
        cols = max(1, int((avail_w + gap) / (target + gap)))
        cols = min(cols, count)
        rows = math.ceil(count / cols)
        cell = (avail_w - (cols - 1) * gap) / cols
        cell = min(cell, (area_h - (rows - 1) * gap) / rows)
        cell = max(cell, 1.0)
        max_visible = cols * rows
        c = _theme_colors()
        for i, pm in enumerate(photos[:max_visible]):
            col = i % cols
            row = i // cols
            cx = 10 + col * (cell + gap)
            cy = y_offset + row * (cell + gap)
            draw_rect = QRectF(cx + pad, cy + pad, cell - 2 * pad, cell - 2 * pad)
            self._draw_scaled_pixmap(painter, pm, draw_rect)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(c["card_border"], 1))
            painter.drawRoundedRect(draw_rect, 6, 6)
        extra = count - max_visible
        if extra > 0:
            badge = QRectF(10 + avail_w - 42, y_offset + area_h - 26, 36, 20)
            painter.setBrush(QBrush(QColor(0, 0, 0, 150)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(badge, 10, 10)
            painter.setPen(QPen(QColor("#ffffff")))
            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            painter.drawText(badge, Qt.AlignmentFlag.AlignCenter, f"+{extra}")

    def _paint_map(self, painter, pm, y_offset, area_h, coords, zoom=MAP_ZOOM):
        rect = QRectF(10, y_offset, self._width - 20, area_h)
        if rect.width() < 2 or rect.height() < 2:
            return
        lat, lon = coords
        x, y = _world_pixel(lat, lon, zoom)
        grid = pm.width() // 256
        tx, ty = int(x // 256), int(y // 256)
        tx0, ty0 = tx - grid // 2, ty - grid // 2
        px, py = x - tx0 * 256, y - ty0 * 256

        dst_ar = rect.width() / rect.height()
        src_ar = pm.width() / pm.height()
        if src_ar > dst_ar:
            sw = pm.height() * dst_ar
            sx = (pm.width() - sw) / 2
            sy, sh = 0.0, float(pm.height())
        else:
            sh = pm.width() / dst_ar
            sy = (pm.height() - sh) / 2
            sx, sw = 0.0, float(pm.width())

        clip = QPainterPath()
        clip.addRoundedRect(rect, 6, 6)
        painter.save()
        painter.setClipPath(clip)
        painter.drawPixmap(rect.toRect(), pm, QRectF(sx, sy, sw, sh).toRect())
        painter.restore()

        pin_x = rect.x() + (px - sx) / sw * rect.width()
        pin_y = rect.y() + (py - sy) / sh * rect.height()
        pin = QPainterPath()
        pin.addEllipse(QPointF(pin_x, pin_y - 9), 6, 6)
        pin.moveTo(pin_x - 3.5, pin_y - 2)
        pin.lineTo(pin_x + 3.5, pin_y - 2)
        pin.lineTo(pin_x, pin_y + 7)
        pin.closeSubpath()
        painter.setBrush(QBrush(QColor("#e74c3c")))
        painter.setPen(QPen(QColor("#ffffff"), 1.5))
        painter.drawPath(pin)

        c = _theme_colors()
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(c["card_border"], 1))
        painter.drawRoundedRect(rect, 6, 6)

        label = f"{lat:.5f}, {lon:.5f}"
        painter.setFont(QFont("Segoe UI", 7))
        fm = painter.fontMetrics()
        tw = fm.horizontalAdvance(label) + 12
        chip = QRectF(
            rect.x() + 4,
            rect.bottom() - 18,
            min(tw, rect.width() - 8),
            14,
        )
        painter.setBrush(QBrush(QColor(0, 0, 0, 150)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(chip, 7, 7)
        painter.setPen(QPen(QColor("#ffffff")))
        painter.drawText(chip, Qt.AlignmentFlag.AlignCenter, label)

    def _get_height(self):
        return self._height

    def boundingRect(self):
        m = self._port_radius + 4
        return QRectF(-m, -m, self._width + 2 * m, self._get_height() + 2 * m)

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        c = _theme_colors()
        rect = QRectF(0, 0, self._width, self._get_height()).adjusted(1, 1, -1, -1)
        type_color = QColor(ENTITY_COLORS.get(self.entity_type, "#636e72"))

        custom = QColor(self.color) if self.color else None
        if custom is not None:
            contrast = _contrast_color(custom)
            card_bg = custom
            title_color = contrast
            content_color = QColor(contrast)
            content_color.setAlpha(200)
            port_color = contrast
            border_color = QColor(contrast)
            border_color.setAlpha(200 if self.isSelected() else 90)
        else:
            card_bg = c["card_bg"]
            title_color = c["card_title"]
            content_color = c["card_content"]
            port_color = c["port_color"]
            border_color = c["port_color"] if self.isSelected() else c["card_border"]

        glow_color = QColor(type_color)
        glow_color.setAlpha(40)
        painter.setBrush(QBrush(glow_color))
        painter.setPen(Qt.PenStyle.NoPen)
        if self.isSelected():
            glow_rect = rect.adjusted(-3, -3, 3, 3)
            painter.drawRoundedRect(glow_rect, 12, 12)
        painter.setBrush(QBrush(glow_color))
        if self.isSelected():
            glow_rect2 = rect.adjusted(-1, -1, 1, 1)
            painter.drawRoundedRect(glow_rect2, 11, 11)

        painter.setBrush(QBrush(card_bg))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, 10, 10)

        border_width = 2 if self.isSelected() else 1
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(border_color, border_width))
        painter.drawRoundedRect(rect, 10, 10)

        title_y = 10
        painter.setPen(title_color)
        font_title = QFont("Segoe UI", 10, QFont.Weight.Bold)
        painter.setFont(font_title)
        title_rect = QRectF(10, title_y, self._width - 20, 20)
        painter.drawText(
            title_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            self.title,
        )

        y_offset = title_y + 22
        content_area = self._get_height() - y_offset - 6

        photos = self._photo_evidence() if self.entity_type == "Photo" else None
        if photos:
            self._paint_photo_gallery(painter, photos, y_offset, content_area)
        elif self.entity_type == "Geolocation":
            coords = _resolve_coordinates(self)
            map_pix = None
            if coords:
                zoom = self._map_zoom
                scale = max(0.5, abs(painter.worldTransform().m11()))
                grid = _map_grid_for_size(self, scale)
                map_pix = _load_map_pixmap(self, grid, zoom)
                if map_pix is None:
                    for g in range(grid - 1, 1, -1):
                        pm = _MAP_CACHE.get(_map_key(*coords, g, zoom))
                        if pm is not None:
                            map_pix = pm
                            break
            if map_pix is not None:
                self._paint_map(painter, map_pix, y_offset, content_area, coords, zoom)
            else:
                label = _location_label(self)
                if not label:
                    painter.setPen(content_color)
                    painter.setFont(QFont("Segoe UI", 8))
                    painter.drawText(
                        QRectF(10, y_offset, self._width - 20, content_area),
                        Qt.AlignmentFlag.AlignCenter,
                        "No location",
                    )
                else:
                    text = f"\U0001f4cd {label}"
                    if coords is None:
                        text += " \u2026"
                    painter.setPen(content_color)
                    painter.setFont(QFont("Segoe UI", 8))
                    painter.drawText(
                        QRectF(10, y_offset, self._width - 20, content_area),
                        Qt.AlignmentFlag.AlignCenter,
                        text,
                    )
        elif self.content:
            painter.setPen(content_color)
            font_content = QFont("Segoe UI", 9)
            painter.setFont(font_content)
            content_rect = QRectF(10, y_offset, self._width - 20, content_area)
            opt = QTextOption()
            opt.setWrapMode(QTextOption.WrapMode.WordWrap)
            painter.drawText(content_rect, self.content, opt)
        elif self.evidence:
            painter.setPen(content_color)
            font_content = QFont("Segoe UI", 7)
            painter.setFont(font_content)
            max_items = min(len(self.evidence), 3)
            for i in range(max_items):
                ev_path = self.evidence[i]
                label = (
                    os.path.basename(ev_path) if os.path.exists(ev_path) else ev_path
                )
                if len(label) > 20:
                    label = label[:17] + "..."
                ev_rect = QRectF(12, y_offset, self._width - 24, 14)
                painter.drawText(
                    ev_rect,
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                    f"\u2022 {label}",
                )
                y_offset += 16
        elif self.entity_type == "Photo":
            painter.setPen(content_color)
            painter.setFont(QFont("Segoe UI", 8))
            painter.drawText(
                QRectF(10, y_offset, self._width - 20, content_area),
                Qt.AlignmentFlag.AlignCenter,
                "No photos",
            )

        painter.setPen(Qt.PenStyle.NoPen)
        for _, pos in self._ports().items():
            painter.setBrush(QBrush(port_color))
            painter.drawEllipse(pos, self._port_radius, self._port_radius)

        if self.isSelected():
            hr = self._resize_handle_rect().adjusted(3, 3, -3, -3)
            painter.setBrush(QBrush(type_color))
            painter.setPen(QPen(type_color, 1))
            painter.drawRoundedRect(hr, 3, 3)

    def _resize_handle_rect(self):
        s = 16
        return QRectF(self._width - s, self._height - s, s, s)

    def _on_resize_handle(self, pos):
        return self._resize_handle_rect().adjusted(-2, -2, 2, 2).contains(pos)

    def _ports(self):
        h = self._get_height()
        return {
            "left": QPointF(0, h / 2),
            "right": QPointF(self._width, h / 2),
            "top": QPointF(self._width / 2, 0),
            "bottom": QPointF(self._width / 2, h),
        }

    def port_pos(self, name):
        return self._ports()[name]

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            for edge in self._connected_edges():
                edge.adjust()
        return super().itemChange(change, value)

    def add_edge_ref(self, edge):
        if edge not in self._edges:
            self._edges.append(edge)

    def remove_edge_ref(self, edge):
        if edge in self._edges:
            self._edges.remove(edge)

    def _connected_edges(self):
        return list(self._edges)

    def _port_at_pos(self, pos):
        r = self._port_radius + 4
        for name, p in self._ports().items():
            if (pos - p).manhattanLength() < r:
                return name
        return None

    def hoverMoveEvent(self, event):
        if self._on_resize_handle(event.pos()):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif self._port_at_pos(event.pos()):
            self.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event):
        self.setCursor(Qt.CursorShape.ArrowCursor)
        super().hoverLeaveEvent(event)

    def mouseDoubleClickEvent(self, event):
        if (
            event.button() == Qt.MouseButton.LeftButton
            and not self._port_at_pos(event.pos())
            and not self._on_resize_handle(event.pos())
        ):
            for view in self.scene().views():
                if isinstance(view, GraphWidget):
                    view.edit_node(self)
                    break
        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self._on_resize_handle(event.pos()):
                self._resizing = True
                self._resize_start = event.pos()
                self._resize_size = QPointF(self._width, self._height)
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
                event.accept()
                return
            port = self._port_at_pos(event.pos())
            if port:
                self._drag_port = port
                self._start_edge_drag(event)
                return
        super().mousePressEvent(event)

    def _start_edge_drag(self, event):
        self._temp_edge = QGraphicsPathItem()
        pen = QPen(QColor("#2c3e50"), 2, Qt.PenStyle.DashLine)
        self._temp_edge.setPen(pen)
        self.scene().addItem(self._temp_edge)
        self._dragging_edge = True

    def mouseMoveEvent(self, event):
        if self._resizing:
            delta = event.pos() - self._resize_start
            new_w = max(100, int(self._resize_size.x() + delta.x()))
            new_h = max(60, int(self._resize_size.y() + delta.y()))
            if new_w != self._width or new_h != self._height:
                self.prepareGeometryChange()
                self._width = new_w
                self._height = new_h
                for edge in self._connected_edges():
                    edge.adjust()
                self.update()
            event.accept()
            return
        if self._dragging_edge and self._temp_edge:
            start = self.mapToScene(self.port_pos(self._drag_port))
            end = event.scenePos()
            dx, dy = PORT_DIR[self._drag_port]
            path = build_edge_path(start, end, QPointF(dx, dy), QPointF())
            self._temp_edge.setPath(path)
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._resizing:
            self._resizing = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return
        if self._dragging_edge:
            self._dragging_edge = False
            if self._temp_edge:
                self.scene().removeItem(self._temp_edge)
                self._temp_edge = None

            target_node = None
            for item in self.scene().items(event.scenePos()):
                if isinstance(item, NodeItem) and item != self:
                    target_node = item
                    break

            if target_node:
                for view in self.scene().views():
                    if isinstance(view, GraphWidget):
                        tp = (
                            target_node._port_at_pos(
                                target_node.mapFromScene(event.scenePos())
                            )
                            or "left"
                        )
                        view.add_edge(self, target_node, self._drag_port, tp)
                        break
            self._drag_port = None
        else:
            super().mouseReleaseEvent(event)


class EdgeItem(QGraphicsPathItem):
    def __init__(
        self,
        source: NodeItem,
        target: NodeItem,
        source_port="right",
        target_port="left",
        label="",
        relationship_type="",
        style="normal",
        parent=None,
    ):
        super().__init__(parent)
        self.source = source
        self.target = target
        self.source_port = source_port
        self.target_port = target_port
        self.label = label
        self.relationship_type = relationship_type
        self.style = style if style in EDGE_STYLES else "normal"
        self.setPen(self._make_pen())
        self.setZValue(-1)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.adjust()

    def _make_pen(self):
        spec = EDGE_STYLES.get(self.style, EDGE_STYLES["normal"])
        pen = QPen(
            _theme_colors()["edge_color"],
            spec["width"],
            spec["pen_style"],
            Qt.PenCapStyle.RoundCap,
            Qt.PenJoinStyle.RoundJoin,
        )
        if self.style == "dashed":
            pen.setDashPattern([6, 4])
        return pen

    def adjust(self):
        src = self.source.mapToScene(self.source.port_pos(self.source_port))
        tgt = self.target.mapToScene(self.target.port_pos(self.target_port))
        sdx, sdy = PORT_DIR[self.source_port]
        tdx, tdy = PORT_DIR[self.target_port]
        path = build_edge_path(src, tgt, QPointF(sdx, sdy), QPointF(tdx, tdy))
        self.setPath(path)

    def shape(self):
        stroker = QPainterPathStroker()
        stroker.setWidth(24)
        return stroker.createStroke(self.path())

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = _theme_colors()
        spec = EDGE_STYLES.get(self.style, EDGE_STYLES["normal"])
        pen = self._make_pen()
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(self.path())

        if self.path().elementCount() > 0:
            last_pt = self.path().currentPosition()
            path_length = self.path().length()
            if path_length > 10:
                percent = 1.0 - 10 / path_length
                prev_pt = self.path().pointAtPercent(percent)
            else:
                prev_pt = self.path().pointAtPercent(0)

            line = QLineF(prev_pt, last_pt)
            angle = -line.angle()

            painter.save()
            painter.translate(last_pt)
            painter.rotate(angle)
            arrow_size = 9 + spec["width"]
            painter.setBrush(QBrush(c["edge_color"]))
            painter.setPen(Qt.PenStyle.NoPen)
            arrow_path = QPainterPath()
            arrow_path.moveTo(0, 0)
            arrow_path.lineTo(-arrow_size, -arrow_size / 2)
            arrow_path.lineTo(-arrow_size, arrow_size / 2)
            arrow_path.closeSubpath()
            painter.drawPath(arrow_path)
            painter.restore()

        display = self.relationship_type or self.label
        if display:
            path_length = self.path().length()
            if path_length > 40:
                mid = self.path().pointAtPercent(0.5)
                painter.save()
                fm = painter.fontMetrics()
                text_w = fm.horizontalAdvance(display) + 12
                text_h = fm.height() + 6
                bg = QRectF(mid.x() - text_w / 2, mid.y() - text_h / 2, text_w, text_h)
                painter.setBrush(QBrush(c["card_title"]))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(bg, 4, 4)
                painter.setPen(QPen(c["card_bg"]))
                painter.drawText(bg, Qt.AlignmentFlag.AlignCenter, display)
                painter.restore()

        if self.label and self.relationship_type:
            mid = self.path().pointAtPercent(0.5)
            painter.save()
            painter.setFont(QFont("Segoe UI", 7))
            fm = painter.fontMetrics()
            text_w = fm.horizontalAdvance(self.label) + 8
            text_h = fm.height() + 4
            bg = QRectF(
                mid.x() - text_w / 2,
                mid.y() + 10,
                text_w,
                text_h,
            )
            painter.setBrush(QBrush(c["card_border"]))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(bg, 3, 3)
            painter.setPen(QPen(c["card_title"]))
            painter.drawText(bg, Qt.AlignmentFlag.AlignCenter, self.label)
            painter.restore()


class NodeEditDialog(QMainWindow):
    data_ready = Signal(str, str, str, list)

    def __init__(
        self, title="", content="", entity_type="Custom", evidence=None, parent=None
    ):
        super().__init__(parent)
        self.setWindowTitle("Edit Node")

        from src.ui.theme import dialog_palette

        pal = dialog_palette()
        bg = pal["bg"]
        surface = pal["surface"]
        border = pal["border"]
        text = pal["text"]
        radius = pal["radius"]

        self.setStyleSheet(f"""
            NodeEditDialog {{
                background-color: {bg};
                color: {text};
                border: 1px solid {border};
                border-radius: {radius};
            }}
            NodeEditDialog QLineEdit, NodeEditDialog QPlainTextEdit {{
                border-radius: {radius};
                border: 1px solid {border};
                background-color: {surface};
                color: {text};
                padding: 5px;
                selection-background-color: {text};
                selection-color: {bg};
            }}
            NodeEditDialog QLineEdit:focus, NodeEditDialog QPlainTextEdit:focus {{
                border: 1px solid {text};
            }}
            NodeEditDialog QLineEdit::placeholder,
            NodeEditDialog QPlainTextEdit::placeholder {{
                color: {border};
            }}
            NodeEditDialog QPushButton {{
                border-radius: {radius};
                border: 1px solid {border};
                background-color: {surface};
                color: {text};
                padding: 6px 16px;
                min-height: 24px;
            }}
            NodeEditDialog QPushButton:hover {{
                background-color: {border};
                color: {text};
            }}
            NodeEditDialog QPushButton:pressed {{
                background-color: {text};
                color: {bg};
            }}
        """)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setSpacing(8)
        self.setCentralWidget(central)

        self.title_edit = QLineEdit(title)
        self.title_edit.setPlaceholderText("Title")
        layout.addWidget(self.title_edit)

        self.content_edit = QPlainTextEdit(content)
        self.content_edit.setPlaceholderText("Content")
        self.content_edit.setMinimumHeight(80)
        layout.addWidget(self.content_edit)

        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Type:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(ENTITY_NAMES)
        if entity_type in ENTITY_NAMES:
            self.type_combo.setCurrentIndex(ENTITY_NAMES.index(entity_type))
        type_layout.addWidget(self.type_combo)
        layout.addLayout(type_layout)

        evidence_label = QLabel("Evidence:")
        layout.addWidget(evidence_label)

        self.evidence_list = QListWidget()
        self.evidence_list.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.evidence_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.evidence_list.customContextMenuRequested.connect(
            self._evidence_context_menu
        )
        self.evidence_list.itemDoubleClicked.connect(self._open_evidence)
        evidence = evidence or []
        for ev_path in evidence:
            label = os.path.basename(ev_path) if os.path.exists(ev_path) else ev_path
            self.evidence_list.addItem(f"{label}\n{ev_path}")
        layout.addWidget(self.evidence_list)

        ev_btn_layout = QHBoxLayout()
        btn_add_file = QPushButton("Add File")
        btn_add_file.clicked.connect(self._add_file)
        btn_add_url = QPushButton("Add URL")
        btn_add_url.clicked.connect(self._add_url)
        btn_remove_ev = QPushButton("Remove Selected")
        btn_remove_ev.clicked.connect(self._remove_evidence)
        ev_btn_layout.addWidget(btn_add_file)
        ev_btn_layout.addWidget(btn_add_url)
        ev_btn_layout.addWidget(btn_remove_ev)
        layout.addLayout(ev_btn_layout)

        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_save = QPushButton("Save")
        btn_save.clicked.connect(self._save)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.close)
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

    def _save(self):
        evidence = []
        for i in range(self.evidence_list.count()):
            text = self.evidence_list.item(i).text()
            evidence.append(text.split("\n", 1)[-1])
        self.data_ready.emit(
            self.title_edit.text(),
            self.content_edit.toPlainText(),
            self.type_combo.currentText(),
            evidence,
        )
        self.close()

    def _add_file(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select Evidence Files")
        for f in files:
            self.evidence_list.addItem(f"{os.path.basename(f)}\n{f}")

    def _add_url(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Add URL")
        from src.ui.theme import dialog_palette

        pal = dialog_palette()
        bg = pal["bg"]
        surface = pal["surface"]
        border = pal["border"]
        text = pal["text"]
        radius = pal["radius"]
        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: {bg};
                color: {text};
                border: 1px solid {border};
                border-radius: {radius};
            }}
            QLineEdit {{
                border-radius: {radius};
                border: 1px solid {border};
                background-color: {surface};
                color: {text};
                padding: 5px;
                selection-background-color: {text};
                selection-color: {bg};
            }}
            QPushButton {{
                border-radius: {radius};
                border: 1px solid {border};
                background-color: {surface};
                color: {text};
                padding: 6px 16px;
                min-height: 24px;
            }}
            QPushButton:hover {{
                background-color: {border};
                color: {text};
            }}
            QPushButton:pressed {{
                background-color: {text};
                color: {bg};
            }}
        """)
        layout = QVBoxLayout(dialog)
        line_edit = QLineEdit()
        line_edit.setPlaceholderText("https://example.com/file.pdf")
        layout.addWidget(line_edit)
        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("OK")
        btn_ok.clicked.connect(dialog.accept)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(dialog.reject)
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)
        _center_dialog(dialog)
        if dialog.exec() == QDialog.DialogCode.Accepted and line_edit.text().strip():
            self.evidence_list.addItem(
                f"{line_edit.text().strip()}\n{line_edit.text().strip()}"
            )

    def _remove_evidence(self):
        for item in self.evidence_list.selectedItems():
            self.evidence_list.takeItem(self.evidence_list.row(item))

    def _evidence_context_menu(self, pos):
        item = self.evidence_list.itemAt(pos)
        if not item:
            return
        menu = QMenu(self)
        delete_act = QAction("Delete", self)
        delete_act.triggered.connect(lambda: self._remove_evidence())
        menu.addAction(delete_act)
        menu.exec(self.evidence_list.viewport().mapToGlobal(pos))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete and self.evidence_list.hasFocus():
            self._remove_evidence()
        else:
            super().keyPressEvent(event)

    def _open_evidence(self, item):
        path = item.text().split("\n", 1)[-1]
        url = QUrl.fromLocalFile(path) if os.path.exists(path) else QUrl(path)
        QDesktopServices.openUrl(url)

    def get_data(self):
        evidence = []
        for i in range(self.evidence_list.count()):
            path = self.evidence_list.item(i).text().split("\n", 1)[-1]
            evidence.append(path)
        return (
            self.title_edit.text(),
            self.content_edit.toPlainText(),
            self.type_combo.currentText(),
            evidence,
        )


class PropertiesPanel(QDockWidget):
    def __init__(self, parent=None):
        super().__init__("Properties", parent)
        self.setAllowedAreas(
            Qt.DockWidgetArea.RightDockWidgetArea | Qt.DockWidgetArea.LeftDockWidgetArea
        )
        self._node = None

        widget = QWidget()
        layout = QVBoxLayout(widget)

        info_group = QGroupBox("Node Info")
        info_layout = QFormLayout()
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Title")
        self.title_edit.textChanged.connect(self._on_title_changed)
        self.type_combo = QComboBox()
        self.type_combo.addItems(ENTITY_NAMES)
        self.type_combo.currentTextChanged.connect(self._on_type_changed)
        self.id_label = QLabel("-")
        info_layout.addRow("Title:", self.title_edit)
        info_layout.addRow("Type:", self.type_combo)
        info_layout.addRow("ID:", self.id_label)
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        content_group = QGroupBox("Content")
        content_layout = QVBoxLayout()
        self.content_edit = QPlainTextEdit()
        self.content_edit.setPlaceholderText("Content")
        self.content_edit.textChanged.connect(self._on_content_changed)
        content_layout.addWidget(self.content_edit)
        content_group.setLayout(content_layout)
        layout.addWidget(content_group)

        evidence_group = QGroupBox("Evidence")
        evidence_layout = QVBoxLayout()
        self.evidence_list = QListWidget()
        self.evidence_list.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.evidence_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.evidence_list.customContextMenuRequested.connect(
            self._evidence_context_menu
        )
        self.evidence_list.itemDoubleClicked.connect(self._open_evidence)
        evidence_layout.addWidget(self.evidence_list)
        ev_btn_layout = QHBoxLayout()
        btn_add_file = QPushButton("Add File")
        btn_add_file.clicked.connect(self._add_file)
        btn_add_url = QPushButton("Add URL")
        btn_add_url.clicked.connect(self._add_url)
        btn_remove = QPushButton("Remove")
        btn_remove.clicked.connect(self._remove_evidence)
        ev_btn_layout.addWidget(btn_add_file)
        ev_btn_layout.addWidget(btn_add_url)
        ev_btn_layout.addWidget(btn_remove)
        evidence_layout.addLayout(ev_btn_layout)
        evidence_group.setLayout(evidence_layout)
        layout.addWidget(evidence_group)

        layout.addStretch()
        widget.setLayout(layout)
        self.setWidget(widget)
        self.clear()

    def show_node(self, node):
        self._node = node
        self.title_edit.blockSignals(True)
        self.title_edit.setText(node.title)
        self.title_edit.blockSignals(False)
        self.type_combo.blockSignals(True)
        self.type_combo.setCurrentIndex(
            ENTITY_NAMES.index(node.entity_type)
            if node.entity_type in ENTITY_NAMES
            else 0
        )
        self.type_combo.blockSignals(False)
        self.id_label.setText(node.id[:8] + "...")
        self.content_edit.blockSignals(True)
        self.content_edit.setPlainText(node.content)
        self.content_edit.blockSignals(False)
        self.evidence_list.clear()
        for ev in node.evidence:
            label = os.path.basename(ev) if os.path.exists(ev) else ev
            self.evidence_list.addItem(f"{label}\n{ev}")

    def clear(self):
        self._node = None
        self.title_edit.blockSignals(True)
        self.title_edit.setText("")
        self.title_edit.blockSignals(False)
        self.type_combo.blockSignals(True)
        self.type_combo.setCurrentIndex(0)
        self.type_combo.blockSignals(False)
        self.id_label.setText("-")
        self.content_edit.blockSignals(True)
        self.content_edit.setPlainText("")
        self.content_edit.blockSignals(False)
        self.evidence_list.clear()

    def _on_title_changed(self, text):
        if self._node:
            self._node.title = text
            self._node.update()

    def _on_type_changed(self, text):
        if self._node:
            self._node.entity_type = text
            self._node.prepareGeometryChange()
            self._node.update()

    def _on_content_changed(self):
        if self._node:
            self._node.content = self.content_edit.toPlainText()
            self._node.update()

    def _add_file(self):
        if not self._node:
            return
        files, _ = QFileDialog.getOpenFileNames(self, "Select Evidence Files")
        for f in files:
            self._node.evidence.append(f)
            self.evidence_list.addItem(f"{os.path.basename(f)}\n{f}")
        self._node._photo_cache.clear()
        self._node.update()

    def _add_url(self):
        if not self._node:
            return
        from src.ui.theme import dialog_palette

        pal = dialog_palette()
        bg = pal["bg"]
        surface = pal["surface"]
        border = pal["border"]
        text = pal["text"]
        radius = pal["radius"]
        dialog = QDialog(self)
        dialog.setWindowTitle("Add URL")
        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: {bg};
                color: {text};
                border: 1px solid {border};
                border-radius: {radius};
            }}
            QLineEdit {{
                border-radius: {radius};
                border: 1px solid {border};
                background-color: {surface};
                color: {text};
                padding: 5px;
            }}
            QPushButton {{
                border-radius: {radius};
                border: 1px solid {border};
                background-color: {surface};
                color: {text};
                padding: 6px 16px;
                min-height: 24px;
            }}
            QPushButton:hover {{
                background-color: {border};
            }}
            QPushButton:pressed {{
                background-color: {text};
                color: {bg};
            }}
        """)
        dlg_layout = QVBoxLayout(dialog)
        line_edit = QLineEdit()
        line_edit.setPlaceholderText("https://example.com/file.pdf")
        dlg_layout.addWidget(line_edit)
        btn_hlay = QHBoxLayout()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(dialog.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        btn_hlay.addWidget(ok_btn)
        btn_hlay.addWidget(cancel_btn)
        dlg_layout.addLayout(btn_hlay)
        _center_dialog(dialog)
        if dialog.exec() == QDialog.DialogCode.Accepted and line_edit.text().strip():
            url = line_edit.text().strip()
            self._node.evidence.append(url)
            self.evidence_list.addItem(f"{url}\n{url}")
            self._node.update()

    def _remove_evidence(self):
        if not self._node:
            return
        for item in self.evidence_list.selectedItems():
            idx = self.evidence_list.row(item)
            if 0 <= idx < len(self._node.evidence):
                del self._node.evidence[idx]
            self.evidence_list.takeItem(idx)
        self._node._photo_cache.clear()
        self._node.update()

    def _evidence_context_menu(self, pos):
        item = self.evidence_list.itemAt(pos)
        if not item:
            return
        menu = QMenu(self)
        delete_act = QAction("Delete", self)
        delete_act.triggered.connect(self._remove_evidence)
        menu.addAction(delete_act)
        menu.exec(self.evidence_list.viewport().mapToGlobal(pos))

    def _open_evidence(self, item):
        path = item.text().split("\n", 1)[-1]
        url = QUrl.fromLocalFile(path) if os.path.exists(path) else QUrl(path)
        QDesktopServices.openUrl(url)


class GraphWidget(QGraphicsView):
    nodeAdded = Signal(object)
    edgeAdded = Signal(object)
    selectionChanged = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform
        )
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)

        self._scene = QGraphicsScene(self)
        self._scene.setSceneRect(-5000, -5000, 10000, 10000)
        self.setScene(self._scene)
        self._scene.selectionChanged.connect(self._on_selection_changed)

        self._panning = False
        self._pan_start = QPointF()
        self._filter_text = ""
        self._path_source = None

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        self._accept_drops = True
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasText() and event.mimeData().text() in ENTITY_NAMES:
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasText() and event.mimeData().text() in ENTITY_NAMES:
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        etype = event.mimeData().text()
        if etype in ENTITY_NAMES:
            scene_pos = self.mapToScene(event.position().toPoint())
            node = self.add_node(scene_pos, etype)
            node.title = f"New {etype}"
            node.update()
            event.acceptProposedAction()
        else:
            super().dropEvent(event)

    def set_filter(self, text: str):
        self._filter_text = text.lower().strip()
        for item in self._scene.items():
            if isinstance(item, NodeItem):
                match = (
                    not self._filter_text
                    or self._filter_text in item.title.lower()
                    or self._filter_text in item.entity_type.lower()
                    or self._filter_text in item.content.lower()
                )
                item.setVisible(match)
        self._scene.update()

    def _on_selection_changed(self):
        selected = self._scene.selectedItems()
        if len(selected) == 1 and isinstance(selected[0], NodeItem):
            self.selectionChanged.emit(selected[0])
        else:
            self.selectionChanged.emit(None)

    def _show_context_menu(self, pos):
        scene_pos = self.mapToScene(pos)
        item = self._scene.itemAt(scene_pos, self.transform())
        menu = QMenu(self)

        if isinstance(item, EdgeItem):
            label_action = QAction("Edit Edge", self)
            label_action.triggered.connect(lambda: self.edit_edge_label(item))
            menu.addAction(label_action)

            style_menu = QMenu("Style", self)
            style_group = QActionGroup(self)
            style_group.setExclusive(True)
            for sname in EDGE_STYLES:
                act = QAction(EDGE_STYLES[sname]["label"], self)
                act.setCheckable(True)
                act.setChecked(item.style == sname)
                act.triggered.connect(
                    lambda checked, n=item, s=sname: self._set_edge_style(n, s)
                )
                style_group.addAction(act)
                style_menu.addAction(act)
            menu.addMenu(style_menu)
            menu.addSeparator()
            delete_action = QAction("Delete Edge", self)
            delete_action.triggered.connect(lambda: self.remove_edge(item))
            menu.addAction(delete_action)
        elif isinstance(item, NodeItem):
            edit_action = QAction("Edit", self)
            edit_action.triggered.connect(lambda: self.edit_node(item))
            menu.addAction(edit_action)
            attach_action = QAction("Attach Evidence", self)
            attach_action.triggered.connect(lambda: self.edit_node(item))
            menu.addAction(attach_action)

            color_action = QAction("Set Color...", self)
            color_action.triggered.connect(lambda: self.set_node_color(item))
            menu.addAction(color_action)
            if item.color:
                reset_color_action = QAction("Reset Color", self)
                reset_color_action.triggered.connect(
                    lambda: self.reset_node_color(item)
                )
                menu.addAction(reset_color_action)
            menu.addSeparator()

            analysis_menu = QMenu("Analysis", self)
            sp_action = QAction("Shortest Path", self)
            sp_action.triggered.connect(lambda: self._start_shortest_path(item))
            analysis_menu.addAction(sp_action)
            menu.addMenu(analysis_menu)

            if hasattr(self, "_transform_controller"):
                transforms = self._transform_controller.get_transforms(item)
                if transforms:
                    tx_menu = QMenu("\u26a1 Transforms", self)
                    for tf in transforms:
                        act = QAction(f"  {tf.name}", self)
                        act.setToolTip(tf.description)
                        act.triggered.connect(
                            lambda checked, n=item, t=tf: (
                                self._transform_controller.execute(n, t)
                            )
                        )
                        tx_menu.addAction(act)
                    menu.addMenu(tx_menu)

            menu.addSeparator()

            delete_action = QAction("Delete Node", self)
            delete_action.triggered.connect(lambda: self.remove_node(item))
            menu.addAction(delete_action)
        else:
            add_menu = QMenu("Add", self)
            for etype in ENTITY_NAMES:
                sym = ENTITY_SYMBOLS.get(etype, "")
                act = QAction(f"{sym} {etype}", self)
                act.triggered.connect(
                    lambda checked, t=etype: self.add_node(scene_pos, t)
                )
                add_menu.addAction(act)
            menu.addMenu(add_menu)
            menu.addSeparator()
            analysis_all = QMenu("Global Analysis", self)
            cent_action = QAction("Show Centrality", self)
            cent_action.triggered.connect(self._show_centrality)
            analysis_all.addAction(cent_action)
            cluster_action = QAction("Detect Communities", self)
            cluster_action.triggered.connect(self._detect_communities)
            analysis_all.addAction(cluster_action)
            menu.addMenu(analysis_all)

        menu.exec(self.viewport().mapToGlobal(pos))

    def edit_node(self, node: NodeItem):
        dialog = NodeEditDialog(
            node.title, node.content, node.entity_type, node.evidence, self
        )
        dialog.data_ready.connect(
            lambda title, content, etype, ev: self._on_node_edited(
                node, title, content, etype, ev
            )
        )
        _center_dialog(dialog)
        dialog.show()

    def _on_node_edited(self, node, title, content, entity_type, evidence):
        node.title = title
        node.content = content
        node.entity_type = entity_type
        node.evidence = evidence
        node._photo_cache.clear()
        node.prepareGeometryChange()
        node.update()

    def set_node_color(self, node: NodeItem):
        current = (
            QColor(node.color)
            if node.color
            else QColor(ENTITY_COLORS.get(node.entity_type, "#636e72"))
        )
        color = QColorDialog.getColor(current, self, "Node Color")
        if color.isValid():
            node.color = color.name()
            node.update()

    def reset_node_color(self, node: NodeItem):
        node.color = None
        node.update()

    def _set_edge_style(self, edge, style):
        edge.style = style if style in EDGE_STYLES else "normal"
        edge.setPen(edge._make_pen())
        edge.update()

    def edit_edge_label(self, edge: EdgeItem):
        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Edge")
        from src.ui.theme import dialog_palette

        pal = dialog_palette()
        bg = pal["bg"]
        surface = pal["surface"]
        border = pal["border"]
        text = pal["text"]
        radius = pal["radius"]
        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: {bg};
                color: {text};
                border: 1px solid {border};
                border-radius: {radius};
            }}
            QLineEdit, QComboBox {{
                border-radius: {radius};
                border: 1px solid {border};
                background-color: {surface};
                color: {text};
                padding: 5px;
                selection-background-color: {text};
                selection-color: {bg};
            }}
            QPushButton {{
                border-radius: {radius};
                border: 1px solid {border};
                background-color: {surface};
                color: {text};
                padding: 6px 16px;
                min-height: 24px;
            }}
            QPushButton:hover {{
                background-color: {border};
                color: {text};
            }}
            QPushButton:pressed {{
                background-color: {text};
                color: {bg};
            }}
        """)
        layout = QVBoxLayout(dialog)

        rel_layout = QHBoxLayout()
        rel_layout.addWidget(QLabel("Type:"))
        type_combo = QComboBox()
        type_combo.addItem("")
        for rt in RELATIONSHIP_TYPES:
            type_combo.addItem(rt)
        if edge.relationship_type in RELATIONSHIP_TYPES:
            type_combo.setCurrentText(edge.relationship_type)
        rel_layout.addWidget(type_combo)
        layout.addLayout(rel_layout)

        line_edit = QLineEdit(edge.label)
        line_edit.setPlaceholderText("Additional label (optional)")
        layout.addWidget(line_edit)

        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("OK")
        btn_ok.clicked.connect(dialog.accept)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(dialog.reject)
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)
        _center_dialog(dialog)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            edge.relationship_type = type_combo.currentText()
            edge.label = line_edit.text()
            edge.update()

    def add_node(self, scene_pos, entity_type="Custom"):
        node = NodeItem(title="New node", entity_type=entity_type)
        node.setPos(scene_pos)
        self._scene.addItem(node)
        self.nodeAdded.emit(node)
        return node

    def add_edge(
        self, source_node, target_node, source_port="right", target_port="left"
    ):
        edge = EdgeItem(source_node, target_node, source_port, target_port)
        self._scene.addItem(edge)
        source_node.add_edge_ref(edge)
        target_node.add_edge_ref(edge)
        self.edgeAdded.emit(edge)
        return edge

    def remove_node(self, node: NodeItem):
        for edge in node._connected_edges():
            self.remove_edge(edge)
        self._scene.removeItem(node)

    def remove_edge(self, edge: EdgeItem):
        edge.source.remove_edge_ref(edge)
        edge.target.remove_edge_ref(edge)
        self._scene.removeItem(edge)

    def _to_networkx(self):
        g = nx.Graph()
        for item in self._scene.items():
            if isinstance(item, NodeItem):
                g.add_node(item.id, label=item.title, etype=item.entity_type)
        for item in self._scene.items():
            if isinstance(item, EdgeItem):
                g.add_edge(
                    item.source.id,
                    item.target.id,
                    label=item.relationship_type or item.label,
                )
        return g

    def _start_shortest_path(self, source_node):
        self._path_source = source_node
        for item in self._scene.items():
            if isinstance(item, NodeItem):
                item.setOpacity(0.3 if item != source_node else 1.0)
        self._path_source.setOpacity(1.0)
        msg = f"Click target node for shortest path from '{source_node.title}'"
        self.status_message(msg)

    def _finish_shortest_path(self, target_node):
        if not self._path_source:
            return
        source_id = self._path_source.id
        target_id = target_node.id
        for item in self._scene.items():
            if isinstance(item, NodeItem):
                item.setOpacity(1.0)

        try:
            g = self._to_networkx()
            path = nx.shortest_path(g, source=source_id, target=target_id)
            self._highlight_path(path)
            self.status_message(f"Shortest path: {' → '.join(path)}")
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            self.status_message("No path found between selected nodes")
        self._path_source = None

    def _highlight_path(self, node_ids):
        self._clear_highlights()
        for item in self._scene.items():
            if isinstance(item, NodeItem) and item.id in node_ids:
                item.setOpacity(1.0)
                item.setScale(1.15)
            elif isinstance(item, NodeItem):
                item.setOpacity(0.25)
            if isinstance(item, EdgeItem):
                src_tgt = {item.source.id, item.target.id}
                on_path = any(
                    src_tgt == {node_ids[i], node_ids[i + 1]}
                    for i in range(len(node_ids) - 1)
                )
                item.setOpacity(1.0 if on_path else 0.15)

    def _clear_highlights(self):
        for item in self._scene.items():
            item.setOpacity(1.0)
            if isinstance(item, NodeItem):
                item.setScale(1.0)

    def _show_centrality(self):
        g = self._to_networkx()
        if g.number_of_nodes() == 0:
            self.status_message("Graph is empty")
            return
        cent = nx.degree_centrality(g)
        max_cent = max(cent.values()) if cent else 1
        for item in self._scene.items():
            if isinstance(item, NodeItem):
                c = cent.get(item.id, 0)
                item.setScale(0.8 + c / max_cent * 0.7)
        sorted_nodes = sorted(cent.items(), key=lambda x: x[1], reverse=True)
        top = [f"{g.nodes[n]['label']}: {c:.2f}" for n, c in sorted_nodes[:5]]
        self.status_message(f"Top centrality: {', '.join(top)}")

    def _detect_communities(self):
        g = self._to_networkx()
        if g.number_of_nodes() == 0:
            self.status_message("Graph is empty")
            return
        try:
            from networkx.algorithms.community import greedy_modularity_communities

            communities = list(greedy_modularity_communities(g))
            for i, comm in enumerate(communities):
                for node_id in comm:
                    for item in self._scene.items():
                        if isinstance(item, NodeItem) and item.id == node_id:
                            item.setScale(1.0)
                            break
            self.status_message(f"Found {len(communities)} communities")
        except ImportError:
            self.status_message("Community detection requires networkx 2.x")

    def status_message(self, msg):
        if self.parent():
            main = self.parent().parent().parent()
            if hasattr(main, "statusBar"):
                main.statusBar().showMessage(msg, 5000)

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        scene_pos = self.mapToScene(event.position().toPoint())
        item = self._scene.itemAt(scene_pos, self.transform())
        target = None
        if isinstance(item, NodeItem) and (
            event.modifiers() & Qt.KeyboardModifier.ControlModifier
        ):
            target = _map_zoom_target(item, scene_pos)
        if target is not None:
            new_zoom = target._map_zoom + (1 if delta > 0 else -1)
            if MAP_ZOOM_MIN <= new_zoom <= MAP_ZOOM_MAX:
                target._map_zoom = new_zoom
                _invalidate_map_cache(target)
                target.update()
                event.accept()
                return
        factor = 1.15 if delta > 0 else 1 / 1.15
        self.scale(factor, factor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._pan_start = event.pos()
            self._panning = True
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        if event.button() == Qt.MouseButton.LeftButton and self._path_source:
            scene_pos = self.mapToScene(event.pos())
            item = self._scene.itemAt(scene_pos, self.transform())
            if isinstance(item, NodeItem) and item != self._path_source:
                self._finish_shortest_path(item)
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._panning and event.buttons() & Qt.MouseButton.MiddleButton:
            delta = event.pos() - self._pan_start
            self._pan_start = event.pos()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x()
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y()
            )
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton and self._panning:
            self._panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            for item in self._scene.selectedItems():
                if isinstance(item, NodeItem):
                    self.remove_node(item)
                elif isinstance(item, EdgeItem):
                    self.remove_edge(item)
        else:
            super().keyPressEvent(event)

    def to_dict(self):
        nodes = []
        edges = []
        for item in self._scene.items():
            if isinstance(item, NodeItem):
                nodes.append(
                    {
                        "id": item.id,
                        "title": item.title,
                        "content": item.content,
                        "entity_type": item.entity_type,
                        "evidence": item.evidence,
                        "x": item.pos().x(),
                        "y": item.pos().y(),
                        "width": item._width,
                        "height": item._height,
                        "color": item.color,
                    }
                )
            elif isinstance(item, EdgeItem):
                edges.append(
                    {
                        "source": item.source.id,
                        "target": item.target.id,
                        "source_port": item.source_port,
                        "target_port": item.target_port,
                        "label": item.label,
                        "relationship_type": item.relationship_type,
                        "style": item.style,
                    }
                )
        return {"nodes": nodes, "edges": edges}

    def from_dict(self, data):
        self._scene.clear()
        node_map = {}
        for n in data.get("nodes", []):
            nid = str(n.get("id", uuid.uuid4().hex))
            node = NodeItem(
                title=n.get("title", "Node"),
                content=n.get("content", ""),
                entity_type=n.get("entity_type", "Custom"),
                node_id=nid,
            )
            node.evidence = n.get("evidence", [])
            node.color = n.get("color")
            node._width = int(n.get("width", 160))
            node._height = int(n.get("height", 120))
            node.setPos(n.get("x", 0), n.get("y", 0))
            self._scene.addItem(node)
            node_map[nid] = node
        for e in data.get("edges", []):
            src = node_map.get(str(e.get("source", "")))
            tgt = node_map.get(str(e.get("target", "")))
            if src and tgt:
                sp = e.get("source_port", "right")
                tp = e.get("target_port", "left")
                edge = EdgeItem(
                    src,
                    tgt,
                    sp,
                    tp,
                    label=e.get("label", ""),
                    relationship_type=e.get("relationship_type", ""),
                    style=e.get("style", "normal"),
                )
                self._scene.addItem(edge)
                src.add_edge_ref(edge)
                tgt.add_edge_ref(edge)

    def save_to_json(self, filepath):
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    def load_from_json(self, filepath):
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)
        self.from_dict(data)


if __name__ == "__main__":
    import os

    SAVE_FILE = "graph.json"

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = GraphWidget()
    properties_panel = PropertiesPanel(window)
    window.selectionChanged.connect(properties_panel.show_node)
    window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, properties_panel)
    window.setWindowTitle("Interactive Graph – JSON Persistence")
    window.resize(1100, 650)

    if os.path.exists(SAVE_FILE):
        try:
            window.load_from_json(SAVE_FILE)
        except Exception as e:
            print(f"Error loading graph: {e}")
    else:
        n1 = window.add_node(QPointF(-200, -80))
        n1.title = "Start"
        n1.content = "Beginning of the process"
        n1.update()

        n2 = window.add_node(QPointF(150, 80))
        n2.title = "Finish"
        n2.content = "Final goal"
        n2.update()

        n3 = window.add_node(QPointF(150, -200))
        n3.title = "Intermediate"
        n3.content = "An additional step"
        n3.update()

        window.add_edge(n1, n2)
        window.add_edge(n3, n1)

    def save_on_exit():
        window.save_to_json(SAVE_FILE)

    app.aboutToQuit.connect(save_on_exit)

    window.show()
    sys.exit(app.exec())
