#!/usr/bin/env python3
"""SkyFall per-user installer for Linux, macOS, and Windows.

Usage:
    python3 setup.py                  # install/update for the current user
    python3 setup.py uninstall        # uninstall for the current user
    sudo python3 setup.py --system    # system-wide install (Linux only)
"""

from __future__ import annotations

import argparse
import base64
import os
import plistlib
import shutil
import subprocess
import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path

APP_ID = "skyfall"  # должно совпадать с именем skyfall.desktop (Wayland app-id)
APP_NAME = "SkyFall"
APP_COMMENT = "OSINT investigation toolkit"
APP_CATEGORIES = "Network;Security;Utility;Science;"
APP_KEYWORDS = "osint;security;investigation;recon;skyfall;"

REPO_ROOT = Path(__file__).resolve().parent
ICON_SRC_PNG = REPO_ROOT / "resources" / "icon.png"
ICON_SRC_JPG = REPO_ROOT / "resources" / "icon.jpg"

ICON_SIZES = [16, 22, 24, 32, 48, 64, 96, 128, 192, 256, 512]

# Что НЕ копируем в /opt/skyfall (мусор разработки, venv'ы, кэши)
COPY_IGNORE_DIRS = {
    ".git",
    "__pycache__",
    ".ruff_cache",
    ".qtcreator",
    ".venv",
    "venv",
    "cache",
    ".mypy_cache",
    ".pytest_cache",
}
COPY_IGNORE_FILES = {".DS_Store"}

SYSTEM_APP_DIR = Path("/opt/skyfall")
SYSTEM_BIN_FILE = Path("/usr/local/bin/skyfall")
SYSTEM_DESKTOP_FILE = Path("/usr/share/applications/skyfall.desktop")
SYSTEM_SHARE = Path("/usr/share")
SYSTEM_PIXMAP = Path("/usr/share/pixmaps/skyfall.png")


def _color_enabled() -> bool:
    if os.environ.get("NO_COLOR") or os.environ.get("TERM") == "dumb":
        return False
    if not sys.stdout.isatty():
        return False
    if sys.platform == "win32":
        try:
            import ctypes

            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except Exception:  # noqa: BLE001
            return False
    return True


def _can_encode(text: str) -> bool:
    encoding = getattr(sys.stdout, "encoding", None) or "ascii"
    try:
        text.encode(encoding)
    except (UnicodeEncodeError, LookupError):
        return False
    return True


COLOR = _color_enabled()
UNICODE = _can_encode("✔✖›·█░")
OK_MARK = "✔" if UNICODE else "OK"
FAIL_MARK = "✖" if UNICODE else "x"
BULLET = "›" if UNICODE else ">"
DOT = "·" if UNICODE else "-"


