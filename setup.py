#!/usr/bin/env python3
"""
SkyFall — системный установщик для Linux (в стиле wifite2).

Использование:
    sudo python3 setup.py                  # установка / обновление в /opt/skyfall
    sudo python3 setup.py install          # то же самое
    sudo python3 setup.py uninstall        # удалить из системы
    python3 setup.py --user                # установка без root в ~/.local
    sudo python3 setup.py --uninstall --purge   # удалить + стереть кэш/конфиги

Повторный запуск после `git pull`:
    git pull
    sudo python3 setup.py
— исходники в /opt/skyfall будут перезаписаны, venv обновлён,
  иконки и .desktop переустaновлены, кэши иконок обновлены.

Как обеспечивается иконка везде (X11 + Wayland, GNOME/KDE/XFCE/...):
  * .desktop называется `skyfall.desktop`, внутри `Icon=skyfall` (имя, НЕ путь)
    и `StartupWMClass=skyfall` + `StartupNotify=true`.
  * PNG 1024x1024 из resources/icon.png раскладывается по теме hicolor
    во все стандартные размеры (16..512), плюс fallback-копия
    в `pixmaps/skyfall.png` для старых WM.
  * Лаунчер /usr/local/bin/skyfall запускает main.py через симлинк
    /opt/skyfall/venv/bin/skyfall -> python, поэтому имя процесса —
    "skyfall" (а venv при этом детектится корректно; `exec -a` использовать
    нельзя — он ломает поиск pyvenv.cfg). Wayland app-id дополнительно
    зафиксирован в коде через app.setDesktopFileName("skyfall").
  * После установки вызываются: update-desktop-database,
    gtk-update-icon-cache, xdg-icon-resource forceupdate, kbuildsycoca
    (если есть). Это покрывает X11 и Wayland разом.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
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


def log(msg: str) -> None:
    print(f"[SkyFall setup] {msg}", flush=True)


def warn(msg: str) -> None:
    print(f"[SkyFall setup] WARNING: {msg}", flush=True, file=sys.stderr)


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


def touches_system_paths(args) -> bool:
    """Нужен ли root: трогаем ли /opt, /usr без флага --user."""
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


def copy_tree(src: Path, dst: Path) -> None:
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
        elif entry.is_dir():
            if name == ".git":
                continue
            copy_tree(entry, target)
            # чистим __pycache__ внутри скопированного
            for pyc in target.rglob("__pycache__"):
                if pyc.is_dir():
                    shutil.rmtree(pyc, ignore_errors=True)
        else:
            shutil.copy2(entry, target)


def ensure_venv(app_dir: Path) -> Path:
    """Создать (или переиспользовать) venv в app_dir/venv. Вернуть путь к python."""
    import venv as venvlib

    venv_dir = app_dir / "venv"
    venv_python = venv_dir / "bin" / "python"
    if not venv_python.is_file():
        log(f"creating venv: {venv_dir}")
        venvlib.create(str(venv_dir), with_pip=True)
    else:
        log(f"reusing venv: {venv_dir}")
    return venv_python


def verify_deps(venv_python: Path) -> bool:
    """Проверить, что ключевые зависимости реально импортируются в venv."""
    rc, out = run(
        [str(venv_python), "-c", "import qasync, PySide6; print('deps OK')"],
        timeout=180,
    )
    if rc != 0:
        warn("dependencies verification failed:\n" + out.strip()[-2000:])
        return False
    log("dependencies verified: qasync, PySide6 import OK")
    return True


def pip_install(venv_python: Path, no_deps: bool = False) -> bool:
    req = REPO_ROOT / "requirements.txt"
    log("upgrading pip...")
    run(
        [str(venv_python), "-m", "pip", "install", "--upgrade", "pip"],
        cwd=str(REPO_ROOT),
        timeout=600,
    )
    if no_deps:
        log("--no-deps: skipping requirements.txt")
        return True
    if not req.is_file():
        warn("requirements.txt not found, skipping deps")
        return True
    # ВАЖНО: полный requirements (~150 пакетов: PySide6, scipy, ...) ставится
    # 5-15 минут. Вывод pip показываем вживую (без capture), таймаут — 1 час,
    # иначе был баг: тихий обрыв по timeout=120с и пустой venv.
    log("installing requirements.txt (takes 5-15 min, do not interrupt)...")
    try:
        p = subprocess.run(
            [str(venv_python), "-m", "pip", "install", "-r", str(req)],
            cwd=str(REPO_ROOT),
            timeout=3600,
        )
    except subprocess.TimeoutExpired:
        warn("pip install timed out after 60 minutes. Check your network and re-run.")
        return False
    except Exception as e:  # noqa: BLE001
        warn(f"pip install crashed: {e}")
        return False
    if p.returncode != 0:
        warn(
            "pip install FAILED (see output above). "
            "Fix the error (usually missing system libs or network) "
            "and re-run setup.py."
        )
        return False
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
    if use_venv:
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
    desktop_file.write_text(
        DESKTOP_TEMPLATE.format(
            app_name=APP_NAME,
            comment=APP_COMMENT,
            exec_path=str(exec_path),
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


def refresh_caches(share_dir: Path, user_mode: bool) -> None:
    """Обновить кэши иконок/десктопов чтобы иконка появилась сразу везде."""
    apps_dir = str(share_dir / "applications")
    icons_dir = str(share_dir / "icons" / "hicolor")

    steps: list[list[str]] = [
        ["update-desktop-database", "-q", apps_dir],
        ["gtk-update-icon-cache", "-f", "-t", icons_dir],
        ["xdg-icon-resource", "forceupdate"],
        ["update-icon-caches", icons_dir],
    ]
    for cmd in steps:
        if shutil.which(cmd[0]) is None:
            continue
        rc, out = run(cmd)
        if rc == 0:
            log(f"cache OK: {' '.join(cmd)}")
        else:
            warn(f"cache failed ({' '.join(cmd)}): {out.strip()[-300:]}")

    # KDE Plasma (X11 и Wayland)
    for kbd in ("kbuildsycoca6", "kbuildsycoca5"):
        if shutil.which(kbd):
            rc, _ = run([kbd, "--noincremental"])
            if rc == 0:
                log(f"cache OK: {kbd}")
            break

    # GNOME Wayland подхватывает hicolor автоматически, но на всякий случай
    # трогаем desktop-файл чтобы обновить mtime.
    try:
        d = share_dir / "applications" / f"{APP_ID}.desktop"
        if d.is_file():
            os.utime(d, None)
    except OSError:
        pass

    if user_mode:
        log("user mode: log out/in or run `gtk-launch skyfall` to test the icon")


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
    if touches_system_paths(args) and not is_root():
        warn("system install needs root. Re-run with sudo, or use --user.")
        return 1

    home = Path.home()
    if user_mode:
        app_dir = home / ".local" / "share" / APP_ID
        bin_file = home / ".local" / "bin" / APP_ID
        desktop_file = home / ".local" / "share" / "applications" / f"{APP_ID}.desktop"
        share_dir = home / ".local" / "share"
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
    log(f"{'updating' if updating else 'installing'} {APP_NAME} -> {app_dir}")

    if (REPO_ROOT / "main.py").is_file() is False:
        warn(f"main.py not found in {REPO_ROOT}, aborting")
        return 1

    # 1. Копируем исходники (повторный запуск = обновление)
    copy_tree(REPO_ROOT, app_dir)
    log(f"sources synced: {REPO_ROOT} -> {app_dir}")

    # 2. Python-окружение
    use_venv = not args.no_venv
    deps_ok = True
    if use_venv:
        venv_python = ensure_venv(app_dir)
        deps_ok = pip_install(venv_python, no_deps=args.no_deps)
        if not deps_ok:
            warn("dependencies NOT installed — install is incomplete!")
    else:
        log("--no-venv: using system python3")

    # 3. Лаунчер, .desktop, иконки
    write_launcher(bin_file, app_dir, use_venv)
    write_desktop(desktop_file, bin_file)
    validate_desktop(desktop_file)
    install_icons(share_dir)
    refresh_caches(share_dir, user_mode)

    print()
    if not deps_ok:
        warn(
            f"{APP_NAME} installed BUT WITHOUT dependencies. "
            f"Fix pip errors above and re-run: sudo python3 setup.py"
        )
        return 1
    log(f"{APP_NAME} {'updated' if updating else 'installed'} successfully!")
    log(f"run: {bin_file}  (or find '{APP_NAME}' in your app menu)")
    if user_mode and str(bin_file.parent) not in os.environ.get("PATH", ""):
        warn(f"{bin_file.parent} is not in PATH — add it to ~/.profile")
    return 0


def do_uninstall(args) -> int:
    user_mode: bool = args.user
    if touches_system_paths(args) and not is_root():
        warn("system uninstall needs root. Re-run with sudo, or use --user.")
        return 1

    home = Path.home()
    if user_mode:
        targets = [
            home / ".local" / "share" / APP_ID,
            home / ".local" / "bin" / APP_ID,
            home / ".local" / "share" / "applications" / f"{APP_ID}.desktop",
        ]
        share_dir = home / ".local" / "share"
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
            warn(f"cannot remove {t}: {e}")

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

    refresh_caches(share_dir, user_mode)

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
                warn(f"cannot purge {d}: {e}")

    log("uninstall complete")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="setup.py",
        description="SkyFall system installer for Linux (X11 + Wayland icons, "
        "re-runnable update like wifite2).",
    )
    p.add_argument(
        "command",
        nargs="?",
        choices=["install", "uninstall"],
        default="install",
        help="action (default: install)",
    )
    p.add_argument(
        "--user", action="store_true", help="install into ~/.local without root"
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
    args = build_parser().parse_args(argv)
    cmd = "uninstall" if args.uninstall else args.command
    if cmd == "uninstall":
        return do_uninstall(args)
    return do_install(args)


if __name__ == "__main__":
    sys.exit(main())