def _style(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if COLOR else text


def bold(text: str) -> str:
    return _style(text, "1")


def dim(text: str) -> str:
    return _style(text, "90")


def green(text: str) -> str:
    return _style(text, "32")


def cyan(text: str) -> str:
    return _style(text, "36")


def yellow(text: str) -> str:
    return _style(text, "33")


def red(text: str) -> str:
    return _style(text, "31")


_LINE_ACTIVE = False
_LAST_PROGRESS: str | None = None


def _suspend_progress() -> None:
    """Стереть строку прогресса, чтобы напечатать лог поверх неё."""
    global _LINE_ACTIVE
    if _LINE_ACTIVE:
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()
        _LINE_ACTIVE = False


def _resume_progress() -> None:
    """Вернуть строку прогресса под только что напечатанным логом."""
    global _LINE_ACTIVE
    if _LAST_PROGRESS and sys.stdout.isatty():
        sys.stdout.write(f"\r{_LAST_PROGRESS}\033[K")
        sys.stdout.flush()
        _LINE_ACTIVE = True


def log(msg: str) -> None:
    _suspend_progress()
    print(f"  {dim(BULLET)} {msg}", flush=True)
    _resume_progress()


def warn(msg: str) -> None:
    _suspend_progress()
    print(f"  {yellow('!')} {yellow(msg)}", flush=True, file=sys.stderr)
    _resume_progress()


def error(msg: str) -> None:
    _suspend_progress()
    label = bold(red("Error:"))
    print(f"  {red(FAIL_MARK)} {label} {msg}", flush=True, file=sys.stderr)
    _resume_progress()


@contextmanager
def stage(label: str, start: int, end: int) -> Iterator[None]:
    progress(start, label, status="Starting")
    try:
        yield
    except Exception:
        error(f"{label} failed.")
        raise
    else:
        progress(end, label, status="Complete")


def _fit(text: str, limit: int) -> str:
    """Обрезать текст по ширине терминала, добавив многоточие."""
    if limit <= 1:
        return ""
    if len(text) <= limit:
        return text
    return text[: limit - 1] + ("…" if UNICODE else "~")


def progress(
    percent: int,
    label: str,
    *,
    status: str | None = None,
) -> None:
    """Нарисовать полосу прогресса. В TTY строка перерисовывается на месте."""
    global _LINE_ACTIVE, _LAST_PROGRESS

    percent = max(0, min(100, percent))
    width = 28
    filled = width * percent // 100
    done_char = "█" if UNICODE else "#"
    todo_char = "░" if UNICODE else "-"

    if sys.stdout.isatty():
        columns = shutil.get_terminal_size((80, 24)).columns
        budget = max(20, columns - 1 - (11 + width))
        if status:
            label = _fit(label, max(10, budget - 18))
            status = _fit(status, budget - len(label) - 2)
        else:
            label = _fit(label, budget)

    done = done_char * filled
    todo = todo_char * (width - filled)
    done = green(done) if percent >= 100 else cyan(done)
    bar = f"[{done}{dim(todo)}]"

    line = f"  {bar} {bold(f'{percent:3d}%')}  {label}"
    if status:
        line += f"  {green(status) if status in ('Complete', 'Ready') else dim(status)}"

    if not sys.stdout.isatty():
        print(line, flush=True)
        return

    sys.stdout.write(f"\r{line}\033[K")
    sys.stdout.flush()
    if status in ("Complete", "Ready") or percent >= 100:
        sys.stdout.write("\n")
        sys.stdout.flush()
        _LINE_ACTIVE = False
        _LAST_PROGRESS = None
    else:
        _LINE_ACTIVE = True
        _LAST_PROGRESS = line


def print_banner(action: str, scope: str, target: Path) -> None:
    """Шапка установщика: что делаем и куда ставим."""
    print(flush=True)
    print(f"  {bold(APP_NAME)}  {dim(DOT)}  {APP_COMMENT}", flush=True)
    print(f"  {dim(f'{action} {scope} {DOT} {target}')}", flush=True)
    print(flush=True)


def print_summary(
    updating: bool,
    app_dir: Path,
    bin_file: Path,
    desktop_file: Path | None,
    user_mode: bool,
) -> None:
    """Итог установки: короткая сводка с путями."""
    _suspend_progress()
    title = f"{APP_NAME} {'updated' if updating else 'installed'}"
    rows = [
        ("launcher", str(bin_file)),
        ("app files", str(app_dir)),
    ]
    if desktop_file is not None and desktop_file.is_file():
        rows.append(("shortcut", str(desktop_file)))

    print(flush=True)
    print(f"  {green(OK_MARK)}  {bold(title)}", flush=True)
    print(flush=True)
    for name, value in rows:
        print(f"  {dim(name.ljust(10))}{value}", flush=True)
    print(flush=True)
    if user_mode and sys.platform == "linux":
        print(
            f"  {dim('Tip:')} log out and back in, or run "
            f"{bold('gtk-launch skyfall')}, to refresh the icon.",
            flush=True,
        )
        print(flush=True)


def print_uninstall_summary() -> None:
    _suspend_progress()
    print(flush=True)
    print(f"  {green(OK_MARK)}  {bold(f'{APP_NAME} removed')}", flush=True)
    print(flush=True)


def run(cmd: list[str], timeout: int = 120, **kwargs) -> tuple[int, str]:
    """Запустить команду, вернуть (код, вывод). Никогда не падает."""
    try:
        p = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, **kwargs
        )
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except FileNotFoundError:
        return 127, f"command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return 124, f"command timed out after {timeout}s: {' '.join(cmd)}"
    except Exception as e:  # noqa: BLE001
        return 1, str(e)


def is_root() -> bool:
    try:
        return os.geteuid() == 0
    except AttributeError:
        return False  # Windows — не наш случай


def user_install_paths(home: Path) -> tuple[Path, Path, Path | None, Path | None]:
    """Return user-level app, launcher, desktop-entry, and share paths."""
    if sys.platform == "win32":
        local_app_data = Path(
            os.environ.get("LOCALAPPDATA", home / "AppData" / "Local")
        )
        app_dir = local_app_data / "Programs" / "SkyFall"
        return app_dir, app_dir / "skyfall.cmd", None, None
    if sys.platform == "darwin":
        app_dir = home / "Library" / "Application Support" / APP_ID
        launcher = home / "Applications" / "SkyFall.app" / "Contents" / "MacOS" / APP_ID
        return app_dir, launcher, None, None

    share_dir = home / ".local" / "share"
    app_dir = share_dir / APP_ID
    desktop_file = share_dir / "applications" / f"{APP_ID}.desktop"
    return app_dir, home / ".local" / "bin" / APP_ID, desktop_file, share_dir


def venv_python_path(venv_dir: Path) -> Path:
    if sys.platform == "win32":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def windows_shortcut_path(home: Path) -> Path:
    roaming = Path(os.environ.get("APPDATA", home / "AppData" / "Roaming"))
    return roaming / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "SkyFall.lnk"


def is_user_install(args) -> bool:
    has_custom_paths = any((args.prefix, args.bindir, args.sharedir))
    return args.user or (not args.system and not has_custom_paths)


def write_windows_shortcut(launcher: Path, app_dir: Path, home: Path) -> None:
    shortcut = windows_shortcut_path(home)
    shortcut.parent.mkdir(parents=True, exist_ok=True)

    def quote_ps(value: Path) -> str:
        return "'" + str(value).replace("'", "''") + "'"

    script = (
        "$shell = New-Object -ComObject WScript.Shell; "
        f"$link = $shell.CreateShortcut({quote_ps(shortcut)}); "
        f"$link.TargetPath = {quote_ps(launcher)}; "
        f"$link.WorkingDirectory = {quote_ps(app_dir)}; "
        "$link.Save()"
    )
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    rc, out = run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded]
    )
    if rc:
        warn(f"could not create Start menu shortcut: {out.strip()[-500:]}")
    else:
        log(f"Start menu shortcut: {shortcut}")


def write_macos_app(app_file: Path) -> None:
    contents = app_file.parent.parent
    contents.mkdir(parents=True, exist_ok=True)
    info = {
        "CFBundleExecutable": APP_ID,
        "CFBundleIdentifier": "org.skyfall.app",
        "CFBundleName": APP_NAME,
        "CFBundlePackageType": "APPL",
        "CFBundleVersion": "1.0",
        "LSMinimumSystemVersion": "10.15",
        "NSHighResolutionCapable": True,
    }
    with (contents / "Info.plist").open("wb") as stream:
        plistlib.dump(info, stream)
    os.chmod(app_file, 0o755)
    log(f"application bundle: {app_file.parents[2]}")


def touches_system_paths(args) -> bool:
    """Return whether the selected install paths require root."""
    if args.user:
        return False
    # кейс `--prefix /tmp/root` без bindir/sharedir = полностью локальный корень
    if args.prefix and not args.bindir and not getattr(args, "sharedir", None):
        return False
    prefix = Path(args.prefix) if args.prefix else SYSTEM_APP_DIR
    bindir = Path(args.bindir) if args.bindir else SYSTEM_BIN_FILE.parent
    sharedir = Path(args.sharedir) if getattr(args, "sharedir", None) else SYSTEM_SHARE
    for p in (prefix, bindir, sharedir):
        try:
            if p.resolve().is_relative_to(Path("/usr")) or p.resolve().is_relative_to(
                Path("/opt")
            ):
                return True
        except Exception:  # noqa: BLE001
            s = str(p)
            if s.startswith("/usr") or s.startswith("/opt"):
                return True
    # desktop/share по умолчанию системные
    if not args.prefix and not args.bindir:
        return True
    return False


def find_icon_source() -> Path | None:
    for cand in (ICON_SRC_PNG, ICON_SRC_JPG):
        if cand.is_file():
            return cand
    # последний шанс: любая icon.* в resources/
    for cand in sorted((REPO_ROOT / "resources").glob("icon.*")):
        if cand.is_file() and cand.suffix.lower() in (".png", ".jpg", ".jpeg"):
            return cand
    return None


def resize_icon(src: Path, dst: Path, size: int) -> bool:
    """Создать иконку size x size. Возвращает True при успехе."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    # 1) пробуем Pillow — самый качественный ресайз
    try:
        from PIL import Image  # type: ignore

        with Image.open(src) as im:
            im = im.convert("RGBA")
            im = im.resize((size, size), Image.LANCZOS)
            im.save(dst, "PNG")
        return True
    except ImportError:
        pass
    except Exception as e:  # noqa: BLE001
        warn(f"Pillow resize {size}px failed: {e}")

    # 2) пробуем ImageMagick
    for conv in ("convert", "magick"):
        if shutil.which(conv):
            args = (
                [conv, str(src), "-resize", f"{size}x{size}!", str(dst)]
                if conv == "convert"
                else [conv, str(src), "-resize", f"{size}x{size}!", str(dst)]
            )
            rc, _ = run(args)
            if rc == 0 and dst.is_file():
                return True

    # 3) fallback: просто копируем исходник (DE сам отмасштабирует;
    #    иконка будет видна везде, просто менее чётко на мелких размерах)
    try:
        shutil.copy2(src, dst)
        return True
    except OSError as e:
        warn(f"cannot install icon {size}px: {e}")
        return False


def copy_item_count(src: Path) -> int:
    count = 0
    for entry in src.iterdir():
        if entry.name in COPY_IGNORE_DIRS or entry.name in COPY_IGNORE_FILES:
            continue
        if entry.name.endswith((".pyc", ".pyo")):
            continue
        if entry.is_symlink() or not entry.is_dir():
            count += 1
        elif entry.name != ".git":
            count += copy_item_count(entry)
    return count


def copy_tree(
    src: Path,
    dst: Path,
    on_item: Callable[[str], None] | None = None,
) -> None:
    """Рекурсивно скопировать проект в dst (идемпотентно, для обновлений)."""
    dst.mkdir(parents=True, exist_ok=True)
    for entry in src.iterdir():
        name = entry.name
        if name in COPY_IGNORE_DIRS or name in COPY_IGNORE_FILES:
            continue
        if name.endswith((".pyc", ".pyo")):
            continue
        if name == Path(__file__).name and src == REPO_ROOT:
            # setup.py тоже копируем — удобно для диагностики в /opt
            pass
        target = dst / name
        if entry.is_symlink():
            if target.exists() or target.is_symlink():
                target.unlink()
            target.symlink_to(os.readlink(entry))
            if on_item:
                on_item(name)
        elif entry.is_dir():
            if name == ".git":
                continue
            copy_tree(entry, target, on_item=on_item)
            # чистим __pycache__ внутри скопированного
            for pyc in target.rglob("__pycache__"):
                if pyc.is_dir():
                    shutil.rmtree(pyc, ignore_errors=True)
        else:
            shutil.copy2(entry, target)
            if on_item:
                on_item(name)


def ensure_venv(app_dir: Path) -> Path:
    """Создать (или переиспользовать) venv в app_dir/venv. Вернуть путь к python."""
    import venv as venvlib

    venv_dir = app_dir / "venv"
    venv_python = venv_python_path(venv_dir)
    if not venv_python.is_file():
        progress(27, "Python environment", status="Creating virtual environment")
        venvlib.create(str(venv_dir), with_pip=True)
    else:
        progress(30, "Python environment", status="Reusing virtual environment")
    return venv_python


def verify_deps(venv_python: Path) -> bool:
    """Проверить, что ключевые зависимости реально импортируются в venv."""
    rc, out = run(
        [str(venv_python), "-c", "import qasync, PySide6; print('deps OK')"],
        timeout=180,
    )
    if rc != 0:
        error("dependency verification failed:\n" + out.strip()[-2000:])
        return False
    return True


def pip_install(venv_python: Path, no_deps: bool = False) -> bool:
    req = REPO_ROOT / "requirements.txt"
    progress(35, "Python packages", status="Upgrading pip")
    run(
        [str(venv_python), "-m", "pip", "install", "--upgrade", "pip"],
        cwd=str(REPO_ROOT),
        timeout=600,
    )
    if no_deps:
        progress(80, "Python packages", status="Dependency installation skipped")
        return True
    if not req.is_file():
        warn("requirements.txt not found, skipping deps")
        return True
    progress(40, "Python packages", status="Installing requirements")
    try:
        p = subprocess.run(
            [str(venv_python), "-m", "pip", "install", "-r", str(req)],
            cwd=str(REPO_ROOT),
            timeout=3600,
            capture_output=True,
            text=True,
        )
    except subprocess.TimeoutExpired:
        error("dependency installation timed out after 60 minutes.")
        return False
    except Exception as e:  # noqa: BLE001
        error(f"dependency installation failed: {e}")
        return False
    if p.returncode != 0:
        details = (p.stdout or "") + (p.stderr or "")
        error("dependency installation failed:\n" + details.strip()[-4000:])
        return False
    progress(78, "Python packages", status="Packages installed")
    progress(80, "Python packages", status="Verifying dependencies")
    return verify_deps(venv_python)


def write_launcher(bin_file: Path, app_dir: Path, use_venv: bool) -> None:
    """Лаунчер-обёртка.

    ВАЖНО: нельзя использовать `exec -a skyfall` — CPython ищет pyvenv.cfg
    отталкиваясь от argv[0], и с подменённым argv[0] venv «теряется»
    (sys.prefix становится /usr, зависимости не видны).
    Вместо этого внутри venv создаётся симлинк с именем `skyfall`
    на интерпретатор: argv[0] содержит реальный путь в venv/bin
    (venv детектится), а basename — `skyfall` (красивое имя процесса
    и правильный fallback для Wayland app-id; основной механизм —
    app.setDesktopFileName("skyfall") в main.py).
    """
    bin_file.parent.mkdir(parents=True, exist_ok=True)
    if sys.platform == "win32":
        python = '"%~dp0venv\\Scripts\\python.exe"' if use_venv else "python"
        content = f'@echo off\r\n{python} "%~dp0main.py" %*\r\n'
    elif use_venv:
        py = app_dir / "venv" / "bin" / "python"
        alias = app_dir / "venv" / "bin" / APP_ID
        try:
            if alias.is_symlink() or alias.exists():
                alias.unlink()
            alias.symlink_to(py.name)  # symlink "skyfall" -> "python"
            log(f"interpreter alias: {alias} -> {py.name}")
        except OSError as e:
            warn(f"cannot create interpreter alias {alias}: {e}; using python")
            alias = py
        content = (
            "#!/bin/sh\n"
            f"# Auto-generated by SkyFall setup.py — DO NOT EDIT\n"
            f'exec "{alias}" "{app_dir}/main.py" "$@"\n'
        )
    else:
        content = (
            "#!/bin/sh\n"
            f"# Auto-generated by SkyFall setup.py (system python, no venv)\n"
            f'exec /usr/bin/env python3 "{app_dir}/main.py" "$@"\n'
        )
    bin_file.write_text(content, encoding="utf-8")
    if sys.platform != "win32":
        os.chmod(bin_file, 0o755)
    log(f"launcher: {bin_file}")


DESKTOP_TEMPLATE = """[Desktop Entry]
Type=Application
Name={app_name}
GenericName={app_name} OSINT Toolkit
Comment={comment}
Exec={exec_path} %F
TryExec={exec_path}
Icon={icon_name}
Terminal=false
Categories={categories}
Keywords={keywords}
StartupNotify=true
StartupWMClass={wm_class}
SingleMainWindow=true
MimeType=x-scheme-handler/skyfall;
Actions=Debug;

[Desktop Action Debug]
Name=Run in debug mode
Exec={exec_path} --debug
Icon={icon_name}
"""


def write_desktop(desktop_file: Path, exec_path: Path) -> None:
    desktop_file.parent.mkdir(parents=True, exist_ok=True)
    escaped_exec_path = str(exec_path).replace("\\", "\\\\").replace('"', '\\"')
    desktop_file.write_text(
        DESKTOP_TEMPLATE.format(
            app_name=APP_NAME,
            comment=APP_COMMENT,
            exec_path=f'"{escaped_exec_path}"',
            icon_name=APP_ID,  # ВАЖНО: имя, а не путь — резолвится через hicolor
            categories=APP_CATEGORIES,
            keywords=APP_KEYWORDS,
            wm_class=APP_ID,  # совпадает с exec -a skyfall (X11 + Wayland)
        ),
        encoding="utf-8",
    )
    os.chmod(desktop_file, 0o644)
    log(f"desktop file: {desktop_file}")


def install_icons(share_dir: Path) -> int:
    """Разложить иконки по hicolor + pixmaps fallback. Вернуть кол-во файлов."""
    src = find_icon_source()
    if src is None:
        warn("no icon found in resources/ (expected icon.png), skipping icons")
        return 0
    log(f"icon source: {src}")
    count = 0
    for size in ICON_SIZES:
        dst = (
            share_dir
            / "icons"
            / "hicolor"
            / f"{size}x{size}"
            / "apps"
            / f"{APP_ID}.png"
        )
        if resize_icon(src, dst, size):
            os.chmod(dst, 0o644)
            count += 1
    # fallback для старых WM (XFCE/LXDE/Cinnamon/awesome): pixmaps
    try:
        pixdir = share_dir / "pixmaps"
        pixdir.mkdir(parents=True, exist_ok=True)
        pix = pixdir / f"{APP_ID}.png"
        # для pixmaps кладём максимально качественный крупный PNG
        big = share_dir / "icons" / "hicolor" / "512x512" / "apps" / f"{APP_ID}.png"
        if big.is_file():
            shutil.copy2(big, pix)
        else:
            shutil.copy2(src, pix)
        os.chmod(pix, 0o644)
        count += 1
        log(f"pixmap fallback: {pix}")
    except OSError as e:
        warn(f"pixmap install failed: {e}")
    log(f"installed {count} icon files")
    return count


def refresh_caches(share_dir: Path) -> None:
    """Обновить кэши иконок/десктопов чтобы иконка появилась сразу везде."""
    apps_dir = str(share_dir / "applications")
    icons_dir = str(share_dir / "icons" / "hicolor")

    steps: list[list[str]] = [
        ["update-desktop-database", "-q", apps_dir],
        ["gtk-update-icon-cache", "-f", "-t", icons_dir],
        ["xdg-icon-resource", "forceupdate"],
        ["update-icon-caches", icons_dir],
    ]
    refreshed = 0
    for cmd in steps:
        if shutil.which(cmd[0]) is None:
            continue
        rc, out = run(cmd)
        if rc == 0:
            refreshed += 1
        else:
            warn(f"cache failed ({' '.join(cmd)}): {out.strip()[-300:]}")

    # KDE Plasma (X11 и Wayland)
    for kbd in ("kbuildsycoca6", "kbuildsycoca5"):
        if shutil.which(kbd):
            rc, _ = run([kbd, "--noincremental"])
            if rc == 0:
                refreshed += 1
            break

    # GNOME Wayland подхватывает hicolor автоматически, но на всякий случай
    # трогаем desktop-файл чтобы обновить mtime.
    try:
        d = share_dir / "applications" / f"{APP_ID}.desktop"
        if d.is_file():
            os.utime(d, None)
    except OSError:
        pass

    if refreshed:
        log("refreshed desktop and icon caches")


def validate_desktop(desktop_file: Path) -> None:
    if shutil.which("desktop-file-validate"):
        rc, out = run(["desktop-file-validate", str(desktop_file)])
        if rc != 0:
            warn(f"desktop-file-validate:\n{out.strip()[-1000:]}")
        else:
            log("desktop file validates OK")
    if shutil.which("desktop-file-install") is None:
        pass


def do_install(args) -> int:
    user_mode: bool = args.user
    if args.system and sys.platform != "linux":
        error("system-wide installation is supported only on Linux.")
        return 1
    if touches_system_paths(args) and not is_root():
        error("system installation requires root. Re-run with sudo, or use --user.")
        return 1

    home = Path.home()
    if user_mode:
        app_dir, bin_file, desktop_file, share_dir = user_install_paths(home)
    else:
        app_dir = Path(args.prefix) if args.prefix else SYSTEM_APP_DIR
        bin_file = Path(args.bindir) / APP_ID if args.bindir else SYSTEM_BIN_FILE
        share_dir = Path(args.sharedir) if args.sharedir else SYSTEM_SHARE
        if args.prefix and not args.bindir and not args.sharedir:
            # удобный кейс: --prefix /tmp/root => app в <root>/opt/skyfall,
            # bin в <root>/bin, share в <root>/share
            root = Path(args.prefix)
            if root.name != APP_ID:
                app_dir = root / "opt" / APP_ID
                bin_file = root / "bin" / APP_ID
                share_dir = root / "share"
        desktop_file = share_dir / "applications" / f"{APP_ID}.desktop"

    updating = app_dir.is_dir() and any(app_dir.iterdir())
    action = "Updating" if updating else "Installing"
    if user_mode:
        scope = "for the current user"
    elif args.prefix or args.bindir or args.sharedir:
        scope = "to a custom prefix"
    else:
        scope = "system-wide"

    if (REPO_ROOT / "main.py").is_file() is False:
        error(f"main.py not found in {REPO_ROOT}; installation aborted.")
        return 1

    print_banner(action, scope, app_dir)
    with stage("Copying application files", 0, 25):
        total_items = copy_item_count(REPO_ROOT)
        copied_items = 0

        def report_copy(name: str) -> None:
            nonlocal copied_items
            copied_items += 1
            if sys.stdout.isatty() and total_items:
                percent = copied_items * 25 // total_items
                progress(
                    percent,
                    "Copying application files",
                    status=f"{copied_items}/{total_items}: {name}",
                )

        copy_tree(REPO_ROOT, app_dir, on_item=report_copy)

    use_venv = not args.no_venv
    deps_ok = True
    with stage("Preparing Python environment and dependencies", 25, 80):
        if use_venv:
            venv_python = ensure_venv(app_dir)
            deps_ok = pip_install(venv_python, no_deps=args.no_deps)

    with stage("Creating launchers and application shortcuts", 85, 99):
        write_launcher(bin_file, app_dir, use_venv)
        if sys.platform == "win32":
            write_windows_shortcut(bin_file, app_dir, home)
        elif sys.platform == "darwin":
            write_macos_app(bin_file)
        else:
            write_desktop(desktop_file, bin_file)
            validate_desktop(desktop_file)
            install_icons(share_dir)
            refresh_caches(share_dir)

    if not deps_ok:
        error(f"{APP_NAME} installation is incomplete because dependencies failed.")
        return 1
    progress(100, "Installation complete", status="Ready")
    print_summary(updating, app_dir, bin_file, desktop_file, user_mode)
    return 0


def do_uninstall(args) -> int:
    user_mode: bool = args.user
    if args.system and sys.platform != "linux":
        error("system-wide uninstallation is supported only on Linux.")
        return 1
    if touches_system_paths(args) and not is_root():
        error("system uninstallation requires root. Re-run with sudo, or use --user.")
        return 1

    home = Path.home()
    if user_mode:
        app_dir, bin_file, desktop_file, share_dir = user_install_paths(home)
        targets = [app_dir, bin_file]
        if desktop_file:
            targets.append(desktop_file)
        if sys.platform == "win32":
            targets.append(windows_shortcut_path(home))
        if sys.platform == "darwin":
            targets.append(home / "Applications" / "SkyFall.app")
        share_dir = share_dir or app_dir
    elif args.prefix or args.bindir or args.sharedir:
        # зеркалит логику do_install для кастомных корней
        if args.prefix and not args.bindir and not args.sharedir:
            root = Path(args.prefix)
            if root.name != APP_ID:
                targets = [
                    root / "opt" / APP_ID,
                    root / "bin" / APP_ID,
                    root / "share" / "applications" / f"{APP_ID}.desktop",
                ]
                share_dir = root / "share"
            else:
                targets = [root]
                share_dir = (
                    root.parent.parent / "share"
                    if root.parent.name == "opt"
                    else SYSTEM_SHARE
                )
        else:
            app_dir = Path(args.prefix) if args.prefix else SYSTEM_APP_DIR
            bin_file = Path(args.bindir) / APP_ID if args.bindir else SYSTEM_BIN_FILE
            share_dir = Path(args.sharedir) if args.sharedir else SYSTEM_SHARE
            targets = [
                app_dir,
                bin_file,
                share_dir / "applications" / f"{APP_ID}.desktop",
            ]
    else:
        targets = [SYSTEM_APP_DIR, SYSTEM_BIN_FILE, SYSTEM_DESKTOP_FILE]
        share_dir = SYSTEM_SHARE

    for t in targets:
        try:
            if t.is_symlink() or t.is_file():
                t.unlink()
                log(f"removed file: {t}")
            elif t.is_dir():
                shutil.rmtree(t)
                log(f"removed dir: {t}")
            else:
                log(f"not present, skip: {t}")
        except OSError as e:
            error(f"cannot remove {t}: {e}")

    if sys.platform != "linux":
        if args.purge:
            for d in (
                home / ".skyfall",
                home / ".config" / APP_ID,
                home / ".cache" / APP_ID,
            ):
                try:
                    if d.is_dir():
                        shutil.rmtree(d)
                        log(f"purged: {d}")
                except OSError as e:
                    error(f"cannot purge {d}: {e}")
        print_uninstall_summary()
        return 0

    # иконки hicolor
    removed_icons = 0
    for size in ICON_SIZES:
        f = (
            share_dir
            / "icons"
            / "hicolor"
            / f"{size}x{size}"
            / "apps"
            / f"{APP_ID}.png"
        )
        try:
            if f.is_file():
                f.unlink()
                removed_icons += 1
        except OSError:
            pass
    for pix in (
        share_dir / "pixmaps" / f"{APP_ID}.png",
        share_dir / "pixmaps" / f"{APP_ID}.xpm",
    ):
        try:
            if pix.is_file():
                pix.unlink()
                removed_icons += 1
        except OSError:
            pass
    if removed_icons:
        log(f"removed {removed_icons} icon files")

    refresh_caches(share_dir)

    if args.purge:
        for d in (
            home / ".skyfall",
            home / ".config" / APP_ID,
            home / ".cache" / APP_ID,
        ):
            try:
                if d.is_dir():
                    shutil.rmtree(d)
                    log(f"purged: {d}")
            except OSError as e:
                error(f"cannot purge {d}: {e}")

    print_uninstall_summary()
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="setup.py",
        description="Install or update SkyFall for the current user. "
        "System-wide installation is available on Linux.",
    )
    p.add_argument(
        "command",
        nargs="?",
        choices=["install", "uninstall"],
        default="install",
        help="action (default: install)",
    )
    p.add_argument("--user", action="store_true", help="install for the current user")
    p.add_argument(
        "--system",
        action="store_true",
        help="install system-wide (Linux only; requires root)",
    )
    p.add_argument(
        "--prefix",
        default=None,
        help="custom app dir (default /opt/skyfall). "
        "With --prefix, icons/desktop go to <prefix>/share.",
    )
    p.add_argument(
        "--bindir",
        default=None,
        help="custom dir for the 'skyfall' launcher (default /usr/local/bin)",
    )
    p.add_argument(
        "--sharedir",
        default=None,
        help="custom share dir for icons/desktop (default /usr/share)",
    )
    p.add_argument(
        "--uninstall", action="store_true", help="same as 'uninstall' command"
    )
    p.add_argument(
        "--purge",
        action="store_true",
        help="with uninstall: also delete ~/.skyfall user data",
    )
    p.add_argument(
        "--no-venv", action="store_true", help="don't create venv, use system python3"
    )
    p.add_argument(
        "--no-deps", action="store_true", help="don't pip-install requirements.txt"
    )
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.user and args.system:
        parser.error("--user and --system cannot be used together")
    if sys.platform != "linux" and any((args.prefix, args.bindir, args.sharedir)):
        parser.error("custom --prefix/--bindir/--sharedir paths are Linux-only")
    if args.system and sys.platform != "linux":
        parser.error("--system is supported only on Linux")
    args.user = is_user_install(args)
    cmd = "uninstall" if args.uninstall else args.command
    if cmd == "uninstall":
        return do_uninstall(args)
    return do_install(args)


if __name__ == "__main__":
    sys.exit(main())
